"""DeviceManager — per-round active patches, syndromes, blocking Conditional-S."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.schedule import LatticeSurgerySchedule, PatchOpType, ProgramOp
from core.syndrome_graph import generate_window_syndrome_with_truth, true_predecessor_logical
from core.window_manager import DecodeWindow


@dataclass(frozen=True)
class PatchSyndrome:
    patch_id: int
    chain_id: int
    round: int
    syndrome: np.ndarray
    hidden_z: np.ndarray


@dataclass
class ChainBlockingState:
    chain_id: int
    blocked: bool = False
    block_start: int | None = None
    cond_wait_rounds: int = 0


@dataclass
class DeviceManager:
    """Simulate device rounds: active patches, syndromes, blocking Conditional-S."""

    schedule: LatticeSurgerySchedule
    seed: int
    cycle_time_us: float = 1.0
    chains: list[ChainBlockingState] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.chains:
            self.chains = [
                ChainBlockingState(chain_id=c) for c in range(self.schedule.parallelism)
            ]

    def active_patches_at(self, round_idx: int) -> list[tuple[int, int]]:
        """Return (patch_id, chain_id) pairs active at this round (merge/split aware)."""
        if not self.schedule.program:
            return [(c, c) for c in range(self.schedule.parallelism)]
        active: dict[int, int] = {c: c for c in range(self.schedule.parallelism)}
        for op in self.schedule.program.ops:
            if op.round > round_idx:
                break
            if op.op_type == PatchOpType.MERGE and op.target_patch_id is not None:
                for pid in op.patch_ids:
                    patch = self.schedule.program.patch_by_id(pid)
                    active[patch.chain_id] = op.target_patch_id
            elif op.op_type == PatchOpType.SPLIT and op.target_patch_id is not None:
                src = op.patch_ids[0]
                src_patch = self.schedule.program.patch_by_id(src)
                active[src_patch.chain_id] = op.target_patch_id
        return [(pid, chain) for chain, pid in sorted(active.items())]

    def patch_id_for_chain(self, round_idx: int, chain_id: int) -> int:
        for patch_id, chain in self.active_patches_at(round_idx):
            if chain == chain_id:
                return patch_id
        return chain_id

    def sync_window_patches(self, windows: list[DecodeWindow], round_idx: int) -> None:
        """Remap window patch_id after merge/split ops at this round."""
        for window in windows:
            window.patch_id = self.patch_id_for_chain(round_idx, window.chain_id)

    def ops_at_round(self, round_idx: int) -> tuple[ProgramOp, ...]:
        if not self.schedule.program:
            return ()
        return self.schedule.program.ops_at_round(round_idx)

    def is_chain_blocked(self, chain_id: int) -> bool:
        return any(c.chain_id == chain_id and c.blocked for c in self.chains)

    def blocks_window_progress(
        self,
        window: DecodeWindow,
        *,
        speculative: bool,
        speculated: bool,
    ) -> bool:
        """Conditional-S stall: post-blocking windows wait until dep verified."""
        if window.index_in_chain < self.schedule.blocking_window_index:
            return False
        if not self.is_chain_blocked(window.chain_id):
            return False
        if speculative and speculated:
            return False
        return True

    def appearance_allowed(
        self,
        window: DecodeWindow,
        round_idx: int,
        *,
        speculative: bool,
        window_verified: dict[tuple[int, int], bool],
    ) -> bool:
        """Device gates window exposure at Conditional-S boundaries."""
        if round_idx < window.gen_round:
            return False
        dep_idx = self.schedule.blocking_window_index - 1
        if not speculative and window.index_in_chain >= self.schedule.blocking_window_index:
            if not window_verified.get((window.chain_id, dep_idx), False):
                return False
        if (
            not speculative
            and self.is_chain_blocked(window.chain_id)
            and window.index_in_chain >= self.schedule.blocking_window_index
        ):
            return False
        return True

    def emit_syndrome(
        self,
        *,
        window_id: int,
        patch_id: int,
        chain_id: int,
        pred_id: int | None,
        pred_verified: bool,
        round_idx: int,
        true_pred_logical: int | None = None,
    ) -> PatchSyndrome:
        true_left = (
            int(true_pred_logical) % 2
            if true_pred_logical is not None
            else true_predecessor_logical(
                pred_id=pred_id,
                pred_verified=pred_verified,
                seed=self.seed,
            )
        )
        synd, hidden_z = generate_window_syndrome_with_truth(
            window_id=window_id,
            pred_id=pred_id,
            seed=self.seed + patch_id * 31,
            true_pred_logical=true_left,
        )
        return PatchSyndrome(
            patch_id=patch_id,
            chain_id=chain_id,
            round=round_idx,
            syndrome=synd,
            hidden_z=hidden_z,
        )

    def update_blocking(
        self,
        round_idx: int,
        *,
        window_appeared: dict[tuple[int, int], bool],
        window_verified: dict[tuple[int, int], bool],
    ) -> None:
        """Block chains at Conditional-S when blocking window appeared but dep unverified."""
        block_idx = self.schedule.blocking_window_index
        dep_idx = block_idx - 1
        for chain in self.chains:
            if not chain.blocked:
                if window_appeared.get((chain.chain_id, block_idx), False):
                    if not window_verified.get((chain.chain_id, dep_idx), False):
                        chain.blocked = True
                        chain.block_start = round_idx
            elif chain.block_start is not None:
                if window_verified.get((chain.chain_id, dep_idx), False):
                    chain.blocked = False
                    chain.block_start = None

    def account_conditional_stalls(
        self,
        windows: list[DecodeWindow],
        round_idx: int,
        *,
        speculative: bool,
        window_verified: dict[tuple[int, int], bool],
    ) -> None:
        """Count each Conditional-S stall round once (blocked state or nonspec dep wait)."""
        dep_idx = self.schedule.blocking_window_index - 1
        for chain in self.chains:
            if chain.blocked:
                chain.cond_wait_rounds += 1
                continue
            if speculative:
                continue
            waiting = any(
                w.chain_id == chain.chain_id
                and w.index_in_chain >= self.schedule.blocking_window_index
                and not w.appeared
                and round_idx >= w.gen_round
                and not window_verified.get((w.chain_id, dep_idx), False)
                for w in windows
            )
            if waiting:
                chain.cond_wait_rounds += 1

    def total_conditional_wait_rounds(self) -> int:
        return sum(c.cond_wait_rounds for c in self.chains)

    def blocking_ops_pending_verification(
        self, window_verified: dict[tuple[int, int], bool]
    ) -> list[ProgramOp]:
        pending: list[ProgramOp] = []
        if not self.schedule.program:
            return pending
        for op in self.schedule.program.blocking_ops():
            idx = op.blocks_until_window_index
            if idx is None:
                continue
            for pid in op.patch_ids:
                patch = self.schedule.program.patch_by_id(pid)
                if not window_verified.get((patch.chain_id, idx), False):
                    pending.append(op)
        return pending
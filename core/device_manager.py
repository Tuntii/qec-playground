"""DeviceManager — per-round active patches and syndrome emission (SWIPER-SIM)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.schedule import LatticeSurgerySchedule, PatchOpType, ProgramOp
from core.syndrome_graph import generate_window_syndrome_with_truth, true_predecessor_logical


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
    _active_patch_map: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chains:
            self.chains = [
                ChainBlockingState(chain_id=c) for c in range(self.schedule.parallelism)
            ]
        self._refresh_active_patches()

    def _refresh_active_patches(self) -> None:
        """Map chain_id -> active patch_id after merge/split ops."""
        if self.schedule.program and self.schedule.program.patches:
            self._active_patch_map = {
                p.chain_id: p.patch_id
                for p in self.schedule.program.patches
                if p.chain_id < self.schedule.parallelism
            }
            for op in self.schedule.program.ops:
                if op.op_type == PatchOpType.MERGE and op.target_patch_id is not None:
                    for pid in op.patch_ids:
                        patch = self.schedule.program.patch_by_id(pid)
                        self._active_patch_map[patch.chain_id] = op.target_patch_id
        else:
            self._active_patch_map = {c: c for c in range(self.schedule.parallelism)}

    def active_patches_at(self, round_idx: int) -> list[tuple[int, int]]:
        """Return (patch_id, chain_id) pairs active at this round."""
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

    def emit_syndrome(
        self,
        *,
        window_id: int,
        patch_id: int,
        chain_id: int,
        pred_id: int | None,
        pred_verified: bool,
        round_idx: int,
    ) -> PatchSyndrome:
        true_left = true_predecessor_logical(
            pred_id=pred_id,
            pred_verified=pred_verified,
            seed=self.seed,
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
                    chain.cond_wait_rounds += round_idx - chain.block_start
                    chain.blocked = False
                    chain.block_start = None

    def total_conditional_wait_rounds(self) -> int:
        return sum(c.cond_wait_rounds for c in self.chains)

    def blocking_ops_pending_verification(self, window_verified: dict[tuple[int, int], bool]) -> list[ProgramOp]:
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
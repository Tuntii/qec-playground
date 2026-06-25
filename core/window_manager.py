"""WindowBuilder + WindowManager — commit/buffer windows and strategies (SWIPER-SIM behavioral model)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Callable
from typing import Any

import numpy as np

from core.schedule import LatticeSurgerySchedule


class WindowStrategy(str, Enum):
    PARALLEL = "parallel"
    ALIGNED = "aligned"
    SLIDING = "sliding"


class OrderingStrategy(str, Enum):
    SHALLOW_FIRST = "shallow_first"
    DEEP_FIRST = "deep_first"
    GENERATION_ORDER = "generation_order"


@dataclass
class DecodeWindow:
    window_id: int
    chain_id: int
    patch_id: int
    gen_round: int
    index_in_chain: int
    pred_id: int | None
    source_boundary: int = 0
    sink_boundary: int = 0
    appeared: bool = False
    state: str = "pending"
    speculation_depth: int = 0
    speculated: bool = False
    speculation_correct: bool | None = None
    poisoned: bool = False
    decode_remaining: int = 0
    restarts: int = 0
    syndrome_measured: np.ndarray | None = None
    hidden_z: np.ndarray | None = None
    assumed_pred_logical: int | None = None


@dataclass
class WindowBuilder:
    """Assemble decode windows with source/sink boundaries from schedule."""

    schedule: LatticeSurgerySchedule
    interval: int

    def build(self) -> list[DecodeWindow]:
        windows: list[DecodeWindow] = []
        for chain in range(self.schedule.parallelism):
            prev_id: int | None = None
            patch_id = chain
            if self.schedule.program:
                for p in self.schedule.program.patches:
                    if p.chain_id == chain:
                        patch_id = p.patch_id
                        break
            for idx in range(self.schedule.windows_per_chain):
                wid = len(windows)
                windows.append(
                    DecodeWindow(
                        window_id=wid,
                        chain_id=chain,
                        patch_id=patch_id,
                        gen_round=idx * self.interval,
                        index_in_chain=idx,
                        pred_id=prev_id,
                        source_boundary=0 if prev_id is None else prev_id,
                        sink_boundary=wid,
                    )
                )
                prev_id = wid
        return windows


@dataclass
class WindowManager:
    """Manage window lifecycle and strategy-specific appearance timing."""

    schedule: LatticeSurgerySchedule
    strategy: str
    interval: int
    windows: list[DecodeWindow] = field(default_factory=list)
    aligned_barrier: int = 0

    def __post_init__(self) -> None:
        if not self.windows:
            self.windows = WindowBuilder(self.schedule, self.interval).build()
        self._apply_strategy_gen_rounds()

    def _apply_strategy_gen_rounds(self) -> None:
        stride = max(1, self.schedule.slide_stride_rounds)
        if self.strategy == WindowStrategy.SLIDING.value:
            for w in self.windows:
                w.gen_round = w.index_in_chain * max(1, self.interval // stride)
        elif self.strategy == WindowStrategy.ALIGNED.value:
            for w in self.windows:
                w.gen_round = w.index_in_chain * self.interval

    def tick_appearances(
        self,
        round_idx: int,
        *,
        allow: Callable[[DecodeWindow], bool] | None = None,
    ) -> list[DecodeWindow]:
        """Mark windows that appear this round (strategy-aware for aligned)."""
        newly: list[DecodeWindow] = []

        def _allowed(window: DecodeWindow) -> bool:
            return allow(window) if allow is not None else True

        if self.strategy == WindowStrategy.ALIGNED.value:
            target_index = self.aligned_barrier
            if target_index >= self.schedule.windows_per_chain:
                return newly
            if round_idx < target_index * self.interval:
                return newly
            chains_ready = True
            for chain in range(self.schedule.parallelism):
                if target_index > 0:
                    prev_verified = any(
                        w.chain_id == chain
                        and w.index_in_chain == target_index - 1
                        and w.state == "verified"
                        for w in self.windows
                    )
                    if not prev_verified:
                        chains_ready = False
                        break
            if chains_ready:
                for w in self.windows:
                    if (
                        not w.appeared
                        and w.index_in_chain == target_index
                        and _allowed(w)
                    ):
                        w.appeared = True
                        newly.append(w)
                if newly:
                    self.aligned_barrier += 1
        else:
            for w in self.windows:
                if not w.appeared and round_idx >= w.gen_round and _allowed(w):
                    w.appeared = True
                    newly.append(w)
        return newly

    def pred_verified(self, pred_id: int | None) -> bool:
        if pred_id is None:
            return True
        return self.windows[pred_id].state == "verified"

    def compute_speculation_depth(self, window: DecodeWindow) -> int:
        if window.pred_id is None:
            return 0
        pred = self.windows[window.pred_id]
        if pred.state == "verified":
            return 0
        return pred.speculation_depth + 1

    def sort_ready(self, ready: list[DecodeWindow], ordering: str) -> list[DecodeWindow]:
        if ordering == OrderingStrategy.DEEP_FIRST.value:
            return sorted(ready, key=lambda w: (-w.speculation_depth, w.gen_round, w.window_id))
        if ordering == OrderingStrategy.GENERATION_ORDER.value:
            return sorted(ready, key=lambda w: (w.gen_round, w.window_id))
        return sorted(ready, key=lambda w: (w.speculation_depth, w.gen_round, w.window_id))

    def all_verified(self) -> bool:
        return all(w.appeared and w.state == "verified" for w in self.windows)

    def active_windows(self) -> list[DecodeWindow]:
        return [w for w in self.windows if w.appeared and w.state != "verified"]

    def verified_map(self) -> dict[tuple[int, int], bool]:
        return {
            (w.chain_id, w.index_in_chain): w.state == "verified"
            for w in self.windows
            if w.appeared
        }

    def appeared_map(self) -> dict[tuple[int, int], bool]:
        return {
            (w.chain_id, w.index_in_chain): w.appeared
            for w in self.windows
        }

    def adjacent_dependents(self, poisoned_id: int) -> list[DecodeWindow]:
        """Windows whose predecessor boundary is the poisoned window."""
        return [
            w
            for w in self.windows
            if w.pred_id == poisoned_id
            and w.appeared
            and w.state in ("decoding", "verified", "ready")
            and (w.speculated or w.state != "pending")
        ]

    def trace_snapshot(self, round_idx: int) -> dict[str, Any]:
        return {
            "round": round_idx,
            "appeared": sum(1 for w in self.windows if w.appeared),
            "verified": sum(1 for w in self.windows if w.state == "verified"),
            "decoding": sum(1 for w in self.windows if w.state == "decoding"),
            "ready": sum(1 for w in self.windows if w.state == "ready"),
            "speculated": sum(1 for w in self.windows if w.speculated),
        }
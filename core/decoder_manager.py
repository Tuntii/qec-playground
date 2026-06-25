"""DecoderManager + boundary predictor — dispatch, verify, optimistic restart."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.matching_decoder import confirm_speculation_with_matching
from core.window_manager import DecodeWindow, WindowManager


@dataclass
class BoundaryPredictor:
    """Lightweight predecessor-boundary predictor (independent of full decode)."""

    accuracy: float
    seed: int

    def should_speculate(self, rng: np.random.Generator) -> bool:
        return rng.random() < self.accuracy

    def assumed_boundary(self) -> int:
        """Optimistic assumption: predecessor logical is +1 eigenstate (0)."""
        return 0


@dataclass
class DecoderManager:
    """Classical decoder pool: dispatch, verify, optimistic restart."""

    processor_count: int
    decoder_latency_rounds: int
    speculative: bool
    predictor: BoundaryPredictor
    speculation_count: int = 0
    speculation_correct_count: int = 0
    restart_count: int = 0
    ui_window_count: int = 0
    decoder_samples: list[int] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)

    def record_concurrency(self, decoding_now: int) -> None:
        self.decoder_samples.append(decoding_now)

    @property
    def max_concurrent_decoders(self) -> int:
        return max(self.decoder_samples) if self.decoder_samples else 0

    @property
    def average_concurrent_decoders(self) -> float:
        if not self.decoder_samples:
            return 0.0
        return float(np.mean(self.decoder_samples))

    def free_slots(self, decoding_now: int) -> int:
        return max(0, self.processor_count - decoding_now)

    def reset_speculation(self, window: DecodeWindow) -> None:
        window.speculated = False
        window.speculation_correct = None
        window.speculation_depth = 0
        window.syndrome_measured = None
        window.hidden_z = None
        window.poisoned = False

    def try_promote_pending(
        self,
        window: DecodeWindow,
        wm: WindowManager,
        rng: np.random.Generator,
        *,
        syndrome: np.ndarray | None = None,
        hidden_z: np.ndarray | None = None,
    ) -> bool:
        if window.pred_id is None or wm.pred_verified(window.pred_id):
            self.reset_speculation(window)
            return True
        if not self.speculative:
            return False
        if window.restarts > 0:
            return False
        if not self.predictor.should_speculate(rng):
            return False
        window.speculated = True
        window.speculation_depth = wm.compute_speculation_depth(window)
        window.speculation_correct = None
        if syndrome is not None and hidden_z is not None:
            window.syndrome_measured = syndrome
            window.hidden_z = hidden_z
        self.speculation_count += 1
        return True

    def finish_decode(self, window: DecodeWindow, wm: WindowManager) -> str:
        """Complete one decode step; returns action: verified | restart | continue."""
        if window.speculated and self.speculative:
            pred_ok = False
            if window.syndrome_measured is not None and window.hidden_z is not None:
                pred_ok = confirm_speculation_with_matching(
                    window.syndrome_measured,
                    assumed_pred_logical=self.predictor.assumed_boundary(),
                    hidden_z=window.hidden_z,
                )
            if pred_ok:
                self.speculation_correct_count += 1
                self.reset_speculation(window)
                window.state = "verified"
                return "verified"
            self.apply_optimistic_restart(window, wm)
            return "restart"
        self.reset_speculation(window)
        window.state = "verified"
        return "verified"

    def apply_optimistic_restart(self, poisoned: DecodeWindow, wm: WindowManager) -> None:
        """Restart poisoned window and adjacent-boundary dependents only."""
        self.restart_count += 1
        self.ui_window_count += 1
        poisoned.restarts += 1
        poisoned.poisoned = True
        self.reset_speculation(poisoned)
        if wm.pred_verified(poisoned.pred_id):
            poisoned.state = "ready"
        else:
            poisoned.state = "pending"

        for dep in wm.adjacent_dependents(poisoned.window_id):
            if dep.window_id == poisoned.window_id:
                continue
            dep.restarts += 1
            self.reset_speculation(dep)
            dep.state = "pending" if not wm.pred_verified(dep.pred_id) else "ready"

    def dispatch(
        self,
        wm: WindowManager,
        ordering: str,
        round_idx: int,
    ) -> int:
        """Assign ready windows to free decoder slots; returns ui increments."""
        decoding_now = sum(1 for w in wm.windows if w.state == "decoding")
        self.record_concurrency(decoding_now)
        free = self.free_slots(decoding_now)
        ready = [w for w in wm.windows if w.appeared and w.state == "ready"]
        ui_delta = 0
        for window in wm.sort_ready(ready, ordering)[:free]:
            if window.speculated and self.speculative:
                ui_delta += 1
            window.state = "decoding"
            window.decode_remaining = self.decoder_latency_rounds
        if ui_delta:
            self.ui_window_count += ui_delta
        self.trace.append(
            {
                "round": round_idx,
                "dispatched": min(len(ready), free),
                "decoding": decoding_now + min(len(ready), free),
            }
        )
        return ui_delta
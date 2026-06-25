"""DecoderManager + boundary predictor — dispatch, verify, optimistic restart."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.device_manager import DeviceManager
from core.matching_decoder import confirm_speculation_with_matching
from core.syndrome_graph import true_predecessor_logical
from core.window_manager import DecodeWindow, WindowManager


@dataclass
class BoundaryPredictor:
    """Lightweight predecessor-boundary predictor (independent of full decode)."""

    accuracy: float
    seed: int

    def should_speculate(self, rng: np.random.Generator) -> bool:
        """Paper slider: probability of attempting speculation on unverified deps."""
        return rng.random() < self.accuracy

    def predict_boundary(self, true_logical: int, rng: np.random.Generator) -> int:
        """Predict predecessor logical; correct with probability ``accuracy``."""
        true_bit = int(true_logical) % 2
        if rng.random() < self.accuracy:
            return true_bit
        return 1 - true_bit


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
        window.assumed_pred_logical = None
        window.poisoned = False

    def try_promote_pending(
        self,
        window: DecodeWindow,
        wm: WindowManager,
        device: DeviceManager,
        rng: np.random.Generator,
        *,
        round_idx: int,
    ) -> bool:
        if device.blocks_window_progress(
            window,
            speculative=self.speculative,
            speculated=window.speculated,
        ):
            return False
        if window.pred_id is None or wm.pred_verified(window.pred_id):
            self.reset_speculation(window)
            return True
        if not self.speculative:
            return False
        if window.restarts > 0:
            return False
        if not self.predictor.should_speculate(rng):
            return False

        true_left = true_predecessor_logical(
            pred_id=window.pred_id,
            pred_verified=False,
            seed=self.predictor.seed,
        )
        assumed = self.predictor.predict_boundary(true_left, rng)
        patch_id = device.patch_id_for_chain(round_idx, window.chain_id)
        synd_obj = device.emit_syndrome(
            window_id=window.window_id,
            patch_id=patch_id,
            chain_id=window.chain_id,
            pred_id=window.pred_id,
            pred_verified=False,
            round_idx=round_idx,
            true_pred_logical=true_left,
        )
        window.speculated = True
        window.assumed_pred_logical = assumed
        window.speculation_depth = wm.compute_speculation_depth(window)
        window.speculation_correct = None
        window.syndrome_measured = synd_obj.syndrome
        window.hidden_z = synd_obj.hidden_z
        self.speculation_count += 1
        return True

    def finish_decode(self, window: DecodeWindow, wm: WindowManager) -> str:
        """Complete one decode step; returns action: verified | restart | continue."""
        if window.speculated and self.speculative:
            pred_ok = False
            if window.syndrome_measured is not None and window.hidden_z is not None:
                assumed = (
                    0
                    if window.assumed_pred_logical is None
                    else int(window.assumed_pred_logical) % 2
                )
                pred_ok = confirm_speculation_with_matching(
                    window.syndrome_measured,
                    assumed_pred_logical=assumed,
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
        device: DeviceManager,
        ordering: str,
        round_idx: int,
    ) -> int:
        """Assign ready windows to free decoder slots; returns ui increments."""
        decoding_now = sum(1 for w in wm.windows if w.state == "decoding")
        self.record_concurrency(decoding_now)
        free = self.free_slots(decoding_now)
        ready = [
            w
            for w in wm.windows
            if w.appeared
            and w.state == "ready"
            and not device.blocks_window_progress(
                w,
                speculative=self.speculative,
                speculated=w.speculated,
            )
        ]
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
                "blocked_chains": sum(1 for c in device.chains if c.blocked),
            }
        )
        return ui_delta
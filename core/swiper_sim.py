"""Round-stepped speculative window decoder model (Li & Martonosi, arXiv:2606.24048).

First open-source lightweight implementation of the paper's analysis scheduling
mechanics: window generation, pending/ready/decoding/verified states, predecessor
speculation with misprediction restart, processor-limited dispatch with ordering,
and blocking conditional-wait accounting.

Distinct from the full SWIPER-SIM in jviszlai/swiper (ISCA 2025 SWIPER).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from core.schedule import LatticeSurgerySchedule


class OrderingStrategy(str, Enum):
    SHALLOW_FIRST = "shallow_first"
    DEEP_FIRST = "deep_first"
    GENERATION_ORDER = "generation_order"


@dataclass(frozen=True)
class SwiperConfig:
    processor_count: int = 4
    cycle_time_us: float = 1.0
    speculation_accuracy: float = 0.9
    decoder_latency_rounds: int = 2
    ordering_strategy: str = OrderingStrategy.SHALLOW_FIRST.value
    speculative: bool = True
    seed: int = 42


@dataclass
class _Window:
    window_id: int
    chain_id: int
    gen_round: int
    index_in_chain: int
    pred_id: int | None
    appeared: bool = False
    state: str = "pending"
    speculation_depth: int = 0
    speculated: bool = False
    speculation_correct: bool | None = None
    decode_remaining: int = 0
    verify_remaining: int = 0
    restarts: int = 0


@dataclass
class _ChainState:
    chain_id: int
    blocked: bool = False
    block_start: int | None = None
    cond_wait_rounds: int = 0


def _build_windows(schedule: LatticeSurgerySchedule, interval: int) -> list[_Window]:
    windows: list[_Window] = []
    for chain in range(schedule.parallelism):
        prev_id: int | None = None
        for idx in range(schedule.windows_per_chain):
            wid = len(windows)
            windows.append(
                _Window(
                    window_id=wid,
                    chain_id=chain,
                    gen_round=idx * interval,
                    index_in_chain=idx,
                    pred_id=prev_id,
                )
            )
            prev_id = wid
    return windows


def _pred_verified(windows: list[_Window], pred_id: int | None) -> bool:
    if pred_id is None:
        return True
    return windows[pred_id].state == "verified"


def _compute_speculation_depth(windows: list[_Window], window: _Window) -> int:
    if window.pred_id is None:
        return 0
    pred = windows[window.pred_id]
    if pred.state == "verified":
        return 0
    return pred.speculation_depth + 1


def _sort_ready(ready: list[_Window], strategy: str) -> list[_Window]:
    if strategy == OrderingStrategy.DEEP_FIRST.value:
        return sorted(ready, key=lambda w: (-w.speculation_depth, w.gen_round, w.window_id))
    if strategy == OrderingStrategy.GENERATION_ORDER.value:
        return sorted(ready, key=lambda w: (w.gen_round, w.window_id))
    return sorted(ready, key=lambda w: (w.speculation_depth, w.gen_round, w.window_id))


def _all_windows_verified(windows: list[_Window]) -> bool:
    return all(w.appeared and w.state == "verified" for w in windows)


def _safety_round_limit(schedule: LatticeSurgerySchedule, config: SwiperConfig, interval: int) -> int:
    """Generous cap — completion is detected explicitly; this only guards runaway loops."""
    total = schedule.total_windows()
    restart_budget = max(8, int(4 / max(config.speculation_accuracy, 0.05)))
    per_window = (config.decoder_latency_rounds + 2) * restart_budget
    return (
        schedule.windows_per_chain * interval * 8
        + total * per_window
        + config.decoder_latency_rounds * 20
    )


def _mode_metrics(
    *,
    total_time: int,
    backlog_samples: list[int],
    chain_cond_wait: int,
    ui_window_count: int,
    restart_count: int,
    speculation_count: int,
    speculation_correct_count: int,
    parallelism: int,
    cycle_time_us: float,
    completed: bool,
    windows_verified: int,
    total_windows: int,
) -> dict[str, float]:
    avg_cond_rounds = chain_cond_wait / max(1, parallelism)
    return {
        "total_decoding_time_us": float(total_time) * cycle_time_us,
        "average_window_backlog": float(np.mean(backlog_samples)) if backlog_samples else 0.0,
        "average_conditional_wait_time_us": avg_cond_rounds * cycle_time_us,
        "ui_window_count": float(ui_window_count),
        "restart_count": float(restart_count),
        "speculation_count": float(speculation_count),
        "speculation_accuracy_rate": (
            speculation_correct_count / speculation_count if speculation_count else 1.0
        ),
        "completed": float(completed),
        "windows_verified": float(windows_verified),
        "total_windows": float(total_windows),
    }


def _reset_speculation(window: _Window) -> None:
    window.speculated = False
    window.speculation_correct = None
    window.speculation_depth = 0


def _handle_mis_speculation(
    window: _Window,
    windows: list[_Window],
    *,
    restart_count: int,
    ui_window_count: int,
) -> tuple[int, int]:
    """Abort failed speculation; wait for real predecessor before re-decoding."""
    restart_count += 1
    ui_window_count += 1
    window.restarts += 1
    _reset_speculation(window)
    if _pred_verified(windows, window.pred_id):
        window.state = "ready"
    else:
        window.state = "pending"
    return restart_count, ui_window_count


def _try_promote_pending(
    window: _Window,
    windows: list[_Window],
    config: SwiperConfig,
    rng: np.random.Generator,
    counters: dict[str, int],
) -> bool:
    if window.pred_id is None or _pred_verified(windows, window.pred_id):
        _reset_speculation(window)
        return True
    if not config.speculative:
        return False
    # After a failed speculation, wait for the real predecessor — do not re-speculate.
    if window.restarts > 0:
        return False
    # Predictor accuracy gates whether we speculate early on an unverified predecessor.
    if rng.random() >= config.speculation_accuracy:
        return False
    window.speculated = True
    window.speculation_depth = _compute_speculation_depth(windows, window)
    window.speculation_correct = None
    counters["speculation_count"] += 1
    return True


def run_swiper_simulation(
    schedule: LatticeSurgerySchedule,
    config: SwiperConfig,
) -> dict[str, Any]:
    """Round-stepped speculative window decoder with processor queue and ordering."""
    if config.processor_count < 1:
        raise ValueError("processor_count must be >= 1")
    if not 0.0 <= config.speculation_accuracy <= 1.0:
        raise ValueError("speculation_accuracy must be in [0, 1]")

    rng = np.random.default_rng(config.seed)
    interval = max(1, int(round(config.cycle_time_us)))
    windows = _build_windows(schedule, interval)
    chains = [_ChainState(chain_id=c) for c in range(schedule.parallelism)]

    backlog_samples: list[int] = []
    ui_window_count = 0
    restart_count = 0
    counters = {"speculation_count": 0, "speculation_correct_count": 0}

    safety_limit = _safety_round_limit(schedule, config, interval)
    t = 0
    completed = False

    while t < safety_limit:
        for window in windows:
            if not window.appeared and t >= window.gen_round:
                window.appeared = True

        for chain in chains:
            if not chain.blocked:
                for window in windows:
                    if (
                        window.chain_id == chain.chain_id
                        and window.appeared
                        and window.index_in_chain == schedule.blocking_window_index
                    ):
                        dep_idx = schedule.blocking_window_index - 1
                        dep_window = next(
                            w
                            for w in windows
                            if w.chain_id == chain.chain_id and w.index_in_chain == dep_idx
                        )
                        if dep_window.state != "verified":
                            chain.blocked = True
                            chain.block_start = t
                        break
            elif chain.block_start is not None:
                dep_idx = schedule.blocking_window_index - 1
                dep_window = next(
                    w
                    for w in windows
                    if w.chain_id == chain.chain_id and w.index_in_chain == dep_idx
                )
                if dep_window.state == "verified":
                    chain.cond_wait_rounds += t - chain.block_start
                    chain.blocked = False
                    chain.block_start = None

        for window in windows:
            if window.state == "decoding":
                window.decode_remaining -= 1
                if window.decode_remaining <= 0:
                    if window.speculated and config.speculative:
                        pred_ok = _pred_verified(windows, window.pred_id)
                        if pred_ok:
                            counters["speculation_correct_count"] += 1
                            window.state = "verified"
                            _reset_speculation(window)
                        else:
                            restart_count, ui_window_count = _handle_mis_speculation(
                                window,
                                windows,
                                restart_count=restart_count,
                                ui_window_count=ui_window_count,
                            )
                    else:
                        window.state = "verified"
                        _reset_speculation(window)

        for window in windows:
            if window.appeared and window.state == "pending":
                if _try_promote_pending(window, windows, config, rng, counters):
                    window.state = "ready"

        decoding_now = sum(1 for w in windows if w.state == "decoding")
        free_slots = max(0, config.processor_count - decoding_now)
        ready = [w for w in windows if w.appeared and w.state == "ready"]
        for window in _sort_ready(ready, config.ordering_strategy)[:free_slots]:
            if window.speculated and config.speculative:
                ui_window_count += 1
            window.state = "decoding"
            window.decode_remaining = config.decoder_latency_rounds

        active = [w for w in windows if w.appeared and w.state != "verified"]
        backlog_samples.append(len(active))

        if _all_windows_verified(windows):
            completed = True
            break
        if not active and all(w.appeared for w in windows):
            break
        t += 1

    windows_verified = sum(1 for w in windows if w.state == "verified")
    total_chain_wait = sum(c.cond_wait_rounds for c in chains)
    metrics = _mode_metrics(
        total_time=t,
        backlog_samples=backlog_samples,
        chain_cond_wait=total_chain_wait,
        ui_window_count=ui_window_count,
        restart_count=restart_count,
        speculation_count=counters["speculation_count"],
        speculation_correct_count=counters["speculation_correct_count"],
        parallelism=schedule.parallelism,
        cycle_time_us=config.cycle_time_us,
        completed=completed,
        windows_verified=windows_verified,
        total_windows=schedule.total_windows(),
    )

    return {
        "schedule": {
            "id": schedule.id,
            "name": schedule.name,
            "parallelism": schedule.parallelism,
            "windows_per_chain": schedule.windows_per_chain,
            "blocking_window_index": schedule.blocking_window_index,
        },
        "config": {
            "processor_count": config.processor_count,
            "cycle_time_us": config.cycle_time_us,
            "speculation_accuracy": config.speculation_accuracy,
            "decoder_latency_rounds": config.decoder_latency_rounds,
            "ordering_strategy": config.ordering_strategy,
            "speculative": config.speculative,
            "seed": config.seed,
        },
        "metrics": metrics,
        "completed": completed,
    }


def compare_speculative_modes(
    schedule: LatticeSurgerySchedule,
    base_config: SwiperConfig,
) -> dict[str, Any]:
    spec_cfg = SwiperConfig(
        processor_count=base_config.processor_count,
        cycle_time_us=base_config.cycle_time_us,
        speculation_accuracy=base_config.speculation_accuracy,
        decoder_latency_rounds=base_config.decoder_latency_rounds,
        ordering_strategy=base_config.ordering_strategy,
        speculative=True,
        seed=base_config.seed,
    )
    nonspec_cfg = SwiperConfig(
        processor_count=base_config.processor_count,
        cycle_time_us=base_config.cycle_time_us,
        speculation_accuracy=base_config.speculation_accuracy,
        decoder_latency_rounds=base_config.decoder_latency_rounds,
        ordering_strategy=base_config.ordering_strategy,
        speculative=False,
        seed=base_config.seed,
    )
    speculative = run_swiper_simulation(schedule, spec_cfg)
    non_speculative = run_swiper_simulation(schedule, nonspec_cfg)
    if not speculative["completed"] or not non_speculative["completed"]:
        raise RuntimeError(
            "Simulation did not complete: "
            f"spec={speculative['metrics']['windows_verified']}/{speculative['metrics']['total_windows']} "
            f"nonspec={non_speculative['metrics']['windows_verified']}/{non_speculative['metrics']['total_windows']}"
        )
    spec_m = speculative["metrics"]
    nonspec_m = non_speculative["metrics"]
    return {
        "speculative": spec_m,
        "non_speculative": nonspec_m,
        "cond_wait_reduction": 1.0 - (
            spec_m["average_conditional_wait_time_us"]
            / max(nonspec_m["average_conditional_wait_time_us"], 1e-9)
        ),
        "time_delta_us": nonspec_m["total_decoding_time_us"] - spec_m["total_decoding_time_us"],
    }
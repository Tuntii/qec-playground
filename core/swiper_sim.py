"""Full SWIPER-SIM behavioral model — round-level lattice surgery program decoding.

DeviceManager (syndrome rounds), WindowManager (parallel/aligned/sliding strategies),
DecoderManager (predictor + matching verify + optimistic restart). Cite arXiv:2606.24048.
Lightweight Python reimplementation of jviszlai/swiper manager behaviors (ISCA 2025).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from core.decoder_manager import BoundaryPredictor, DecoderManager
from core.device_manager import DeviceManager
from core.schedule import LatticeSurgerySchedule
from core.window_manager import OrderingStrategy, WindowManager, WindowStrategy


@dataclass(frozen=True)
class SwiperConfig:
    processor_count: int = 4
    cycle_time_us: float = 1.0
    speculation_accuracy: float = 0.9
    decoder_latency_rounds: int = 2
    ordering_strategy: str = OrderingStrategy.SHALLOW_FIRST.value
    window_strategy: str = WindowStrategy.PARALLEL.value
    speculative: bool = True
    seed: int = 42
    emit_trace: bool = False


def _safety_round_limit(schedule: LatticeSurgerySchedule, config: SwiperConfig, interval: int) -> int:
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
    max_concurrent_decoders: int,
    average_concurrent_decoders: float,
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
        "max_concurrent_decoders": float(max_concurrent_decoders),
        "average_concurrent_decoders": average_concurrent_decoders,
        "completed": float(completed),
        "windows_verified": float(windows_verified),
        "total_windows": float(total_windows),
    }


def run_swiper_simulation(
    schedule: LatticeSurgerySchedule,
    config: SwiperConfig,
) -> dict[str, Any]:
    """Round-stepped SWIPER-SIM with Device/Window/Decoder managers."""
    if config.processor_count < 1:
        raise ValueError("processor_count must be >= 1")
    if not 0.0 <= config.speculation_accuracy <= 1.0:
        raise ValueError("speculation_accuracy must be in [0, 1]")

    rng = np.random.default_rng(config.seed)
    interval = max(1, int(round(config.cycle_time_us)))

    wm = WindowManager(
        schedule=schedule,
        strategy=config.window_strategy,
        interval=interval,
    )
    device = DeviceManager(schedule=schedule, seed=config.seed, cycle_time_us=config.cycle_time_us)
    decoder = DecoderManager(
        processor_count=config.processor_count,
        decoder_latency_rounds=config.decoder_latency_rounds,
        speculative=config.speculative,
        predictor=BoundaryPredictor(accuracy=config.speculation_accuracy, seed=config.seed),
    )

    backlog_samples: list[int] = []
    program_trace: list[dict[str, Any]] = []
    safety_limit = _safety_round_limit(schedule, config, interval)
    t = 0
    completed = False

    while t < safety_limit:
        device.sync_window_patches(wm.windows, t)
        round_ops = device.ops_at_round(t)

        verified_now = wm.verified_map()
        wm.tick_appearances(
            t,
            allow=lambda w: device.appearance_allowed(
                w,
                t,
                speculative=config.speculative,
                window_verified=verified_now,
            ),
        )
        device.update_blocking(
            t,
            window_appeared=wm.appeared_map(),
            window_verified=verified_now,
        )
        device.account_conditional_stalls(
            wm.windows,
            t,
            speculative=config.speculative,
            window_verified=verified_now,
        )

        for window in wm.windows:
            if window.state == "decoding":
                window.decode_remaining -= 1
                if window.decode_remaining <= 0:
                    decoder.finish_decode(window, wm)

        for window in wm.windows:
            if window.appeared and window.state == "pending":
                if decoder.try_promote_pending(window, wm, device, rng, round_idx=t):
                    window.state = "ready"

        decoder.dispatch(wm, device, config.ordering_strategy, t)

        active = wm.active_windows()
        backlog_samples.append(len(active))

        if config.emit_trace:
            snap = wm.trace_snapshot(t)
            snap["round_ops"] = [op.op_type.value for op in round_ops]
            snap["active_patches"] = device.active_patches_at(t)
            snap["blocking_pending"] = len(
                device.blocking_ops_pending_verification(wm.verified_map())
            )
            snap["blocked_chains"] = [c.chain_id for c in device.chains if c.blocked]
            program_trace.append(snap)

        if wm.all_verified():
            completed = True
            break
        if not active and all(w.appeared for w in wm.windows):
            break
        t += 1

    decoder.record_concurrency(sum(1 for w in wm.windows if w.state == "decoding"))
    windows_verified = sum(1 for w in wm.windows if w.state == "verified")
    metrics = _mode_metrics(
        total_time=t,
        backlog_samples=backlog_samples,
        chain_cond_wait=device.total_conditional_wait_rounds(),
        ui_window_count=decoder.ui_window_count,
        restart_count=decoder.restart_count,
        speculation_count=decoder.speculation_count,
        speculation_correct_count=decoder.speculation_correct_count,
        parallelism=schedule.parallelism,
        cycle_time_us=config.cycle_time_us,
        completed=completed,
        windows_verified=windows_verified,
        total_windows=schedule.total_windows(),
        max_concurrent_decoders=decoder.max_concurrent_decoders,
        average_concurrent_decoders=decoder.average_concurrent_decoders,
    )

    result: dict[str, Any] = {
        "schedule": {
            "id": schedule.id,
            "name": schedule.name,
            "parallelism": schedule.parallelism,
            "windows_per_chain": schedule.windows_per_chain,
            "blocking_window_index": schedule.blocking_window_index,
            "has_program": schedule.has_program(),
        },
        "config": {
            "processor_count": config.processor_count,
            "cycle_time_us": config.cycle_time_us,
            "speculation_accuracy": config.speculation_accuracy,
            "decoder_latency_rounds": config.decoder_latency_rounds,
            "ordering_strategy": config.ordering_strategy,
            "window_strategy": config.window_strategy,
            "speculative": config.speculative,
            "seed": config.seed,
        },
        "metrics": metrics,
        "completed": completed,
    }
    if config.emit_trace:
        result["program_trace"] = program_trace
        result["decoder_trace"] = decoder.trace
    return result


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
        window_strategy=base_config.window_strategy,
        speculative=True,
        seed=base_config.seed,
        emit_trace=base_config.emit_trace,
    )
    nonspec_cfg = SwiperConfig(
        processor_count=base_config.processor_count,
        cycle_time_us=base_config.cycle_time_us,
        speculation_accuracy=base_config.speculation_accuracy,
        decoder_latency_rounds=base_config.decoder_latency_rounds,
        ordering_strategy=base_config.ordering_strategy,
        window_strategy=base_config.window_strategy,
        speculative=False,
        seed=base_config.seed,
        emit_trace=base_config.emit_trace,
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
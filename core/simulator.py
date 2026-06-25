"""Primary simulation entry — full SWIPER-SIM behavioral model (Li & Martonosi).

Public API: run_simulation() drives Device/Window/Decoder managers in core/swiper_sim.py.
Cite arXiv:2606.24048 when using results.
"""

from __future__ import annotations

from typing import Any

from core.schedule import LatticeSurgerySchedule, default_three_t_injection, load_schedule_by_id
from core.swiper_sim import SwiperConfig, compare_speculative_modes, run_swiper_simulation


def run_simulation(
    *,
    schedule: LatticeSurgerySchedule | None = None,
    schedule_id: str | None = None,
    processor_count: int = 4,
    cycle_time_us: float = 1.0,
    speculation_accuracy: float = 0.9,
    decoder_latency_rounds: int = 2,
    ordering_strategy: str = "shallow_first",
    window_strategy: str = "parallel",
    speculative: bool | None = None,
    compare_modes: bool = True,
    emit_trace: bool = False,
    seed: int = 42,
    # Legacy kwargs ignored (GKP path removed from primary API).
    **_: Any,
) -> dict[str, Any]:
    """
    Run the paper-faithful round-stepped simulator.

    When ``compare_modes`` is True (default), returns speculative and non-speculative
    metrics side-by-side. Otherwise runs a single mode (``speculative`` flag).
    """
    sched = schedule
    if sched is None:
        sched = load_schedule_by_id(schedule_id) if schedule_id else default_three_t_injection()

    base = SwiperConfig(
        processor_count=processor_count,
        cycle_time_us=cycle_time_us,
        speculation_accuracy=speculation_accuracy,
        decoder_latency_rounds=decoder_latency_rounds,
        ordering_strategy=ordering_strategy,
        window_strategy=window_strategy,
        speculative=True,
        seed=seed,
        emit_trace=emit_trace,
    )

    if compare_modes:
        comparison = compare_speculative_modes(sched, base)
        return {
            "schedule": sched,
            "comparison": comparison,
            "speculative": comparison["speculative"],
            "non_speculative": comparison["non_speculative"],
            "completed": bool(
                comparison["speculative"].get("completed")
                and comparison["non_speculative"].get("completed")
            ),
            "params": {
                "processor_count": processor_count,
                "cycle_time_us": cycle_time_us,
                "speculation_accuracy": speculation_accuracy,
                "decoder_latency_rounds": decoder_latency_rounds,
                "ordering_strategy": ordering_strategy,
                "window_strategy": window_strategy,
                "seed": seed,
            },
        }

    mode_spec = True if speculative is None else speculative
    cfg = SwiperConfig(
        processor_count=processor_count,
        cycle_time_us=cycle_time_us,
        speculation_accuracy=speculation_accuracy,
        decoder_latency_rounds=decoder_latency_rounds,
        ordering_strategy=ordering_strategy,
        window_strategy=window_strategy,
        speculative=mode_spec,
        seed=seed,
        emit_trace=emit_trace,
    )
    run = run_swiper_simulation(sched, cfg)
    return {
        "schedule": sched,
        "metrics": run["metrics"],
        "params": run["config"],
    }
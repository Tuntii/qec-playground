"""Backward-compatible decoder API with syndrome-graph matching (Li & Martonosi).

Not the full SWIPER-SIM in jviszlai/swiper (ISCA 2025 SWIPER).
"""

from __future__ import annotations

from typing import Any

from core.schedule import default_three_t_injection
from core.swiper_sim import SwiperConfig, compare_speculative_modes, run_swiper_simulation


def compare_decoders(**kwargs: Any) -> dict[str, Any]:
    """Compare speculative vs non-speculative modes (legacy name)."""
    schedule = kwargs.pop("schedule", None) or default_three_t_injection()
    config = SwiperConfig(
        processor_count=int(kwargs.get("processor_count", 4)),
        cycle_time_us=float(kwargs.get("cycle_time_us", 1.0)),
        speculation_accuracy=float(kwargs.get("speculation_accuracy", 0.9)),
        decoder_latency_rounds=int(kwargs.get("decoder_latency_rounds", 2)),
        ordering_strategy=str(kwargs.get("ordering_strategy", "shallow_first")),
        seed=int(kwargs.get("seed", 42)),
    )
    comp = compare_speculative_modes(schedule, config)
    return {
        "speculative": comp["speculative"],
        "naive": comp["non_speculative"],
        "wait_reduction": comp["cond_wait_reduction"],
        "success_delta": 0.0,
    }


def simulate_speculative_decoder(**kwargs: Any) -> dict[str, float]:
    schedule = kwargs.pop("schedule", None) or default_three_t_injection()
    cfg = SwiperConfig(speculative=True, seed=int(kwargs.get("seed", 42)))
    return run_swiper_simulation(schedule, cfg)["metrics"]


def simulate_naive_decoder(**kwargs: Any) -> dict[str, float]:
    schedule = kwargs.pop("schedule", None) or default_three_t_injection()
    cfg = SwiperConfig(speculative=False, seed=int(kwargs.get("seed", 42)))
    return run_swiper_simulation(schedule, cfg)["metrics"]
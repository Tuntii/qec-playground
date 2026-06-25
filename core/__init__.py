"""QEC-Playground core — Li & Martonosi round-stepped speculative window decoder."""

from core.legacy_gkp import GKPSyndromeShot, simulate_gkp_logical_errors
from core.schedule import LatticeSurgerySchedule, default_three_t_injection
from core.simulator import run_simulation
from core.swiper_sim import SwiperConfig, compare_speculative_modes, run_swiper_simulation

__all__ = [
    "GKPSyndromeShot",
    "LatticeSurgerySchedule",
    "SwiperConfig",
    "compare_speculative_modes",
    "default_three_t_injection",
    "run_simulation",
    "run_swiper_simulation",
    "simulate_gkp_logical_errors",
]
"""QEC-Playground core — full SWIPER-SIM behavioral model (Li & Martonosi)."""

from core.decoder_manager import BoundaryPredictor, DecoderManager
from core.device_manager import DeviceManager
from core.matching_decoder import matching_decode, verify_window_speculation
from core.schedule import LatticeSurgerySchedule, default_three_t_injection, merge_split_example
from core.simulator import run_simulation
from core.swiper_sim import SwiperConfig, compare_speculative_modes, run_swiper_simulation
from core.syndrome_graph import SyndromeGraph, build_syndrome_graph, generate_window_syndrome
from core.window_manager import WindowBuilder, WindowManager, WindowStrategy

__all__ = [
    "BoundaryPredictor",
    "DecoderManager",
    "DeviceManager",
    "GKPSyndromeShot",
    "LatticeSurgerySchedule",
    "SyndromeGraph",
    "SwiperConfig",
    "WindowBuilder",
    "WindowManager",
    "WindowStrategy",
    "build_syndrome_graph",
    "generate_window_syndrome",
    "matching_decode",
    "compare_speculative_modes",
    "default_three_t_injection",
    "merge_split_example",
    "run_simulation",
    "run_swiper_simulation",
    "simulate_gkp_logical_errors",
    "verify_window_speculation",
]

_LEGACY_EXPORTS = frozenset({"GKPSyndromeShot", "simulate_gkp_logical_errors"})


def __getattr__(name: str):
    if name in _LEGACY_EXPORTS:
        from core.legacy_gkp import GKPSyndromeShot, simulate_gkp_logical_errors

        return GKPSyndromeShot if name == "GKPSyndromeShot" else simulate_gkp_logical_errors
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
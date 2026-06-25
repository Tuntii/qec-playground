"""Shared simulation parameters for Streamlit UI and CLI (no Streamlit dependency)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from ui.schedule_loader import ScheduleTemplate, load_template_by_id

ORDERING_CHOICES = ("shallow_first", "deep_first", "generation_order")
DEFAULT_SCHEDULE_ID = "three_t_injection"


@dataclass(frozen=True)
class SimulationParams:
    processor_count: int
    cycle_time_us: float
    speculation_accuracy: float
    decoder_latency_rounds: int
    ordering_strategy: str
    seed: int
    schedule_id: str
    schedule_name: str


def default_cli_params() -> SimulationParams:
    """Paper-default headless parameters (three parallel T-injection, fast gates)."""
    template = load_template_by_id(DEFAULT_SCHEDULE_ID)
    return SimulationParams(
        processor_count=template.default_processor_count,
        cycle_time_us=template.default_cycle_time_us,
        speculation_accuracy=template.default_speculation_accuracy,
        decoder_latency_rounds=template.default_decoder_latency_rounds,
        ordering_strategy=template.default_ordering_strategy,
        seed=42,
        schedule_id=template.id,
        schedule_name=template.name,
    )


def params_from_query(query: dict[str, Any], template: ScheduleTemplate) -> SimulationParams:
    return SimulationParams(
        processor_count=int(query.get("proc", template.default_processor_count)),
        cycle_time_us=float(query.get("cycle", template.default_cycle_time_us)),
        speculation_accuracy=float(query.get("specacc", template.default_speculation_accuracy)),
        decoder_latency_rounds=int(query.get("latency", template.default_decoder_latency_rounds)),
        ordering_strategy=str(query.get("order", template.default_ordering_strategy)),
        seed=int(query.get("seed", 42)),
        schedule_id=str(query.get("schedule", template.id)),
        schedule_name=template.name,
    )


def to_run_kwargs(params: SimulationParams) -> dict[str, Any]:
    return {
        "schedule_id": params.schedule_id,
        "processor_count": params.processor_count,
        "cycle_time_us": params.cycle_time_us,
        "speculation_accuracy": params.speculation_accuracy,
        "decoder_latency_rounds": params.decoder_latency_rounds,
        "ordering_strategy": params.ordering_strategy,
        "seed": params.seed,
        "compare_modes": True,
    }


def build_cli_parser() -> argparse.ArgumentParser:
    defaults = default_cli_params()
    parser = argparse.ArgumentParser(
        description="QEC-Playground Li & Martonosi round-stepped headless simulation (arXiv:2606.24048)",
    )
    parser.add_argument(
        "--processors",
        "--proc",
        dest="processor_count",
        type=int,
        default=defaults.processor_count,
        help="Decoder processor count (default: %(default)s)",
    )
    parser.add_argument(
        "--cycle-time-us",
        type=float,
        choices=(1.0, 2.0),
        default=defaults.cycle_time_us,
        help="Gate cycle time in microseconds: 1.0 fast, 2.0 slow (default: %(default)s)",
    )
    parser.add_argument(
        "--spec-acc",
        dest="speculation_accuracy",
        type=float,
        default=defaults.speculation_accuracy,
        help="Speculation accuracy in [0, 1] (default: %(default)s)",
    )
    parser.add_argument(
        "--decoder-latency",
        dest="decoder_latency_rounds",
        type=int,
        default=defaults.decoder_latency_rounds,
        help="Decoder latency in rounds (default: %(default)s)",
    )
    parser.add_argument(
        "--ordering",
        choices=ORDERING_CHOICES,
        default=defaults.ordering_strategy,
        help="Processor queue ordering strategy (default: %(default)s)",
    )
    parser.add_argument(
        "--schedule",
        dest="schedule_id",
        default=defaults.schedule_id,
        help="Lattice surgery schedule template id (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=defaults.seed,
        help="Random seed (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print full simulation result as JSON after the text report",
    )
    return parser


def parse_cli_argv(argv: list[str]) -> tuple[SimulationParams, bool]:
    """Parse CLI flags into SimulationParams and whether to emit JSON."""
    args = build_cli_parser().parse_args(argv)
    template = load_template_by_id(args.schedule_id)
    params = SimulationParams(
        processor_count=int(args.processor_count),
        cycle_time_us=float(args.cycle_time_us),
        speculation_accuracy=float(args.speculation_accuracy),
        decoder_latency_rounds=int(args.decoder_latency_rounds),
        ordering_strategy=str(args.ordering),
        seed=int(args.seed),
        schedule_id=template.id,
        schedule_name=template.name,
    )
    return params, bool(args.json)
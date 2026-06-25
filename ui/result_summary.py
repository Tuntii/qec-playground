"""Shared formatting for CLI and Streamlit — Li & Martonosi (arXiv:2606.24048).

Formats the four primary paper metrics: total decoding time, window backlog,
conditional wait, and UI window count for speculative vs non-speculative modes.
"""

from __future__ import annotations

from typing import Any

from ui.sim_params import default_cli_params, to_run_kwargs

PAPER_TITLE = "An Analysis of Speculative Window Decoders for Quantum Error Correction"
PAPER_AUTHORS = "Jocelyn Li and Margaret Martonosi"
PAPER_ARXIV = "arXiv:2606.24048"

DEFAULT_HEADLESS_SIMULATION_KWARGS: dict[str, Any] = to_run_kwargs(default_cli_params())


def result_metric_values(result: dict[str, Any]) -> dict[str, str]:
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    return {
        "Spec total decode time (µs)": f"{spec['total_decoding_time_us']:.1f}",
        "Non-spec total decode time (µs)": f"{nonspec['total_decoding_time_us']:.1f}",
        "Spec avg backlog": f"{spec['average_window_backlog']:.2f}",
        "Spec avg cond wait (µs)": f"{spec['average_conditional_wait_time_us']:.2f}",
    }


def format_cli_report(result: dict[str, Any]) -> str:
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    comp = result["comparison"]
    sched = result.get("schedule")
    sched_name = sched.name if hasattr(sched, "name") else str(sched)
    params = result.get("params", {})
    lines = [
        "QEC-Playground Simulation Results",
        f"Paper: {PAPER_TITLE}",
        f"Authors: {PAPER_AUTHORS} ({PAPER_ARXIV})",
        "=" * 40,
        f"Schedule: {sched_name}",
        f"Processors: {params.get('processor_count', '?')}",
        f"Cycle time: {params.get('cycle_time_us', '?')} µs",
        f"Speculation accuracy: {params.get('speculation_accuracy', 0):.2f}",
        f"Ordering: {params.get('ordering_strategy', '?')}",
        "",
        "Speculative decoder",
        f"  Total decoding time:   {spec['total_decoding_time_us']:.1f} µs",
        f"  Average window backlog:{spec['average_window_backlog']:.2f}",
        f"  Avg conditional wait:    {spec['average_conditional_wait_time_us']:.2f} µs",
        f"  UI window count:       {spec['ui_window_count']:.0f}",
        f"  Speculation count:     {spec.get('speculation_count', 0):.0f}",
        f"  Realized speculation rate: {spec.get('speculation_accuracy_rate', 0):.1%}",
        f"  Restart count:           {spec.get('restart_count', 0):.0f}",
        "",
        "Non-speculative decoder",
        f"  Total decoding time:   {nonspec['total_decoding_time_us']:.1f} µs",
        f"  Average window backlog:{nonspec['average_window_backlog']:.2f}",
        f"  Avg conditional wait:    {nonspec['average_conditional_wait_time_us']:.2f} µs",
        f"  UI window count:       {nonspec['ui_window_count']:.0f}",
        "",
        f"Conditional wait reduction: {comp['cond_wait_reduction']:.1%}",
        f"Time delta (non-spec - spec): {comp['time_delta_us']:.1f} µs",
    ]
    return "\n".join(lines)
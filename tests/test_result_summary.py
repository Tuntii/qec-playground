"""Tests for shared result formatting used by CLI and Streamlit."""

from __future__ import annotations

from core.simulator import run_simulation
from ui.result_summary import (
    PAPER_ARXIV,
    PAPER_AUTHORS,
    PAPER_TITLE,
    format_cli_report,
    result_metric_values,
)


def test_result_metric_values_match_cli_report(capsys):
    result = run_simulation(seed=7)
    metrics = result_metric_values(result)
    report = format_cli_report(result)
    print(f"metrics: {metrics}")
    assert metrics["Spec avg cond wait (µs)"] in report
    comp = result["comparison"]
    assert f"{comp['cond_wait_reduction']:.1%}" in report
    assert "QEC-Playground Simulation Results" in report
    assert PAPER_TITLE in report
    assert PAPER_AUTHORS in report
    assert PAPER_ARXIV in report


def test_format_cli_report_contains_decoder_sections(capsys):
    result = run_simulation(seed=1)
    report = format_cli_report(result)
    print(f"report_lines: {len(report.splitlines())}")
    assert "Speculative decoder" in report
    assert "Non-speculative decoder" in report
    assert "Conditional wait reduction" in report
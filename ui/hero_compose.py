"""Compose a dashboard-style hero figure mimicking the Streamlit results layout."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.visualizations import build_all_charts


def build_dashboard_hero_figure(result: dict[str, Any]) -> go.Figure:
    """2×2 dashboard preview: decode time, backlog, conditional wait, UI windows."""
    charts = build_all_charts(result)
    comp = result["comparison"]
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Total decoding time",
            "Average window backlog",
            "Conditional wait",
            "UI window count",
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
        vertical_spacing=0.14,
        horizontal_spacing=0.08,
    )

    for trace in charts["decode_time"].data:
        fig.add_trace(trace, row=1, col=1)
    for trace in charts["backlog"].data:
        fig.add_trace(trace, row=1, col=2)
    for trace in charts["cond_wait"].data:
        fig.add_trace(trace, row=2, col=1)
    for trace in charts["ui_windows"].data:
        fig.add_trace(trace, row=2, col=2)

    spec = result["speculative"]
    fig.update_layout(
        title={
            "text": (
                "QEC-Playground — speculative window decoder dashboard "
                f"(cond wait ↓ {comp['cond_wait_reduction']:.0%}, "
                f"spec backlog {spec['average_window_backlog']:.1f})"
            ),
            "x": 0.5,
        },
        height=720,
        width=1120,
        showlegend=False,
        template="plotly_white",
    )
    return fig
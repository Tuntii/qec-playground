"""Compose a dashboard-style hero figure mimicking the Streamlit results layout."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.visualizations import build_all_charts


def build_dashboard_hero_figure(
    result: dict[str, Any],
    syndromes: list,
) -> go.Figure:
    """2×2 dashboard preview: error rate, heatmap, success, decoder compare."""
    charts = build_all_charts(result, syndromes)
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Error rates",
            "Syndrome heatmap",
            "Success probability",
            "Decoder comparison",
        ),
        specs=[
            [{"type": "bar"}, {"type": "heatmap"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
        vertical_spacing=0.14,
        horizontal_spacing=0.08,
    )

    err = charts["error_rate"]
    for trace in err.data:
        fig.add_trace(trace, row=1, col=1)

    heat = charts["syndrome_heatmap"]
    for trace in heat.data:
        fig.add_trace(trace, row=1, col=2)

    succ = charts["success_probability"]
    for trace in succ.data:
        fig.add_trace(trace, row=2, col=1)

    dec = charts["decoder_comparison"]
    for trace in dec.data:
        fig.add_trace(trace, row=2, col=2)

    gkp = result["gkp"]
    dec_metrics = result["decoder"]
    fig.update_layout(
        title={
            "text": (
                "QEC-Playground — Run Simulation dashboard "
                f"(logical err {gkp['logical_error_rate']:.3f}, "
                f"wait ↓ {dec_metrics['wait_reduction']:.0%})"
            ),
            "x": 0.5,
        },
        height=720,
        width=1120,
        showlegend=False,
        template="plotly_white",
    )
    return fig
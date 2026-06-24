"""Plotly chart builders for QEC-Playground."""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.simulator import GKPSyndromeShot


def syndrome_heatmap_matrix(
    syndromes: list[GKPSyndromeShot],
    bins: int = 12,
) -> tuple[np.ndarray, list[float], list[float]]:
    """Bin syndromes into a 2D histogram (displacement x fidelity)."""
    if not syndromes:
        z = np.zeros((bins, bins))
        return z, [0.0], [1.0]

    disps = [s.displacement for s in syndromes]
    fids = [s.fidelity for s in syndromes]
    disp_edges = np.linspace(min(disps), max(disps) + 1e-9, bins + 1)
    fid_edges = np.linspace(min(fids), max(fids) + 1e-9, bins + 1)

    hist = np.zeros((bins, bins))
    for d, f in zip(disps, fids):
        di = min(bins - 1, int((d - disp_edges[0]) / (disp_edges[-1] - disp_edges[0]) * bins))
        fi = min(bins - 1, int((f - fid_edges[0]) / (fid_edges[-1] - fid_edges[0]) * bins))
        hist[fi, di] += 1

    disp_centers = ((disp_edges[:-1] + disp_edges[1:]) / 2).tolist()
    fid_centers = ((fid_edges[:-1] + fid_edges[1:]) / 2).tolist()
    return hist, disp_centers, fid_centers


def build_syndrome_heatmap(syndromes: list[GKPSyndromeShot]) -> go.Figure:
    """Syndrome heatmap: displacement vs fidelity density."""
    hist, x_centers, y_centers = syndrome_heatmap_matrix(syndromes)
    fig = go.Figure(
        data=go.Heatmap(
            z=hist,
            x=[round(v, 3) for v in x_centers],
            y=[round(v, 3) for v in y_centers],
            colorscale="Viridis",
            colorbar=dict(title="Count"),
        )
    )
    fig.update_layout(
        title="Syndrome heatmap",
        xaxis_title="Displacement",
        yaxis_title="Fidelity",
        height=360,
    )
    return fig


def build_error_rate_chart(result: dict[str, Any]) -> go.Figure:
    """Bar chart of logical and physical error rates."""
    gkp = result["gkp"]
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Physical", "Logical"],
                y=[gkp["physical_error_rate"], gkp["logical_error_rate"]],
                marker_color=["#6366f1", "#ec4899"],
            )
        ]
    )
    fig.update_layout(
        title="Error rates",
        yaxis_title="Rate",
        yaxis=dict(range=[0, min(1.0, max(gkp["physical_error_rate"], gkp["logical_error_rate"]) * 1.3 + 0.01)]),
        height=360,
    )
    return fig


def build_decoder_comparison_chart(result: dict[str, Any]) -> go.Figure:
    """Grouped bar chart: speculative vs naive decoder metrics."""
    dec = result["decoder"]
    spec = dec["speculative"]
    naive = dec["naive"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            name="Speculative",
            x=["Success prob.", "Mean wait"],
            y=[spec["success_probability"], spec["mean_wait_cycles"] / 10],
            marker_color="#22c55e",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Naive",
            x=["Success prob.", "Mean wait"],
            y=[naive["success_probability"], naive["mean_wait_cycles"] / 10],
            marker_color="#f97316",
        )
    )
    fig.update_layout(
        title="Decoder comparison (wait scaled ÷10)",
        barmode="group",
        height=360,
        legend=dict(orientation="h"),
    )
    return fig


def build_success_probability_chart(result: dict[str, Any]) -> go.Figure:
    """Success probability comparison with wait reduction annotation."""
    dec = result["decoder"]
    fig = go.Figure(
        data=go.Bar(
            x=["Speculative", "Naive"],
            y=[
                dec["speculative"]["success_probability"],
                dec["naive"]["success_probability"],
            ],
            marker_color=["#22c55e", "#f97316"],
            text=[
                f"{dec['speculative']['success_probability']:.1%}",
                f"{dec['naive']['success_probability']:.1%}",
            ],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Success probability (wait reduction {dec['wait_reduction']:.0%})",
        yaxis_title="Probability",
        yaxis=dict(range=[0, 1.05]),
        height=360,
    )
    return fig


def build_all_charts(
    result: dict[str, Any],
    syndromes: list[GKPSyndromeShot],
) -> dict[str, go.Figure]:
    """Build all MVP Plotly figures."""
    return {
        "error_rate": build_error_rate_chart(result),
        "syndrome_heatmap": build_syndrome_heatmap(syndromes),
        "decoder_comparison": build_decoder_comparison_chart(result),
        "success_probability": build_success_probability_chart(result),
    }
"""Plotly charts for Li & Martonosi (arXiv:2606.24048) paper metrics."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_decode_time_chart(result: dict[str, Any]) -> go.Figure:
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    fig = go.Figure(
        data=go.Bar(
            x=["Speculative", "Non-speculative"],
            y=[spec["total_decoding_time_us"], nonspec["total_decoding_time_us"]],
            marker_color=["#22c55e", "#f97316"],
            text=[
                f"{spec['total_decoding_time_us']:.0f} µs",
                f"{nonspec['total_decoding_time_us']:.0f} µs",
            ],
            textposition="outside",
        )
    )
    fig.update_layout(title="Total decoding time", yaxis_title="µs", height=360)
    return fig


def build_backlog_chart(result: dict[str, Any]) -> go.Figure:
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    fig = go.Figure(
        data=go.Bar(
            x=["Speculative", "Non-speculative"],
            y=[spec["average_window_backlog"], nonspec["average_window_backlog"]],
            marker_color=["#6366f1", "#ec4899"],
        )
    )
    fig.update_layout(title="Average window backlog", height=360)
    return fig


def build_cond_wait_chart(result: dict[str, Any]) -> go.Figure:
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    comp = result["comparison"]
    fig = go.Figure(
        data=go.Bar(
            x=["Speculative", "Non-speculative"],
            y=[
                spec["average_conditional_wait_time_us"],
                nonspec["average_conditional_wait_time_us"],
            ],
            marker_color=["#0ea5e9", "#a855f7"],
            text=[
                f"{spec['average_conditional_wait_time_us']:.2f}",
                f"{nonspec['average_conditional_wait_time_us']:.2f}",
            ],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Conditional wait (reduction {comp['cond_wait_reduction']:.0%})",
        yaxis_title="µs",
        height=360,
    )
    return fig


def build_ui_windows_chart(result: dict[str, Any]) -> go.Figure:
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    fig = go.Figure(
        data=go.Bar(
            x=["Speculative", "Non-speculative"],
            y=[spec["ui_window_count"], nonspec["ui_window_count"]],
            marker_color=["#14b8a6", "#f43f5e"],
        )
    )
    fig.update_layout(title="UI window count", height=360)
    return fig


def build_all_charts(result: dict[str, Any]) -> dict[str, go.Figure]:
    return {
        "decode_time": build_decode_time_chart(result),
        "backlog": build_backlog_chart(result),
        "cond_wait": build_cond_wait_chart(result),
        "ui_windows": build_ui_windows_chart(result),
    }
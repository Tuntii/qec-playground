"""Streamlit sidebar — arXiv:2606.24048 paper parameters."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ui.schedule_loader import ScheduleTemplate
from ui.sim_params import SimulationParams, params_from_query


def render_sidebar(
    template: ScheduleTemplate,
    query: dict[str, Any] | None = None,
) -> SimulationParams:
    st.sidebar.header("Paper parameters (Li & Martonosi, arXiv:2606.24048)")

    initial = params_from_query(query, template) if query else None
    processor_count = st.sidebar.slider(
        "Decoder processors",
        min_value=1,
        max_value=8,
        value=int(initial.processor_count if initial else template.default_processor_count),
        step=1,
    )
    default_cycle = initial.cycle_time_us if initial else template.default_cycle_time_us
    gate_speed = st.sidebar.selectbox(
        "Gate speed (cycle time)",
        options=[("Fast (1µs)", 1.0), ("Slow (2µs)", 2.0)],
        index=0 if default_cycle <= 1.0 else 1,
        format_func=lambda x: x[0],
    )
    cycle_time_us = float(gate_speed[1])
    speculation_accuracy = st.sidebar.slider(
        "Speculation accuracy",
        min_value=0.0,
        max_value=1.0,
        value=float(initial.speculation_accuracy if initial else template.default_speculation_accuracy),
        step=0.05,
    )
    decoder_latency_rounds = st.sidebar.slider(
        "Decoder latency (rounds)",
        min_value=1,
        max_value=6,
        value=int(initial.decoder_latency_rounds if initial else template.default_decoder_latency_rounds),
        step=1,
    )
    ordering_strategy = st.sidebar.selectbox(
        "Ordering strategy",
        options=[
            ("Shallow speculations first", "shallow_first"),
            ("Deep speculations first", "deep_first"),
            ("Window generation order", "generation_order"),
        ],
        index=_ordering_index(initial or template),
        format_func=lambda x: x[0],
    )[1]
    seed = st.sidebar.number_input(
        "Random seed",
        min_value=0,
        value=int(initial.seed if initial else 42),
        step=1,
    )

    return SimulationParams(
        processor_count=int(processor_count),
        cycle_time_us=cycle_time_us,
        speculation_accuracy=float(speculation_accuracy),
        decoder_latency_rounds=int(decoder_latency_rounds),
        ordering_strategy=str(ordering_strategy),
        seed=int(seed),
        schedule_id=template.id,
        schedule_name=template.name,
    )


def _ordering_index(params: SimulationParams | ScheduleTemplate) -> int:
    strategy = (
        params.ordering_strategy
        if isinstance(params, SimulationParams)
        else params.default_ordering_strategy
    )
    mapping = {"shallow_first": 0, "deep_first": 1, "generation_order": 2}
    return mapping.get(strategy, 0)
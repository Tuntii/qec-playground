"""Streamlit sidebar parameter controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from ui.circuit_loader import CircuitTemplate


@dataclass(frozen=True)
class SimulationParams:
    squeezing_db: float
    noise_p: float
    skip_threshold: float
    shots: int
    window_size: int
    surface_distance: int
    seed: int
    circuit_id: str
    circuit_name: str


def render_sidebar(
    template: CircuitTemplate,
    query: dict[str, Any] | None = None,
) -> SimulationParams:
    """Render MVP sliders and return simulation parameters."""
    st.sidebar.header("Simulation parameters")

    initial = params_from_query(query, template) if query else None
    squeezing_db = st.sidebar.slider(
        "GKP squeezing (dB)",
        min_value=5.0,
        max_value=20.0,
        value=float(initial.squeezing_db if initial else template.default_squeezing_db),
        step=0.5,
    )
    skip_threshold = st.sidebar.slider(
        "Skip threshold",
        min_value=0.0,
        max_value=1.0,
        value=float(initial.skip_threshold if initial else 0.7),
        step=0.05,
    )
    noise_p = st.sidebar.slider(
        "Noise level",
        min_value=0.0,
        max_value=0.15,
        value=float(initial.noise_p if initial else template.default_noise_p),
        step=0.005,
        format="%.3f",
    )
    shots = st.sidebar.slider(
        "Shot count",
        min_value=100,
        max_value=3000,
        value=int(initial.shots if initial else 800),
        step=100,
    )
    seed = st.sidebar.number_input(
        "Random seed",
        min_value=0,
        value=int(initial.seed if initial else 42),
        step=1,
    )

    return SimulationParams(
        squeezing_db=squeezing_db,
        noise_p=noise_p,
        skip_threshold=skip_threshold,
        shots=shots,
        window_size=template.window_size,
        surface_distance=template.surface_distance,
        seed=int(seed),
        circuit_id=template.id,
        circuit_name=template.name,
    )


def params_from_query(query: dict[str, Any], template: CircuitTemplate) -> SimulationParams:
    """Build params from URL query dict (share link restore)."""
    return SimulationParams(
        squeezing_db=float(query.get("sq", template.default_squeezing_db)),
        noise_p=float(query.get("noise", template.default_noise_p)),
        skip_threshold=float(query.get("skip", 0.7)),
        shots=int(query.get("shots", 800)),
        window_size=int(query.get("win", template.window_size)),
        surface_distance=int(query.get("dist", template.surface_distance)),
        seed=int(query.get("seed", 42)),
        circuit_id=str(query.get("circuit", template.id)),
        circuit_name=template.name,
    )
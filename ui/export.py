"""Export helpers: CSV, PNG, shareable config URLs."""

from __future__ import annotations

import base64
import io
import json
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go

from ui.sliders import SimulationParams


def results_to_dataframe(result: dict[str, Any], params: SimulationParams) -> pd.DataFrame:
    """Flatten simulation result into a single-row metrics DataFrame."""
    gkp = result["gkp"]
    dec = result["decoder"]
    row = {
        "circuit_id": params.circuit_id,
        "circuit_name": params.circuit_name,
        "squeezing_db": params.squeezing_db,
        "noise_p": params.noise_p,
        "skip_threshold": params.skip_threshold,
        "shots": params.shots,
        "window_size": params.window_size,
        "surface_distance": params.surface_distance,
        "seed": params.seed,
        "logical_error_rate": gkp["logical_error_rate"],
        "physical_error_rate": gkp["physical_error_rate"],
        "mean_fidelity": gkp["mean_fidelity"],
        "speculative_success": dec["speculative"]["success_probability"],
        "speculative_wait": dec["speculative"]["mean_wait_cycles"],
        "naive_success": dec["naive"]["success_probability"],
        "naive_wait": dec["naive"]["mean_wait_cycles"],
        "wait_reduction": dec["wait_reduction"],
        "success_delta": dec["success_delta"],
    }
    return pd.DataFrame([row])


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """Serialize DataFrame to CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def figure_to_png(fig: go.Figure) -> bytes:
    """Render a Plotly figure to PNG bytes."""
    return fig.to_image(format="png", scale=2)


def build_share_query(params: SimulationParams) -> dict[str, str | int | float]:
    """Build URL query dict for shareable config."""
    return {
        "circuit": params.circuit_id,
        "sq": params.squeezing_db,
        "noise": params.noise_p,
        "skip": params.skip_threshold,
        "shots": params.shots,
        "win": params.window_size,
        "dist": params.surface_distance,
        "seed": params.seed,
    }


def build_share_url(params: SimulationParams, base_url: str = "http://localhost:8501") -> str:
    """Build a shareable URL encoding current simulation parameters."""
    query = build_share_query(params)
    return f"{base_url}?{urlencode(query)}"


def encode_config_payload(params: SimulationParams) -> str:
    """Base64-encoded config blob for clipboard share."""
    payload = json.dumps(build_share_query(params), separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_config_payload(token: str) -> dict[str, Any]:
    """Decode a base64 config blob."""
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    return json.loads(raw.decode("utf-8"))
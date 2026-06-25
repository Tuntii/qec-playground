"""Export helpers: CSV, PNG, shareable config URLs."""

from __future__ import annotations

import base64
import io
import json
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go

from ui.sim_params import SimulationParams


def results_to_dataframe(result: dict[str, Any], params: SimulationParams) -> pd.DataFrame:
    """Flatten simulation result into a single-row metrics DataFrame."""
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    comp = result["comparison"]
    row = {
        "schedule_id": params.schedule_id,
        "schedule_name": params.schedule_name,
        "processor_count": params.processor_count,
        "cycle_time_us": params.cycle_time_us,
        "speculation_accuracy": params.speculation_accuracy,
        "decoder_latency_rounds": params.decoder_latency_rounds,
        "ordering_strategy": params.ordering_strategy,
        "seed": params.seed,
        "spec_total_decoding_time_us": spec["total_decoding_time_us"],
        "spec_average_window_backlog": spec["average_window_backlog"],
        "spec_average_conditional_wait_time_us": spec["average_conditional_wait_time_us"],
        "spec_ui_window_count": spec["ui_window_count"],
        "nonspec_total_decoding_time_us": nonspec["total_decoding_time_us"],
        "nonspec_average_window_backlog": nonspec["average_window_backlog"],
        "nonspec_average_conditional_wait_time_us": nonspec["average_conditional_wait_time_us"],
        "nonspec_ui_window_count": nonspec["ui_window_count"],
        "cond_wait_reduction": comp["cond_wait_reduction"],
        "time_delta_us": comp["time_delta_us"],
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
        "schedule": params.schedule_id,
        "proc": params.processor_count,
        "cycle": params.cycle_time_us,
        "specacc": params.speculation_accuracy,
        "latency": params.decoder_latency_rounds,
        "order": params.ordering_strategy,
        "seed": params.seed,
    }


def default_share_base_url() -> str:
    """Resolve share-link base from QEC_DEMO_BASE_URL or localhost default."""
    import os

    return os.environ.get("QEC_DEMO_BASE_URL", "http://localhost:8501").rstrip("/")


def build_share_url(
    params: SimulationParams,
    base_url: str | None = None,
) -> str:
    """Build a shareable URL encoding current simulation parameters."""
    query = build_share_query(params)
    root = (base_url or default_share_base_url()).rstrip("/")
    return f"{root}?{urlencode(query)}"


def encode_config_payload(params: SimulationParams) -> str:
    """Base64-encoded config blob for clipboard share."""
    payload = json.dumps(build_share_query(params), separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_config_payload(token: str) -> dict[str, Any]:
    """Decode a base64 config blob."""
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    return json.loads(raw.decode("utf-8"))
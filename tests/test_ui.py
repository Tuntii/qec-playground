"""Tests for MVP UI helper modules."""

import pytest

from core.simulator import run_simulation
from ui.circuit_loader import list_templates, load_template_by_id, parse_qasm
from ui.export import (
    build_share_url,
    dataframe_to_csv,
    decode_config_payload,
    encode_config_payload,
    results_to_dataframe,
)
from ui.sliders import SimulationParams, params_from_query
from ui.visualizations import build_all_charts, syndrome_heatmap_matrix


def test_list_templates_returns_five(capsys):
    templates = list_templates()
    print(f"template_count: {len(templates)} names={[t.name for t in templates]}")
    assert len(templates) == 5


def test_load_template_by_id():
    template = load_template_by_id("surface_gkp_d3")
    assert template.surface_distance == 3
    assert template.window_size == 4


def test_parse_qasm_extracts_qubits(capsys):
    qasm = 'OPENQASM 2.0;\nqreg q[16];\n'
    template = parse_qasm(qasm)
    print(f"qasm_distance: {template.surface_distance} window: {template.window_size}")
    assert template.surface_distance >= 3
    assert template.source == "qasm"


def test_parse_qasm_empty_raises():
    with pytest.raises(ValueError):
        parse_qasm("   ")


def test_build_all_charts_from_real_simulation(capsys):
    result = run_simulation(shots=200, seed=123, include_syndromes=True)
    charts = build_all_charts(result, result["syndromes"])
    print(f"charts_count: {len(charts)}")
    assert len(charts) == 4
    assert result["gkp"]["logical_error_rate"] >= 0.0


def test_syndrome_heatmap_matrix_shape():
    result = run_simulation(shots=50, seed=1, include_syndromes=True)
    hist, x_centers, y_centers = syndrome_heatmap_matrix(result["syndromes"], bins=8)
    assert hist.shape == (8, 8)
    assert len(x_centers) == 8


def test_export_csv_and_share_url(capsys):
    result = run_simulation(shots=100, seed=7)
    params = SimulationParams(
        squeezing_db=10.0,
        noise_p=0.02,
        skip_threshold=0.7,
        shots=100,
        window_size=4,
        surface_distance=3,
        seed=7,
        circuit_id="surface_gkp_d3",
        circuit_name="Surface-GKP distance-3",
    )
    df = results_to_dataframe(result, params)
    csv_bytes = dataframe_to_csv(df)
    url = build_share_url(params)
    token = encode_config_payload(params)
    restored = decode_config_payload(token)
    print(f"csv_len: {len(csv_bytes)} share_url_ok: {url.startswith('http')} token_len: {len(token)}")
    assert len(csv_bytes) > 50
    assert url.startswith("http")
    assert len(token) > 10
    assert restored["circuit"] == "surface_gkp_d3"


def test_params_from_query_overrides(capsys):
    template = load_template_by_id("gkp_memory")
    params = params_from_query(
        {"sq": "11.5", "noise": "0.04", "skip": "0.6", "shots": "500", "seed": "99"},
        template,
    )
    print(f"query_params: sq={params.squeezing_db} shots={params.shots}")
    assert params.squeezing_db == 11.5
    assert params.shots == 500
    assert params.seed == 99
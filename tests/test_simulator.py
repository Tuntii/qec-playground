"""Tests for GKP logical error simulation."""

import pytest

from core.metrics import gkp_cell_half_width, gkp_lattice_spacing
from core.simulator import create_finite_gkp_state, run_simulation, simulate_gkp_logical_errors


def test_gkp_state_is_normalized():
    state = create_finite_gkp_state(squeezing_db=10.0, dim=24)
    assert abs(state.norm() - 1.0) < 1e-6


def test_lattice_spacing_matches_cell_width():
    assert gkp_cell_half_width() == gkp_lattice_spacing() / 2


def test_logical_error_rate_in_valid_range(capsys):
    result = simulate_gkp_logical_errors(
        squeezing_db=10.0,
        noise_p=0.01,
        shots=500,
        seed=42,
    )
    print(
        f"GKP rates: logical={result['logical_error_rate']:.4f} "
        f"physical={result['physical_error_rate']:.4f} "
        f"fidelity={result['mean_fidelity']:.4f}"
    )
    assert 0.0 <= result["logical_error_rate"] <= 1.0
    assert 0.0 <= result["physical_error_rate"] <= 1.0
    assert 0.0 <= result["mean_fidelity"] <= 1.0
    assert len(result["syndromes"]) == 500


def test_higher_noise_increases_error_rate(capsys):
    low_noise = simulate_gkp_logical_errors(
        squeezing_db=10.0, noise_p=0.005, shots=800, seed=1
    )
    high_noise = simulate_gkp_logical_errors(
        squeezing_db=10.0, noise_p=0.08, shots=800, seed=1
    )
    print(
        f"noise_sensitivity: low_p=0.005 rate={low_noise['logical_error_rate']:.4f} "
        f"high_p=0.08 rate={high_noise['logical_error_rate']:.4f}"
    )
    assert high_noise["logical_error_rate"] > low_noise["logical_error_rate"]
    assert high_noise["mean_fidelity"] < low_noise["mean_fidelity"]


def test_higher_squeezing_reduces_error_rate(capsys):
    low_squeeze = simulate_gkp_logical_errors(
        squeezing_db=5.0, noise_p=0.03, shots=800, seed=2
    )
    high_squeeze = simulate_gkp_logical_errors(
        squeezing_db=15.0, noise_p=0.03, shots=800, seed=2
    )
    print(
        f"squeeze_sensitivity: 5dB rate={low_squeeze['logical_error_rate']:.4f} "
        f"15dB rate={high_squeeze['logical_error_rate']:.4f}"
    )
    assert high_squeeze["logical_error_rate"] <= low_squeeze["logical_error_rate"]


def test_errors_driven_by_qutip_fidelity(capsys):
    """Physical errors must correlate with per-shot QuTiP fidelity, not a side model."""
    result = simulate_gkp_logical_errors(
        squeezing_db=10.0, noise_p=0.05, shots=200, seed=7
    )
    error_fids = [s.fidelity for s in result["syndromes"] if s.physical_error]
    ok_fids = [s.fidelity for s in result["syndromes"] if not s.physical_error]
    print(
        f"qutip_error_fids: errors={len(error_fids)} ok={len(ok_fids)} "
        f"mean_err_fid={sum(error_fids)/max(len(error_fids),1):.4f}"
    )
    if error_fids and ok_fids:
        assert sum(error_fids) / len(error_fids) < sum(ok_fids) / len(ok_fids)


def test_run_simulation_returns_combined_results(capsys):
    result = run_simulation(
        squeezing_db=10.0,
        noise_p=0.02,
        skip_threshold=0.7,
        shots=300,
        seed=99,
    )
    print(
        f"combined: gkp_rate={result['gkp']['logical_error_rate']:.4f} "
        f"spec_success={result['decoder']['speculative']['success_probability']:.4f} "
        f"naive_wait={result['decoder']['naive']['mean_wait_cycles']:.2f}"
    )
    assert "gkp" in result
    assert "decoder" in result
    assert 0.0 <= result["gkp"]["logical_error_rate"] <= 1.0
    assert "speculative" in result["decoder"]
    assert "naive" in result["decoder"]


def test_invalid_noise_raises():
    with pytest.raises(ValueError):
        simulate_gkp_logical_errors(noise_p=1.5)
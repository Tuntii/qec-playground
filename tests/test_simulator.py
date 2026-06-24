"""Tests for GKP logical error simulation."""

import pytest

from core.simulator import create_finite_gkp_state, run_simulation, simulate_gkp_logical_errors


def test_gkp_state_is_normalized():
    state = create_finite_gkp_state(squeezing_db=10.0, dim=24)
    assert abs(state.norm() - 1.0) < 1e-6


def test_logical_error_rate_in_valid_range():
    result = simulate_gkp_logical_errors(
        squeezing_db=10.0,
        noise_p=0.01,
        shots=500,
        seed=42,
    )
    assert 0.0 <= result["logical_error_rate"] <= 1.0
    assert 0.0 <= result["physical_error_rate"] <= 1.0
    assert 0.0 <= result["mean_fidelity"] <= 1.0


def test_higher_noise_increases_error_rate():
    low_noise = simulate_gkp_logical_errors(
        squeezing_db=10.0, noise_p=0.005, shots=800, seed=1
    )
    high_noise = simulate_gkp_logical_errors(
        squeezing_db=10.0, noise_p=0.08, shots=800, seed=1
    )
    assert high_noise["logical_error_rate"] > low_noise["logical_error_rate"]


def test_higher_squeezing_reduces_error_rate():
    low_squeeze = simulate_gkp_logical_errors(
        squeezing_db=5.0, noise_p=0.03, shots=800, seed=2
    )
    high_squeeze = simulate_gkp_logical_errors(
        squeezing_db=15.0, noise_p=0.03, shots=800, seed=2
    )
    assert high_squeeze["logical_error_rate"] <= low_squeeze["logical_error_rate"]


def test_run_simulation_returns_combined_results():
    result = run_simulation(
        squeezing_db=10.0,
        noise_p=0.02,
        skip_threshold=0.7,
        shots=300,
        seed=99,
    )
    assert "gkp" in result
    assert "decoder" in result
    assert 0.0 <= result["gkp"]["logical_error_rate"] <= 1.0
    assert "speculative" in result["decoder"]
    assert "naive" in result["decoder"]


def test_invalid_noise_raises():
    with pytest.raises(ValueError):
        simulate_gkp_logical_errors(noise_p=1.5)
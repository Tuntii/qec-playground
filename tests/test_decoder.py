"""Tests for speculative window decoder simulation."""

import pytest

from core.decoder import compare_decoders, simulate_naive_decoder, simulate_speculative_decoder
from core.simulator import simulate_gkp_logical_errors


def _syndromes(noise_p: float, shots: int, seed: int):
    return simulate_gkp_logical_errors(
        squeezing_db=10.0, noise_p=noise_p, shots=shots, seed=seed
    )["syndromes"]


def test_speculative_decoder_outputs_in_range(capsys):
    gkp = simulate_gkp_logical_errors(noise_p=0.02, shots=600, seed=10)
    result = simulate_speculative_decoder(
        syndromes=gkp["syndromes"],
        noise_p=0.02,
        skip_threshold=0.6,
        physical_error_rate=gkp["physical_error_rate"],
        seed=10,
    )
    print(
        f"speculative: success={result['success_probability']:.4f} "
        f"wait={result['mean_wait_cycles']:.2f} "
        f"spec_rate={result['speculation_rate']:.4f}"
    )
    assert 0.0 <= result["success_probability"] <= 1.0
    assert result["mean_wait_cycles"] >= 1.0
    assert 0.0 <= result["speculation_rate"] <= 1.0


def test_naive_decoder_never_speculates(capsys):
    gkp = simulate_gkp_logical_errors(noise_p=0.02, shots=400, seed=11)
    result = simulate_naive_decoder(
        syndromes=gkp["syndromes"],
        noise_p=0.02,
        physical_error_rate=gkp["physical_error_rate"],
        seed=11,
    )
    print(f"naive: success={result['success_probability']:.4f} wait={result['mean_wait_cycles']:.2f}")
    assert result["speculation_rate"] == 0.0
    assert result["mean_wait_cycles"] >= 1.0


def test_low_threshold_speculates_more_than_high_threshold(capsys):
    synd = _syndromes(noise_p=0.02, shots=1000, seed=20)
    gkp = simulate_gkp_logical_errors(noise_p=0.02, shots=1000, seed=20)
    low_thr = simulate_speculative_decoder(
        syndromes=synd,
        skip_threshold=0.3,
        noise_p=0.02,
        physical_error_rate=gkp["physical_error_rate"],
        seed=20,
    )
    high_thr = simulate_speculative_decoder(
        syndromes=synd,
        skip_threshold=0.95,
        noise_p=0.02,
        physical_error_rate=gkp["physical_error_rate"],
        seed=20,
    )
    print(
        f"threshold_sensitivity: low_thr_rate={low_thr['speculation_rate']:.4f} "
        f"high_thr_rate={high_thr['speculation_rate']:.4f}"
    )
    assert low_thr["speculation_rate"] >= high_thr["speculation_rate"]


def test_speculative_waits_less_than_naive(capsys):
    gkp = simulate_gkp_logical_errors(noise_p=0.03, shots=800, seed=30)
    comparison = compare_decoders(
        syndromes=gkp["syndromes"],
        noise_p=0.03,
        skip_threshold=0.5,
        physical_error_rate=gkp["physical_error_rate"],
        seed=30,
    )
    spec_wait = comparison["speculative"]["mean_wait_cycles"]
    naive_wait = comparison["naive"]["mean_wait_cycles"]
    print(
        f"decoder_compare: spec_wait={spec_wait:.2f} naive_wait={naive_wait:.2f} "
        f"wait_reduction={comparison['wait_reduction']:.2%}"
    )
    assert spec_wait <= naive_wait
    assert comparison["wait_reduction"] >= 0.0


def test_identical_rolls_across_modes(capsys):
    """Shared dep/success rolls; speculative mode skips waits when confidence high."""
    gkp = simulate_gkp_logical_errors(noise_p=0.04, shots=500, seed=40)
    comparison = compare_decoders(
        syndromes=gkp["syndromes"],
        noise_p=0.04,
        skip_threshold=0.55,
        physical_error_rate=gkp["physical_error_rate"],
        seed=40,
    )
    print(
        f"shared_rolls: spec_success={comparison['speculative']['success_probability']:.4f} "
        f"naive_success={comparison['naive']['success_probability']:.4f} "
        f"spec_wait={comparison['speculative']['mean_wait_cycles']:.2f} "
        f"naive_wait={comparison['naive']['mean_wait_cycles']:.2f}"
    )
    assert comparison["speculative"]["mean_wait_cycles"] < comparison["naive"]["mean_wait_cycles"]
    assert comparison["speculative"]["speculation_rate"] > 0.0


def test_invalid_skip_threshold_raises():
    gkp = simulate_gkp_logical_errors(shots=10, seed=0)
    with pytest.raises(ValueError):
        simulate_speculative_decoder(
            syndromes=gkp["syndromes"],
            skip_threshold=1.5,
        )
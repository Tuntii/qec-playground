"""Tests for speculative window decoder simulation."""

import pytest

from core.decoder import compare_decoders, simulate_naive_decoder, simulate_speculative_decoder


def test_speculative_decoder_outputs_in_range():
    result = simulate_speculative_decoder(
        noise_p=0.02,
        skip_threshold=0.6,
        shots=600,
        base_logical_rate=0.04,
        seed=10,
    )
    assert 0.0 <= result["success_probability"] <= 1.0
    assert result["mean_wait_cycles"] >= 1.0
    assert 0.0 <= result["speculation_rate"] <= 1.0


def test_naive_decoder_never_speculates():
    result = simulate_naive_decoder(
        noise_p=0.02,
        shots=400,
        base_logical_rate=0.04,
        seed=11,
    )
    assert result["speculation_rate"] == 0.0
    assert result["mean_wait_cycles"] >= 1.0


def test_low_threshold_speculates_more_than_high_threshold():
    low_thr = simulate_speculative_decoder(
        skip_threshold=0.3,
        noise_p=0.02,
        shots=1000,
        base_logical_rate=0.05,
        seed=20,
    )
    high_thr = simulate_speculative_decoder(
        skip_threshold=0.95,
        noise_p=0.02,
        shots=1000,
        base_logical_rate=0.05,
        seed=20,
    )
    assert low_thr["speculation_rate"] >= high_thr["speculation_rate"]


def test_speculative_waits_less_than_naive():
    comparison = compare_decoders(
        noise_p=0.03,
        skip_threshold=0.5,
        shots=800,
        base_logical_rate=0.06,
        seed=30,
    )
    spec_wait = comparison["speculative"]["mean_wait_cycles"]
    naive_wait = comparison["naive"]["mean_wait_cycles"]
    assert spec_wait <= naive_wait
    assert comparison["wait_reduction"] >= 0.0


def test_decoder_outputs_differ_between_modes():
    comparison = compare_decoders(
        noise_p=0.04,
        skip_threshold=0.55,
        shots=1000,
        base_logical_rate=0.07,
        seed=40,
    )
    assert (
        comparison["speculative"]["mean_wait_cycles"]
        != comparison["naive"]["mean_wait_cycles"]
        or comparison["speculative"]["success_probability"]
        != comparison["naive"]["success_probability"]
    )


def test_invalid_skip_threshold_raises():
    with pytest.raises(ValueError):
        simulate_speculative_decoder(skip_threshold=1.5)
"""Tests for backward-compatible decoder API."""

from core.decoder import compare_decoders, simulate_naive_decoder, simulate_speculative_decoder
from core.matching_decoder import matching_decode
from core.schedule import default_three_t_injection
from core.syndrome_graph import build_syndrome_graph
import numpy as np


def test_speculative_decoder_outputs_paper_metrics(capsys):
    result = simulate_speculative_decoder(seed=10, processor_count=4)
    print(f"speculative: time={result['total_decoding_time_us']:.1f}")
    assert result["total_decoding_time_us"] > 0.0
    assert result["average_window_backlog"] >= 0.0


def test_naive_decoder_outputs_paper_metrics(capsys):
    result = simulate_naive_decoder(seed=11, processor_count=4)
    print(f"naive: wait={result['average_conditional_wait_time_us']:.2f}")
    assert result["average_conditional_wait_time_us"] >= 0.0


def test_compare_decoders_wait_reduction(capsys):
    comparison = compare_decoders(seed=42, speculation_accuracy=0.9)
    spec_wait = comparison["speculative"]["average_conditional_wait_time_us"]
    naive_wait = comparison["naive"]["average_conditional_wait_time_us"]
    print(
        f"decoder_compare: spec_wait={spec_wait:.2f} naive_wait={naive_wait:.2f} "
        f"wait_reduction={comparison['wait_reduction']:.2%}"
    )
    assert spec_wait <= naive_wait
    assert comparison["wait_reduction"] >= 0.0


def test_compare_decoders_with_schedule(capsys):
    schedule = default_three_t_injection()
    comparison = compare_decoders(schedule=schedule, seed=40)
    print(f"schedule_id: {schedule.id}")
    assert "speculative" in comparison
    assert "naive" in comparison


def test_decoder_api_exposes_matching_metrics(capsys):
    result = simulate_speculative_decoder(seed=42)
    print(
        f"rate={result.get('speculation_accuracy_rate')} "
        f"count={result.get('speculation_count')}"
    )
    assert "speculation_accuracy_rate" in result
    assert 0.0 <= result["speculation_accuracy_rate"] <= 1.0


def test_matching_decoder_on_graph(capsys):
    graph = build_syndrome_graph(np.array([0, 1, 1, 0], dtype=np.int8), left_boundary_logical=0)
    out = matching_decode(graph)
    print(f"pair_match satisfied={out.satisfied} cost={out.matching_cost}")
    assert out.satisfied is True
"""Direct tests for syndrome graph + matching decoder (shipped functions)."""

import numpy as np

from core.matching_decoder import (
    confirm_speculation_with_matching,
    matching_decode,
    verify_window_speculation,
)
from core.syndrome_graph import build_syndrome_graph, generate_window_syndrome


def test_matching_decode_satisfies_clean_path(capsys):
    syndrome = np.zeros(8, dtype=np.int8)
    graph = build_syndrome_graph(syndrome, left_boundary_logical=0)
    outcome = matching_decode(graph)
    print(f"satisfied={outcome.satisfied} logical={outcome.logical_correction}")
    assert outcome.satisfied is True
    assert outcome.logical_correction == 0


def test_boundary_mismatch_rejects_speculation(capsys):
    syndrome = np.array([1, 0, 1, 0, 0, 0, 0, 0], dtype=np.int8)
    ok = confirm_speculation_with_matching(
        syndrome,
        assumed_pred_logical=0,
        true_pred_logical=1,
    )
    print(f"boundary_mismatch_ok={ok}")
    assert ok is False


def test_boundary_match_accepts_speculation(capsys):
    syndrome = np.zeros(6, dtype=np.int8)
    ok = confirm_speculation_with_matching(
        syndrome,
        assumed_pred_logical=0,
        true_pred_logical=0,
    )
    print(f"boundary_match_ok={ok}")
    assert ok is True


def test_verify_window_speculation_reproducible(capsys):
    a = verify_window_speculation(window_id=3, pred_id=2, pred_verified=False, seed=42)
    b = verify_window_speculation(window_id=3, pred_id=2, pred_verified=False, seed=42)
    synd = generate_window_syndrome(window_id=3, pred_id=2, seed=42)
    print(f"verify={a} synd_sum={synd.sum()}")
    assert a == b


def test_verified_predecessor_uses_zero_logical(capsys):
    ok = verify_window_speculation(window_id=1, pred_id=0, pred_verified=True, seed=7)
    print(f"verified_pred_ok={ok}")
    assert ok is True
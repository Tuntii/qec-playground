"""Direct tests for syndrome graph + matching decoder (shipped functions)."""

import numpy as np

from core.matching_decoder import (
    _path_z_chain,
    confirm_speculation_with_matching,
    matching_decode,
    verify_window_speculation,
)
from core.syndrome_graph import (
    build_syndrome_graph,
    generate_window_syndrome_with_truth,
    stabilizer_syndrome,
)


def test_matching_decode_requires_hidden_z_agreement(capsys):
    syndrome = np.array([1, 0, 1, 0], dtype=np.int8)
    hidden = np.array([0, 1, 1, 0, 1], dtype=np.int8)
    graph = build_syndrome_graph(syndrome, left_boundary_logical=0, hidden_z=hidden)
    outcome = matching_decode(graph)
    z_assumed = _path_z_chain(syndrome, 0)
    print(f"satisfied={outcome.satisfied} z_eq={np.array_equal(z_assumed, hidden)}")
    assert outcome.satisfied == bool(np.array_equal(z_assumed, hidden))


def test_same_boundary_noise_passes_when_boundary_matches(capsys):
    """Boundary speculation passes when assumed logical matches hidden_z[0]."""
    synd, hidden = generate_window_syndrome_with_truth(
        window_id=11,
        pred_id=4,
        seed=2024,
        true_pred_logical=0,
        measurement_noise_rate=0.35,
        data_error_rate=0.25,
    )
    z_assumed = _path_z_chain(synd, 0)
    ok = confirm_speculation_with_matching(synd, assumed_pred_logical=0, hidden_z=hidden)
    print(
        f"hidden0={hidden[0]} synd_sum={synd.sum()} "
        f"z_match={np.array_equal(z_assumed, hidden)} ok={ok}"
    )
    assert hidden[0] == 0
    assert ok is True


def test_latent_pred_logical_changes_hidden_z(capsys):
    synd0, hidden0 = generate_window_syndrome_with_truth(
        window_id=3, pred_id=2, seed=42, true_pred_logical=0
    )
    synd1, hidden1 = generate_window_syndrome_with_truth(
        window_id=3, pred_id=2, seed=42, true_pred_logical=1
    )
    print(f"h0={hidden0[0]} h1={hidden1[0]} synd_diff={not np.array_equal(synd0, synd1)}")
    assert hidden0[0] == 0
    assert hidden1[0] == 1


def test_confirm_fails_when_assumed_decode_differs_from_hidden(capsys):
    synd, hidden = generate_window_syndrome_with_truth(
        window_id=7, pred_id=1, seed=1, true_pred_logical=1
    )
    ok = confirm_speculation_with_matching(synd, assumed_pred_logical=0, hidden_z=hidden)
    z_assumed = _path_z_chain(synd, 0)
    print(f"ok={ok} match={np.array_equal(z_assumed, hidden)}")
    assert hidden[0] == 1
    assert ok is False


def test_confirm_passes_when_assumed_matches_hidden(capsys):
    synd = np.zeros(6, dtype=np.int8)
    hidden = np.zeros(7, dtype=np.int8)
    ok = confirm_speculation_with_matching(synd, assumed_pred_logical=0, hidden_z=hidden)
    print(f"clean_ok={ok}")
    assert ok is True


def test_verify_window_speculation_reproducible(capsys):
    a = verify_window_speculation(window_id=3, pred_id=2, pred_verified=False, seed=42)
    b = verify_window_speculation(window_id=3, pred_id=2, pred_verified=False, seed=42)
    print(f"verify={a}")
    assert a == b


def test_stabilizer_syndrome_roundtrip(capsys):
    hidden = np.array([1, 0, 1, 1, 0, 0, 1], dtype=np.int8)
    synd = stabilizer_syndrome(hidden)
    graph = build_syndrome_graph(synd, left_boundary_logical=int(hidden[0]), hidden_z=hidden)
    out = matching_decode(graph)
    print(f"roundtrip={out.satisfied}")
    assert out.satisfied is True
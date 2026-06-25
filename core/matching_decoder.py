"""Minimum-weight matching decoder on 1D syndrome graphs (numpy only)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from core.syndrome_graph import SyndromeGraph, true_predecessor_logical


@dataclass(frozen=True)
class MatchingOutcome:
    satisfied: bool
    logical_correction: int
    matching_cost: int


def _path_z_chain(syndrome: np.ndarray, left_boundary: int) -> np.ndarray:
    """Unique minimum-weight Z string for a 1D path code with boundary z[0]."""
    z = np.zeros(syndrome.size + 1, dtype=np.int8)
    z[0] = int(left_boundary) % 2
    for i, bit in enumerate(syndrome):
        z[i + 1] = (int(bit) + z[i]) % 2
    return z


def _mwpm_cost_on_defects(defects: tuple[int, ...], n_checks: int) -> int:
    """MWPM cost pairing defect check nodes on a line (exact DP)."""
    if not defects:
        return 0
    d = len(defects)
    inf = 10**12

    @lru_cache(maxsize=None)
    def dp(idx: int, used_mask: int) -> int:
        if used_mask == (1 << d) - 1:
            return 0
        best = inf
        first = next(i for i in range(d) if not (used_mask >> i) & 1)
        for j in range(first + 1, d):
            if (used_mask >> j) & 1:
                continue
            pair_cost = defects[j] - defects[first]
            rest = dp(first + 1, used_mask | (1 << first) | (1 << j))
            if rest < inf:
                best = min(best, pair_cost + rest)
        left_cost = defects[first] + 1
        rest = dp(first + 1, used_mask | (1 << first))
        if rest < inf:
            best = min(best, left_cost + rest)
        right_cost = n_checks - defects[first]
        rest = dp(first + 1, used_mask | (1 << first))
        if rest < inf:
            best = min(best, right_cost + rest)
        return best

    return dp(0, 0)


def matching_decode(graph: SyndromeGraph) -> MatchingOutcome:
    """Decode measured syndromes with MWPM (path code + defect-pairing cost)."""
    synd = np.asarray(graph.syndrome, dtype=np.int8)
    left = int(graph.left_boundary_logical) % 2
    z = _path_z_chain(synd, left)
    implied = (z[:-1] + z[1:]) % 2
    satisfied = bool(np.array_equal(implied, synd))
    defects = tuple(int(i) for i in np.flatnonzero(synd))
    pair_cost = _mwpm_cost_on_defects(defects, synd.size)
    weight_cost = int(z.sum())
    matching_cost = pair_cost + weight_cost
    logical = int(z[-1])
    return MatchingOutcome(
        satisfied=satisfied,
        logical_correction=logical,
        matching_cost=matching_cost,
    )


def confirm_speculation_with_matching(
    syndrome: np.ndarray,
    *,
    assumed_pred_logical: int,
    true_pred_logical: int,
) -> bool:
    """Compare MWPM/path decode under assumed vs true predecessor boundary on same syndrome."""
    synd = np.asarray(syndrome, dtype=np.int8)
    assumed = matching_decode(
        SyndromeGraph(syndrome=synd, left_boundary_logical=int(assumed_pred_logical) % 2, n_data_qubits=synd.size + 1)
    )
    truth = matching_decode(
        SyndromeGraph(syndrome=synd, left_boundary_logical=int(true_pred_logical) % 2, n_data_qubits=synd.size + 1)
    )
    if not assumed.satisfied or not truth.satisfied:
        return False
    return assumed.logical_correction == truth.logical_correction


def verify_window_speculation(
    *,
    window_id: int,
    pred_id: int | None,
    pred_verified: bool,
    seed: int,
    syndrome: np.ndarray | None = None,
) -> bool:
    """Build syndrome for this window and confirm assumed (0) vs true predecessor logical."""
    from core.syndrome_graph import generate_window_syndrome

    synd = (
        generate_window_syndrome(window_id=window_id, pred_id=pred_id, seed=seed)
        if syndrome is None
        else np.asarray(syndrome, dtype=np.int8)
    )
    true_left = true_predecessor_logical(pred_id=pred_id, pred_verified=pred_verified, seed=seed)
    return confirm_speculation_with_matching(
        synd,
        assumed_pred_logical=0,
        true_pred_logical=true_left,
    )
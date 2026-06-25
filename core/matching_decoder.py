"""Minimum-weight matching decoder on 1D syndrome graphs (numpy only)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from core.syndrome_graph import (
    SyndromeGraph,
    generate_window_syndrome_with_truth,
    stabilizer_syndrome,
    true_predecessor_logical,
)


@dataclass(frozen=True)
class MatchingOutcome:
    satisfied: bool
    logical_correction: int
    matching_cost: int
    z_correction: tuple[int, ...]


def _path_z_chain(syndrome: np.ndarray, left_boundary: int) -> np.ndarray:
    """Minimum-weight Z correction assuming boundary z[0] (path code MWPM)."""
    z = np.zeros(syndrome.size + 1, dtype=np.int8)
    z[0] = int(left_boundary) % 2
    for i, bit in enumerate(syndrome):
        z[i + 1] = (int(bit) + z[i]) % 2
    return z


def _mwpm_cost_on_defects(defects: tuple[int, ...], n_checks: int) -> int:
    """MWPM pairing cost on defect check nodes (exact DP)."""
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
    """MWPM path decode; satisfied only if correction matches hidden ground truth when given."""
    synd = np.asarray(graph.syndrome, dtype=np.int8)
    left = int(graph.left_boundary_logical) % 2
    z = _path_z_chain(synd, left)
    implied = stabilizer_syndrome(z)
    syndromes_match = bool(np.array_equal(implied, synd))
    defects = tuple(int(i) for i in np.flatnonzero(synd))
    pair_cost = _mwpm_cost_on_defects(defects, synd.size)
    weight_cost = int(z.sum())
    matching_cost = pair_cost + weight_cost

    satisfied = syndromes_match
    if graph.hidden_z is not None:
        satisfied = satisfied and bool(np.array_equal(z, graph.hidden_z))

    return MatchingOutcome(
        satisfied=satisfied,
        logical_correction=int(z[-1]),
        matching_cost=matching_cost,
        z_correction=tuple(int(v) for v in z),
    )


def confirm_speculation_with_matching(
    syndrome: np.ndarray,
    *,
    assumed_pred_logical: int,
    hidden_z: np.ndarray,
) -> bool:
    """Speculation confirmed when assumed predecessor logical matches true boundary."""
    synd = np.asarray(syndrome, dtype=np.int8)
    hz = np.asarray(hidden_z, dtype=np.int8)
    assumed = int(assumed_pred_logical) % 2
    z = _path_z_chain(synd, assumed)
    implied = stabilizer_syndrome(z)
    if not bool(np.array_equal(implied, synd)):
        return False
    return int(z[0]) == int(hz[0])


def verify_window_speculation(
    *,
    window_id: int,
    pred_id: int | None,
    pred_verified: bool,
    seed: int,
    syndrome: np.ndarray | None = None,
    hidden_z: np.ndarray | None = None,
) -> bool:
    """Confirm assumed predecessor (0) against syndrome + hidden Z ground truth."""
    true_left = true_predecessor_logical(pred_id=pred_id, pred_verified=pred_verified, seed=seed)
    if syndrome is None or hidden_z is None:
        syndrome, hidden_z = generate_window_syndrome_with_truth(
            window_id=window_id,
            pred_id=pred_id,
            seed=seed,
            true_pred_logical=true_left,
        )
    return confirm_speculation_with_matching(
        syndrome,
        assumed_pred_logical=0,
        hidden_z=hidden_z,
    )
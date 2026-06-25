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


def _min_cost_path_matching(
    defects: tuple[int, ...],
    n_checks: int,
    *,
    use_left_boundary: bool,
) -> tuple[int, int]:
    """Exact MWPM on a path with optional left-boundary absorption."""
    if not defects:
        return 0, 0

    d = len(defects)
    inf = 10**12

    @lru_cache(maxsize=None)
    def dp(idx: int, used_mask: int, left_used: bool) -> int:
        if used_mask == (1 << d) - 1:
            return 0
        best = inf
        first = next(i for i in range(d) if not (used_mask >> i) & 1)
        for j in range(first + 1, d):
            if (used_mask >> j) & 1:
                continue
            pair_cost = defects[j] - defects[first]
            rest = dp(first + 1, used_mask | (1 << first) | (1 << j), left_used)
            if rest < inf:
                best = min(best, pair_cost + rest)
        if not left_used:
            left_cost = defects[first] + 1
            rest = dp(first + 1, used_mask | (1 << first), True)
            if rest < inf:
                best = min(best, left_cost + rest)
        right_cost = n_checks - defects[first]
        rest = dp(first + 1, used_mask | (1 << first), left_used)
        if rest < inf:
            best = min(best, right_cost + rest)
        return best

    base_cost = dp(0, 0, False)
    if base_cost >= inf:
        return inf, 0

    residual = (d + int(use_left_boundary)) % 2
    return base_cost, residual


def _effective_syndrome(syndrome: np.ndarray, left_boundary_logical: int) -> np.ndarray:
    """Predecessor logical flips the first stabilizer on the path."""
    effective = np.asarray(syndrome, dtype=np.int8).copy()
    if int(left_boundary_logical) % 2:
        effective[0] ^= 1
    return effective


def matching_decode(graph: SyndromeGraph) -> MatchingOutcome:
    """Run MWPM; residual logical parity reflects boundary mismatch."""
    effective = _effective_syndrome(graph.syndrome, graph.left_boundary_logical)
    defects = tuple(int(i) for i in np.flatnonzero(effective))
    need_left = (len(defects) + graph.left_boundary_logical) % 2 == 1
    cost, residual = _min_cost_path_matching(defects, effective.size, use_left_boundary=need_left)
    if cost >= 10**12:
        return MatchingOutcome(satisfied=False, logical_correction=1, matching_cost=cost)
    logical = (graph.left_boundary_logical + residual) % 2
    return MatchingOutcome(satisfied=True, logical_correction=logical, matching_cost=cost)


def confirm_speculation_with_matching(
    syndrome: np.ndarray,
    *,
    assumed_pred_logical: int,
    true_pred_logical: int,
) -> bool:
    """Speculation confirmed when assumed predecessor logical matches true and MWPM agrees."""
    assumed_left = int(assumed_pred_logical) % 2
    true_left = int(true_pred_logical) % 2
    if assumed_left != true_left:
        return False
    assumed_graph = SyndromeGraph(
        syndrome=np.asarray(syndrome, dtype=np.int8),
        left_boundary_logical=assumed_left,
        n_data_qubits=int(syndrome.size) + 1,
    )
    true_graph = SyndromeGraph(
        syndrome=np.asarray(syndrome, dtype=np.int8),
        left_boundary_logical=true_left,
        n_data_qubits=int(syndrome.size) + 1,
    )
    assumed = matching_decode(assumed_graph)
    truth = matching_decode(true_graph)
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
    """End-to-end: build syndrome, compare assumed (0) vs true predecessor logical."""
    from core.syndrome_graph import build_syndrome_graph, generate_window_syndrome

    synd = (
        generate_window_syndrome(window_id=window_id, pred_id=pred_id, seed=seed)
        if syndrome is None
        else np.asarray(syndrome, dtype=np.int8)
    )
    true_left = true_predecessor_logical(pred_id=pred_id, pred_verified=pred_verified, seed=seed)
    assumed_left = 0
    return confirm_speculation_with_matching(
        synd,
        assumed_pred_logical=assumed_left,
        true_pred_logical=true_left,
    )
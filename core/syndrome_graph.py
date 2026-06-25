"""Syndrome graph construction for window decode rounds (path stabilizer layout)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SyndromeGraph:
    """Check nodes on a 1D path; defects are activated stabilizer measurements."""

    syndrome: np.ndarray
    left_boundary_logical: int
    n_data_qubits: int

    def defect_positions(self) -> tuple[int, ...]:
        return tuple(int(i) for i in np.flatnonzero(self.syndrome))


def build_syndrome_graph(
    syndrome: np.ndarray,
    *,
    left_boundary_logical: int,
) -> SyndromeGraph:
    """Wrap measured syndromes and predecessor logical boundary for matching."""
    arr = np.asarray(syndrome, dtype=np.int8).copy()
    if arr.ndim != 1:
        raise ValueError("syndrome must be a 1D array")
    if arr.size < 2:
        raise ValueError("syndrome must have at least 2 checks")
    left = int(left_boundary_logical) % 2
    return SyndromeGraph(syndrome=arr, left_boundary_logical=left, n_data_qubits=int(arr.size) + 1)


def generate_window_syndrome(
    *,
    window_id: int,
    pred_id: int | None,
    seed: int,
    n_checks: int = 8,
    defect_rate: float = 0.22,
) -> np.ndarray:
    """Sample a reproducible defect pattern for one decode round."""
    pred_key = -1 if pred_id is None else int(pred_id)
    rng = np.random.default_rng(seed + window_id * 104_729 + pred_key * 42_169)
    return (rng.random(n_checks) < defect_rate).astype(np.int8)


def true_predecessor_logical(*, pred_id: int | None, pred_verified: bool, seed: int) -> int:
    """Latent logical from predecessor when not yet verified (deterministic from seed)."""
    if pred_id is None or pred_verified:
        return 0
    return int(np.random.default_rng(seed + int(pred_id) * 7_919).integers(0, 2))
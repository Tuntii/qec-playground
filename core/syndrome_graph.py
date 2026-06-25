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
    hidden_z: np.ndarray | None = None

    def defect_positions(self) -> tuple[int, ...]:
        return tuple(int(i) for i in np.flatnonzero(self.syndrome))


def stabilizer_syndrome(z: np.ndarray) -> np.ndarray:
    """Z stabilizers on a path: s[i] = z[i] + z[i+1] (mod 2)."""
    z = np.asarray(z, dtype=np.int8)
    return (z[:-1] + z[1:]) % 2


def build_syndrome_graph(
    syndrome: np.ndarray,
    *,
    left_boundary_logical: int,
    hidden_z: np.ndarray | None = None,
) -> SyndromeGraph:
    """Wrap measured syndromes and predecessor logical boundary for matching."""
    arr = np.asarray(syndrome, dtype=np.int8).copy()
    if arr.ndim != 1:
        raise ValueError("syndrome must be a 1D array")
    if arr.size < 2:
        raise ValueError("syndrome must have at least 2 checks")
    left = int(left_boundary_logical) % 2
    hz = None if hidden_z is None else np.asarray(hidden_z, dtype=np.int8).copy()
    return SyndromeGraph(
        syndrome=arr,
        left_boundary_logical=left,
        n_data_qubits=int(arr.size) + 1,
        hidden_z=hz,
    )


def true_predecessor_logical(*, pred_id: int | None, pred_verified: bool, seed: int) -> int:
    """Latent logical from predecessor when not yet verified (deterministic from seed)."""
    if pred_id is None or pred_verified:
        return 0
    return int(np.random.default_rng(seed + int(pred_id) * 7_919).integers(0, 2))


def generate_window_syndrome_with_truth(
    *,
    window_id: int,
    pred_id: int | None,
    seed: int,
    true_pred_logical: int,
    n_checks: int = 8,
    data_error_rate: float = 0.10,
    measurement_noise_rate: float = 0.06,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample physical Z errors + measurement noise; syndrome depends on true_pred_logical."""
    pred_key = -1 if pred_id is None else int(pred_id)
    rng = np.random.default_rng(seed + window_id * 104_729 + pred_key * 42_169)

    z = np.zeros(n_checks + 1, dtype=np.int8)
    z[0] = int(true_pred_logical) % 2
    for i in range(1, n_checks + 1):
        if rng.random() < data_error_rate:
            z[i] ^= 1

    clean = stabilizer_syndrome(z)
    noise = (rng.random(n_checks) < measurement_noise_rate).astype(np.int8)
    measured = (clean + noise) % 2
    return measured, z


def generate_window_syndrome(
    *,
    window_id: int,
    pred_id: int | None,
    seed: int,
    n_checks: int = 8,
    true_pred_logical: int = 0,
) -> np.ndarray:
    """Backward-compatible: return measured syndrome only."""
    measured, _ = generate_window_syndrome_with_truth(
        window_id=window_id,
        pred_id=pred_id,
        seed=seed,
        true_pred_logical=true_pred_logical,
        n_checks=n_checks,
    )
    return measured
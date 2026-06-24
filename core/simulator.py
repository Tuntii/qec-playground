"""GKP state preparation and logical error simulation using QuTiP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import qutip as qt

from core.metrics import (
    envelope_variance,
    gkp_cell_half_width,
    logical_error_probability,
    squeezing_db_to_r,
    surface_logical_rate,
)


@dataclass(frozen=True)
class GKPConfig:
    squeezing_db: float = 10.0
    noise_p: float = 0.01
    shots: int = 1000
    hilbert_dim: int = 32
    surface_distance: int = 3
    seed: int = 42


def create_finite_gkp_state(squeezing_db: float, dim: int = 32) -> qt.Qobj:
    """
    Build a finite-energy GKP-like state as a truncated sum of displaced peaks.

    Uses QuTiP squeezed vacuum envelopes summed over a small GKP lattice patch.
    """
    r = squeezing_db_to_r(squeezing_db)
    sqrt_2pi = np.sqrt(2 * np.pi)
    displacements = [n * sqrt_2pi for n in range(-1, 2)]

    peaks: list[qt.Qobj] = []
    for x0 in displacements:
        squeezed = qt.squeeze(dim, r) * qt.basis(dim, 0)
        displaced = qt.displace(dim, x0, 0) * squeezed
        peaks.append(displaced.unit())

    state = sum(peaks).unit()
    return state


def _state_fidelity(a: qt.Qobj, b: qt.Qobj) -> float:
    """Fidelity between two states, tolerating small Hilbert-space truncation drift."""
    d = min(a.shape[0], b.shape[0])
    a_vec = a.full()[:d, 0]
    b_vec = b.full()[:d, 0]
    return float(abs(np.vdot(a_vec, b_vec)) ** 2)


def apply_noise_channel(
    state: qt.Qobj,
    noise_p: float,
    rng: np.random.Generator,
) -> tuple[qt.Qobj, float]:
    """
    Apply displacement + depolarization noise; return updated state and displacement.
    """
    dim = state.dims[0][0]
    sigma = np.sqrt(noise_p) * 0.5
    displacement = rng.normal(0.0, sigma)
    noisy = (qt.displace(dim, displacement, 0) * state).unit()
    return noisy, displacement


def simulate_gkp_logical_errors(
    squeezing_db: float = 10.0,
    noise_p: float = 0.01,
    shots: int = 1000,
    hilbert_dim: int = 32,
    surface_distance: int = 3,
    seed: int = 42,
) -> dict[str, float]:
    """
    Monte Carlo estimate of logical error rate for finite-squeezing GKP + surface.

    Returns rates in [0, 1] and diagnostic metrics derived from the GKP envelope.
    """
    if not 0.0 <= noise_p <= 1.0:
        raise ValueError("noise_p must be in [0, 1]")
    if shots < 1:
        raise ValueError("shots must be >= 1")

    rng = np.random.default_rng(seed)
    ideal = create_finite_gkp_state(squeezing_db, dim=hilbert_dim)
    cell_hw = gkp_cell_half_width()
    var = envelope_variance(squeezing_db)
    displacement_std = np.sqrt(var + noise_p * 0.25)

    logical_errors = 0
    fidelities: list[float] = []

    for _ in range(shots):
        noisy, disp = apply_noise_channel(ideal, noise_p, rng)
        fid = _state_fidelity(ideal, noisy)
        fidelities.append(fid)

        envelope_error = abs(disp) > cell_hw
        model_error = rng.random() < logical_error_probability(
            displacement_std, cell_hw, noise_p
        )
        if envelope_error or model_error:
            logical_errors += 1

    physical_rate = logical_errors / shots
    logical_rate = surface_logical_rate(physical_rate, surface_distance)

    return {
        "logical_error_rate": logical_rate,
        "physical_error_rate": physical_rate,
        "mean_fidelity": float(np.mean(fidelities)),
        "envelope_variance": var,
        "displacement_std": displacement_std,
        "squeezing_db": float(squeezing_db),
        "noise_p": float(noise_p),
        "shots": float(shots),
    }


def run_simulation(
    squeezing_db: float = 10.0,
    noise_p: float = 0.01,
    skip_threshold: float = 0.7,
    shots: int = 1000,
    window_size: int = 4,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Run combined GKP + speculative decoder simulation.

    Primary entry point for CLI and tests.
    """
    from core.decoder import compare_decoders

    gkp = simulate_gkp_logical_errors(
        squeezing_db=squeezing_db,
        noise_p=noise_p,
        shots=shots,
        seed=seed,
    )
    decoder = compare_decoders(
        noise_p=noise_p,
        skip_threshold=skip_threshold,
        shots=shots,
        window_size=window_size,
        base_logical_rate=gkp["logical_error_rate"],
        seed=seed + 1,
    )
    return {
        "gkp": gkp,
        "decoder": decoder,
        "params": {
            "squeezing_db": squeezing_db,
            "noise_p": noise_p,
            "skip_threshold": skip_threshold,
            "shots": shots,
            "window_size": window_size,
            "seed": seed,
        },
    }
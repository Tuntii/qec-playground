"""GKP state preparation and logical error simulation using QuTiP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import qutip as qt

from core.metrics import (
    envelope_variance,
    fidelity_error_threshold,
    gkp_cell_half_width,
    gkp_lattice_spacing,
    squeezing_db_to_r,
    surface_logical_rate,
)


@dataclass(frozen=True)
class GKPSyndromeShot:
    """Per-shot syndrome data derived from QuTiP state evolution."""

    fidelity: float
    displacement: float
    confidence: float
    physical_error: bool


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

    Peaks are placed at n * sqrt(2*pi), matching the GKP position lattice.
    """
    r = squeezing_db_to_r(squeezing_db)
    spacing = gkp_lattice_spacing()
    displacements = [n * spacing for n in range(-1, 2)]

    peaks: list[qt.Qobj] = []
    for x0 in displacements:
        squeezed = qt.squeeze(dim, r) * qt.basis(dim, 0)
        displaced = qt.displace(dim, x0, 0) * squeezed
        peaks.append(displaced.unit())

    return sum(peaks).unit()


def _state_fidelity(a: qt.Qobj, b: qt.Qobj) -> float:
    """Fidelity between two states, tolerating small Hilbert-space truncation drift."""
    d = min(a.shape[0], b.shape[0])
    a_vec = a.full()[:d, 0]
    b_vec = b.full()[:d, 0]
    return float(abs(np.vdot(a_vec, b_vec)) ** 2)


def apply_noise_channel(
    state: qt.Qobj,
    noise_p: float,
    squeezing_db: float,
    rng: np.random.Generator,
) -> tuple[qt.Qobj, float]:
    """Apply QuTiP displacement noise; return noisy state and displacement."""
    dim = state.dims[0][0]
    # Displacement variance shrinks with tighter squeezing (smaller envelope).
    sigma = np.sqrt(noise_p * envelope_variance(squeezing_db))
    displacement = rng.normal(0.0, sigma)
    noisy = (qt.displace(dim, displacement, 0) * state).unit()
    return noisy, displacement


def _classify_shot(
    ideal: qt.Qobj,
    noisy: qt.Qobj,
    displacement: float,
    noise_p: float,
    squeezing_db: float,
) -> GKPSyndromeShot:
    """Derive syndrome observables and error flag purely from QuTiP state data."""
    fidelity = _state_fidelity(ideal, noisy)
    threshold = fidelity_error_threshold(noise_p, squeezing_db)
    env = envelope_variance(squeezing_db)
    slip_bound = gkp_cell_half_width() * np.sqrt(env)
    lattice_slip = abs(displacement) > slip_bound
    fidelity_loss = fidelity < threshold
    physical_error = lattice_slip or fidelity_loss

    return GKPSyndromeShot(
        fidelity=fidelity,
        displacement=displacement,
        confidence=fidelity,
        physical_error=physical_error,
    )


def simulate_gkp_logical_errors(
    squeezing_db: float = 10.0,
    noise_p: float = 0.01,
    shots: int = 1000,
    hilbert_dim: int = 32,
    surface_distance: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Monte Carlo estimate of logical error rate for finite-squeezing GKP + surface.

    Physical errors are counted from QuTiP fidelity and displacement per shot.
    """
    if not 0.0 <= noise_p <= 1.0:
        raise ValueError("noise_p must be in [0, 1]")
    if shots < 1:
        raise ValueError("shots must be >= 1")

    rng = np.random.default_rng(seed)
    ideal = create_finite_gkp_state(squeezing_db, dim=hilbert_dim)
    var = envelope_variance(squeezing_db)

    syndromes: list[GKPSyndromeShot] = []
    for _ in range(shots):
        noisy, disp = apply_noise_channel(ideal, noise_p, squeezing_db, rng)
        syndromes.append(
            _classify_shot(ideal, noisy, disp, noise_p, squeezing_db)
        )

    physical_errors = sum(1 for s in syndromes if s.physical_error)
    physical_rate = physical_errors / shots
    logical_rate = surface_logical_rate(physical_rate, surface_distance)
    fidelities = [s.fidelity for s in syndromes]

    return {
        "logical_error_rate": logical_rate,
        "physical_error_rate": physical_rate,
        "mean_fidelity": float(np.mean(fidelities)),
        "envelope_variance": var,
        "lattice_spacing": gkp_lattice_spacing(),
        "cell_half_width": gkp_cell_half_width(),
        "squeezing_db": float(squeezing_db),
        "noise_p": float(noise_p),
        "shots": float(shots),
        "syndromes": syndromes,
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

    Decoder windows consume the per-shot GKP syndromes from the same QuTiP run.
    """
    from core.decoder import compare_decoders

    gkp = simulate_gkp_logical_errors(
        squeezing_db=squeezing_db,
        noise_p=noise_p,
        shots=shots,
        seed=seed,
    )
    decoder = compare_decoders(
        syndromes=gkp["syndromes"],
        noise_p=noise_p,
        skip_threshold=skip_threshold,
        window_size=window_size,
        physical_error_rate=gkp["physical_error_rate"],
        seed=seed,
    )
    return {
        "gkp": {k: v for k, v in gkp.items() if k != "syndromes"},
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
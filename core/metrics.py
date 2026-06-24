"""Metric helpers for GKP and decoder simulations."""

from __future__ import annotations

import math


def squeezing_db_to_r(squeezing_db: float) -> float:
    """Convert squeezing in decibels to the squeezing parameter r."""
    return squeezing_db * math.log(10) / 20


def envelope_variance(squeezing_db: float) -> float:
    """Position-quadrature variance of the finite-squeezing GKP envelope."""
    r = squeezing_db_to_r(squeezing_db)
    return math.exp(-2 * r)


def gkp_cell_half_width() -> float:
    """Half-width of a GKP lattice cell in position quadrature (natural units)."""
    return math.sqrt(math.pi) / 2


def logical_error_probability(
    displacement_std: float,
    cell_half_width: float,
    noise_p: float,
) -> float:
    """
    Approximate per-qubit logical error probability from displacement noise.

    Combines envelope leakage outside the GKP cell with an independent
    depolarizing-like channel probability ``noise_p``.
    """
    if displacement_std <= 0:
        envelope_leak = 0.0
    else:
        # Tail mass outside ±cell_half_width under Gaussian displacement.
        z = cell_half_width / displacement_std
        envelope_leak = math.erfc(z / math.sqrt(2))

    return min(1.0, max(0.0, 1.0 - (1.0 - envelope_leak) * (1.0 - noise_p)))


def surface_logical_rate(physical_rate: float, distance: int = 3) -> float:
    """Distance-d scaling for a surface-code logical error (simplified)."""
    return min(1.0, physical_rate ** ((distance + 1) // 2))
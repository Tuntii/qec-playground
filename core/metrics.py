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


def gkp_lattice_spacing() -> float:
    """Period of the GKP position lattice (natural units)."""
    return math.sqrt(2 * math.pi)


def gkp_cell_half_width() -> float:
    """Half-width of one GKP cell; peaks sit at n * lattice_spacing."""
    return gkp_lattice_spacing() / 2


def fidelity_error_threshold(noise_p: float, squeezing_db: float) -> float:
    """
    Minimum codeword fidelity before counting a QuTiP physical error.

    Fixed bar so error counting reflects QuTiP fidelity degradation from
    the channel; noise_p drives displacement magnitude separately.
    """
    # Wider peaks (low squeeze) fail fidelity sooner; threshold leniency tracks envelope.
    return max(0.5, 0.93 + 0.08 * envelope_variance(squeezing_db))


def surface_logical_rate(physical_rate: float, distance: int = 3) -> float:
    """Distance-d scaling for a surface-code logical error (simplified)."""
    return min(1.0, physical_rate ** ((distance + 1) // 2))
"""Speculative window decoder simulation with naive baseline comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from core.simulator import GKPSyndromeShot


@dataclass(frozen=True)
class WindowOutcome:
    success: bool
    waited_cycles: int
    speculated: bool
    speculation_correct: bool


def _dependency_ready(
    dep_roll: float,
    noise_p: float,
    waited: int,
    window_size: int,
) -> bool:
    """Whether upstream window dependencies have converged."""
    progress = waited / max(window_size, 1)
    success_prob = min(0.99, progress * (1.0 - 0.5 * noise_p))
    return dep_roll < success_prob


def simulate_window(
    syndrome: GKPSyndromeShot,
    noise_p: float,
    skip_threshold: float,
    window_size: int,
    speculative: bool,
    physical_error_rate: float,
    dep_roll: float,
    success_roll: float,
) -> WindowOutcome:
    """
    Simulate one decoding window using GKP-derived syndrome confidence.

    Shared ``dep_roll`` and ``success_roll`` ensure identical stochastic
    conditions when comparing speculative vs naive on the same shot.
    """
    confidence = syndrome.confidence
    speculated = False
    waited = 0

    if speculative and confidence >= skip_threshold:
        speculated = True
        waited = 1
        deps_ok = _dependency_ready(dep_roll, noise_p, waited=1, window_size=window_size)
        speculation_correct = deps_ok
    else:
        deps_ok = False
        for cycle in range(1, window_size + 1):
            waited = cycle
            if _dependency_ready(dep_roll, noise_p, waited=cycle, window_size=window_size):
                deps_ok = True
                break
        speculation_correct = not speculated

    shot_error_prior = physical_error_rate
    if syndrome.physical_error:
        shot_error_prior = min(1.0, shot_error_prior + (1.0 - syndrome.fidelity))

    if speculated and not speculation_correct:
        error_prob = min(1.0, shot_error_prior + noise_p * 0.5)
    elif not deps_ok:
        error_prob = min(1.0, shot_error_prior + noise_p * 0.3)
    else:
        error_prob = shot_error_prior * (1.0 - 0.3 * confidence)

    success = success_roll > error_prob
    return WindowOutcome(
        success=success,
        waited_cycles=waited,
        speculated=speculated,
        speculation_correct=speculation_correct if speculated else True,
    )


def _run_decoder_mode(
    syndromes: list[GKPSyndromeShot],
    rng: np.random.Generator,
    noise_p: float,
    skip_threshold: float,
    window_size: int,
    speculative: bool,
    physical_error_rate: float,
) -> dict[str, float]:
    outcomes: list[WindowOutcome] = []
    for syndrome in syndromes:
        dep_roll = float(rng.random())
        success_roll = float(rng.random())
        outcomes.append(
            simulate_window(
                syndrome=syndrome,
                noise_p=noise_p,
                skip_threshold=skip_threshold,
                window_size=window_size,
                speculative=speculative,
                physical_error_rate=physical_error_rate,
                dep_roll=dep_roll,
                success_roll=success_roll,
            )
        )

    shots = len(outcomes)
    successes = sum(1 for o in outcomes if o.success)
    speculated = sum(1 for o in outcomes if o.speculated)
    correct_spec = sum(1 for o in outcomes if o.speculated and o.speculation_correct)
    waits = [o.waited_cycles for o in outcomes]

    return {
        "success_probability": successes / shots,
        "mean_wait_cycles": float(np.mean(waits)),
        "speculation_rate": speculated / shots,
        "speculation_accuracy": correct_spec / speculated if speculated else 1.0,
        "skip_threshold": float(skip_threshold),
        "noise_p": float(noise_p),
        "shots": float(shots),
    }


def simulate_speculative_decoder(
    syndromes: list[GKPSyndromeShot],
    noise_p: float = 0.01,
    skip_threshold: float = 0.7,
    window_size: int = 4,
    physical_error_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Run speculative window decoder over GKP-derived syndromes."""
    if not 0.0 <= skip_threshold <= 1.0:
        raise ValueError("skip_threshold must be in [0, 1]")

    rng = np.random.default_rng(seed)
    return _run_decoder_mode(
        syndromes=syndromes,
        rng=rng,
        noise_p=noise_p,
        skip_threshold=skip_threshold,
        window_size=window_size,
        speculative=True,
        physical_error_rate=physical_error_rate,
    )


def simulate_naive_decoder(
    syndromes: list[GKPSyndromeShot],
    noise_p: float = 0.01,
    window_size: int = 4,
    physical_error_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Naive baseline: never skip dependency waits."""
    rng = np.random.default_rng(seed)
    return _run_decoder_mode(
        syndromes=syndromes,
        rng=rng,
        noise_p=noise_p,
        skip_threshold=1.0,
        window_size=window_size,
        speculative=False,
        physical_error_rate=physical_error_rate,
    )


def compare_decoders(
    syndromes: list[GKPSyndromeShot],
    noise_p: float = 0.01,
    skip_threshold: float = 0.7,
    window_size: int = 4,
    physical_error_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Compare speculative and naive decoders on identical GKP syndromes.

    Each shot reuses the same dep_roll and success_roll for both modes by
    drawing randomness once per shot before applying both decoders.
    """
    if not 0.0 <= skip_threshold <= 1.0:
        raise ValueError("skip_threshold must be in [0, 1]")

    rng = np.random.default_rng(seed)
    spec_outcomes: list[WindowOutcome] = []
    naive_outcomes: list[WindowOutcome] = []

    for syndrome in syndromes:
        dep_roll = float(rng.random())
        success_roll = float(rng.random())
        spec_outcomes.append(
            simulate_window(
                syndrome=syndrome,
                noise_p=noise_p,
                skip_threshold=skip_threshold,
                window_size=window_size,
                speculative=True,
                physical_error_rate=physical_error_rate,
                dep_roll=dep_roll,
                success_roll=success_roll,
            )
        )
        naive_outcomes.append(
            simulate_window(
                syndrome=syndrome,
                noise_p=noise_p,
                skip_threshold=1.0,
                window_size=window_size,
                speculative=False,
                physical_error_rate=physical_error_rate,
                dep_roll=dep_roll,
                success_roll=success_roll,
            )
        )

    def _summarize(outcomes: list[WindowOutcome], threshold: float) -> dict[str, float]:
        shots = len(outcomes)
        successes = sum(1 for o in outcomes if o.success)
        speculated = sum(1 for o in outcomes if o.speculated)
        correct_spec = sum(1 for o in outcomes if o.speculated and o.speculation_correct)
        waits = [o.waited_cycles for o in outcomes]
        return {
            "success_probability": successes / shots,
            "mean_wait_cycles": float(np.mean(waits)),
            "speculation_rate": speculated / shots,
            "speculation_accuracy": correct_spec / speculated if speculated else 1.0,
            "skip_threshold": threshold,
            "noise_p": float(noise_p),
            "shots": float(shots),
        }

    speculative = _summarize(spec_outcomes, skip_threshold)
    naive = _summarize(naive_outcomes, 1.0)

    wait_reduction = 1.0 - (
        speculative["mean_wait_cycles"] / max(naive["mean_wait_cycles"], 1e-9)
    )

    return {
        "speculative": speculative,
        "naive": naive,
        "wait_reduction": float(wait_reduction),
        "success_delta": (
            speculative["success_probability"] - naive["success_probability"]
        ),
    }
"""Speculative window decoder simulation with naive baseline comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class WindowOutcome:
    success: bool
    waited_cycles: int
    speculated: bool
    speculation_correct: bool


def _syndrome_confidence(rng: np.random.Generator, noise_p: float) -> float:
    """Draw a syndrome measurement confidence inversely related to noise."""
    base = 1.0 - noise_p
    jitter = rng.normal(0.0, 0.08)
    return float(np.clip(base + jitter, 0.0, 1.0))


def _dependency_ready(
    rng: np.random.Generator,
    noise_p: float,
    waited: int,
    window_size: int,
) -> bool:
    """Whether upstream window dependencies have converged."""
    # More waiting cycles improve dependency resolution; noise slows convergence.
    progress = waited / max(window_size, 1)
    success_prob = min(0.99, progress * (1.0 - 0.5 * noise_p))
    return bool(rng.random() < success_prob)


def simulate_window(
    rng: np.random.Generator,
    noise_p: float,
    skip_threshold: float,
    window_size: int,
    speculative: bool,
    base_logical_rate: float,
) -> WindowOutcome:
    """
    Simulate one decoding window with optional speculative skip.

    Speculative mode skips waiting when syndrome confidence exceeds
    ``skip_threshold``; naive mode always waits for full dependency resolution.
    """
    confidence = _syndrome_confidence(rng, noise_p)
    speculated = False
    waited = 0

    if speculative and confidence >= skip_threshold:
        speculated = True
        waited = 1
        deps_ok = _dependency_ready(rng, noise_p, waited=1, window_size=window_size)
        speculation_correct = deps_ok
    else:
        for cycle in range(1, window_size + 1):
            waited = cycle
            if _dependency_ready(rng, noise_p, waited=cycle, window_size=window_size):
                deps_ok = True
                break
        else:
            deps_ok = False
        speculation_correct = not speculated

    # Logical error likelihood rises when speculation is wrong or deps fail.
    if speculated and not speculation_correct:
        error_prob = min(1.0, base_logical_rate + noise_p * 0.5)
    elif not deps_ok:
        error_prob = min(1.0, base_logical_rate + noise_p * 0.3)
    else:
        error_prob = base_logical_rate * (1.0 - 0.3 * confidence)

    success = rng.random() > error_prob
    return WindowOutcome(
        success=success,
        waited_cycles=waited,
        speculated=speculated,
        speculation_correct=speculation_correct if speculated else True,
    )


def simulate_speculative_decoder(
    noise_p: float = 0.01,
    skip_threshold: float = 0.7,
    shots: int = 1000,
    window_size: int = 4,
    base_logical_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Run speculative window decoder over many shots."""
    if not 0.0 <= skip_threshold <= 1.0:
        raise ValueError("skip_threshold must be in [0, 1]")

    rng = np.random.default_rng(seed)
    outcomes = [
        simulate_window(
            rng,
            noise_p=noise_p,
            skip_threshold=skip_threshold,
            window_size=window_size,
            speculative=True,
            base_logical_rate=base_logical_rate,
        )
        for _ in range(shots)
    ]

    successes = sum(1 for o in outcomes if o.success)
    speculated = sum(1 for o in outcomes if o.speculated)
    correct_spec = sum(
        1 for o in outcomes if o.speculated and o.speculation_correct
    )
    waits = [o.waited_cycles for o in outcomes]

    return {
        "success_probability": successes / shots,
        "mean_wait_cycles": float(np.mean(waits)),
        "speculation_rate": speculated / shots,
        "speculation_accuracy": (
            correct_spec / speculated if speculated else 1.0
        ),
        "skip_threshold": float(skip_threshold),
        "noise_p": float(noise_p),
        "shots": float(shots),
    }


def simulate_naive_decoder(
    noise_p: float = 0.01,
    shots: int = 1000,
    window_size: int = 4,
    base_logical_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Naive baseline: never skip dependency waits."""
    rng = np.random.default_rng(seed)
    outcomes = [
        simulate_window(
            rng,
            noise_p=noise_p,
            skip_threshold=1.0,
            window_size=window_size,
            speculative=False,
            base_logical_rate=base_logical_rate,
        )
        for _ in range(shots)
    ]

    successes = sum(1 for o in outcomes if o.success)
    waits = [o.waited_cycles for o in outcomes]

    return {
        "success_probability": successes / shots,
        "mean_wait_cycles": float(np.mean(waits)),
        "speculation_rate": 0.0,
        "speculation_accuracy": 1.0,
        "noise_p": float(noise_p),
        "shots": float(shots),
    }


def compare_decoders(
    noise_p: float = 0.01,
    skip_threshold: float = 0.7,
    shots: int = 1000,
    window_size: int = 4,
    base_logical_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """Compare speculative and naive decoders on identical noise conditions."""
    speculative = simulate_speculative_decoder(
        noise_p=noise_p,
        skip_threshold=skip_threshold,
        shots=shots,
        window_size=window_size,
        base_logical_rate=base_logical_rate,
        seed=seed,
    )
    naive = simulate_naive_decoder(
        noise_p=noise_p,
        shots=shots,
        window_size=window_size,
        base_logical_rate=base_logical_rate,
        seed=seed,
    )

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
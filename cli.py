"""Headless CLI entry — no Streamlit imports."""

from __future__ import annotations

import json
import sys

from core.simulator import run_simulation


def main() -> int:
    result = run_simulation(
        squeezing_db=10.0,
        noise_p=0.02,
        skip_threshold=0.7,
        shots=1000,
        window_size=4,
        seed=42,
    )

    gkp = result["gkp"]
    dec = result["decoder"]

    print("QEC-Playground Simulation Results")
    print("=" * 40)
    print(f"GKP squeezing:        {gkp['squeezing_db']:.1f} dB")
    print(f"Noise level:          {gkp['noise_p']:.4f}")
    print(f"Logical error rate:   {gkp['logical_error_rate']:.4f}")
    print(f"Physical error rate:  {gkp['physical_error_rate']:.4f}")
    print(f"Mean fidelity:        {gkp['mean_fidelity']:.4f}")
    print()
    print("Speculative Decoder")
    print(f"  Success probability: {dec['speculative']['success_probability']:.4f}")
    print(f"  Mean wait cycles:    {dec['speculative']['mean_wait_cycles']:.2f}")
    print(f"  Speculation rate:    {dec['speculative']['speculation_rate']:.4f}")
    print()
    print("Naive Decoder")
    print(f"  Success probability: {dec['naive']['success_probability']:.4f}")
    print(f"  Mean wait cycles:    {dec['naive']['mean_wait_cycles']:.2f}")
    print()
    print(f"Wait reduction:       {dec['wait_reduction']:.2%}")
    print(f"Success delta:        {dec['success_delta']:+.4f}")

    if "--json" in sys.argv:
        print()
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
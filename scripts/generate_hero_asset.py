"""Regenerate assets/hero.png from a real simulation chart (figure_to_png path)."""

from __future__ import annotations

from pathlib import Path

from core.simulator import run_simulation
from ui.export import figure_to_png
from ui.visualizations import build_all_charts

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "hero.png"


def main() -> None:
    result = run_simulation(shots=400, seed=42, include_syndromes=True)
    charts = build_all_charts(result, result["syndromes"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(figure_to_png(charts["success_probability"]))
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
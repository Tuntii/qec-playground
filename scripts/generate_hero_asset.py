"""Regenerate assets/hero.png as a dashboard-style UI screenshot preview."""

from __future__ import annotations

from pathlib import Path

from core.simulator import run_simulation
from ui.export import figure_to_png
from ui.hero_compose import build_dashboard_hero_figure

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "hero.png"


def main() -> None:
    result = run_simulation(shots=400, seed=42, include_syndromes=True)
    fig = build_dashboard_hero_figure(result, result["syndromes"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(figure_to_png(fig))
    print(f"Wrote dashboard hero {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
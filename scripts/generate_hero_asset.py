"""Regenerate assets/hero.png — Streamlit screenshot or composed dashboard fallback."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.hero_screenshot import (  # noqa: E402
    HeroCaptureError,
    PlaywrightNotReadyError,
    capture_hero_screenshot,
)

OUT = ROOT / "assets" / "hero.png"
APP = ROOT / "app.py"


def compose_dashboard_hero(out_path: Path) -> None:
    """Plotly 2×2 dashboard PNG from default simulation (no browser)."""
    from core.simulator import run_simulation
    from ui.export import figure_to_png
    from ui.hero_compose import build_dashboard_hero_figure
    from ui.sim_params import default_cli_params, to_run_kwargs

    result = run_simulation(**to_run_kwargs(default_cli_params()))
    fig = build_dashboard_hero_figure(result)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(figure_to_png(fig))


def main() -> int:
    try:
        capture_hero_screenshot(APP, OUT, auto_install=True)
        print(f"Wrote Streamlit screenshot hero {OUT} ({OUT.stat().st_size} bytes)")
        return 0
    except PlaywrightNotReadyError as exc:
        print(f"Playwright unavailable, using composed dashboard: {exc}", file=sys.stderr)
    except subprocess.CalledProcessError as exc:
        print(f"Playwright install failed, using composed dashboard: {exc}", file=sys.stderr)
    except HeroCaptureError as exc:
        print(f"Screenshot capture failed, using composed dashboard: {exc}", file=sys.stderr)

    compose_dashboard_hero(OUT)
    print(f"Wrote composed dashboard hero {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
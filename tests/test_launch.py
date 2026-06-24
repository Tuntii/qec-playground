"""Launch / publish artifact checks (README, assets, share URL)."""

from __future__ import annotations

import os
from pathlib import Path

from core.simulator import run_simulation
from ui.export import build_share_url, default_share_base_url, figure_to_png
from ui.hero_compose import build_dashboard_hero_figure
from ui.sliders import SimulationParams

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
HERO = ROOT / "assets" / "hero.png"
ASSETS_DIR = ROOT / "assets"

DEMO_PLACEHOLDER = "YOUR_DEMO_URL"
STAR_CTA = "Star'ını ver ki quantum dünyasında ilk senin tool'un ünlensin 🔥"
ARXIV_LINE = "24 Haziran 2026"


def test_readme_contains_launch_sections(capsys):
    text = README.read_text(encoding="utf-8")
    has_hero_embed = f"![QEC-Playground dashboard" in text and "](assets/hero.png)" in text
    has_install = "pip install -r requirements.txt" in text and "streamlit run app.py" in text
    has_cli = "python cli.py" in text
    has_demo_placeholder = DEMO_PLACEHOLDER in text
    has_star = STAR_CTA in text
    has_arxiv = ARXIV_LINE in text
    print(
        "readme_checks:",
        f"hero_embed={has_hero_embed}",
        f"install={has_install}",
        f"cli_cmd={has_cli}",
        f"demo_placeholder={has_demo_placeholder}",
        f"star_cta={has_star}",
        f"arxiv={has_arxiv}",
    )
    assert has_hero_embed
    assert has_install
    assert has_cli
    assert has_demo_placeholder
    assert has_star
    assert has_arxiv


def test_hero_asset_exists_and_referenced(capsys):
    readme = README.read_text(encoding="utf-8")
    assets = sorted(p.name for p in ASSETS_DIR.glob("*"))
    print(f"hero_exists: {HERO.exists()} size: {HERO.stat().st_size if HERO.exists() else 0}")
    print(f"assets_list: {assets}")
    assert HERO.exists()
    assert HERO.suffix == ".png"
    assert HERO.stat().st_size > 5000
    assert "assets/hero.png" in readme
    assert "hero.png" in assets


def test_dashboard_hero_compose(capsys):
    result = run_simulation(shots=200, seed=42, include_syndromes=True)
    fig = build_dashboard_hero_figure(result, result["syndromes"])
    png = figure_to_png(fig)
    print(f"dashboard_hero_bytes: {len(png)} subplot_count: {len(fig.data)}")
    assert len(fig.data) >= 4
    assert len(png) > 10000


def test_build_share_url_custom_base(capsys):
    params = SimulationParams(
        squeezing_db=10.0,
        noise_p=0.02,
        skip_threshold=0.7,
        shots=200,
        window_size=4,
        surface_distance=3,
        seed=1,
        circuit_id="surface_gkp_d3",
        circuit_name="Surface-GKP distance-3",
    )
    url = build_share_url(params, base_url="https://example.com/demo")
    print(f"share_custom: {url[:50]}...")
    assert url.startswith("https://example.com/demo?")
    assert "circuit=surface_gkp_d3" in url


def test_default_share_base_from_env(monkeypatch, capsys):
    monkeypatch.setenv("QEC_DEMO_BASE_URL", "https://example.com/live")
    base = default_share_base_url()
    print(f"env_base: {base}")
    assert base == "https://example.com/live"


def test_launch_simulation_rates(capsys):
    res = run_simulation(shots=100, seed=99)
    print(f"sim_rates_ok: {'logical_error_rate' in res.get('gkp', {})}")
    assert "logical_error_rate" in res["gkp"]
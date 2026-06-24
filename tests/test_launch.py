"""Launch / publish artifact checks (README, assets, share URL)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from core.simulator import run_simulation
from ui.export import build_share_url, default_share_base_url
from ui.sliders import SimulationParams

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
HERO = ROOT / "assets" / "hero.png"


def test_readme_contains_launch_sections(capsys):
    text = README.read_text(encoding="utf-8")
    print(
        "readme_checks:",
        "hero" in text,
        "pip install" in text,
        "streamlit run app.py" in text,
        "python app.py" in text,
    )
    assert "assets/hero.png" in text
    assert "pip install -r requirements.txt" in text
    assert "streamlit run app.py" in text
    assert "python app.py" in text
    assert "huggingface.co/spaces" in text.lower() or "Interactive demo" in text
    assert re.search(r"star", text, re.I)


def test_hero_asset_exists_and_referenced(capsys):
    readme = README.read_text(encoding="utf-8")
    print(f"hero_exists: {HERO.exists()} size: {HERO.stat().st_size if HERO.exists() else 0}")
    assert HERO.exists()
    assert HERO.suffix == ".png"
    assert HERO.stat().st_size > 1000
    assert "assets/hero.png" in readme


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
    url = build_share_url(
        params,
        base_url="https://huggingface.co/spaces/tunay/qec-playground",
    )
    print(f"share_hf: {url[:60]}...")
    assert url.startswith("https://huggingface.co/spaces/tunay/qec-playground?")
    assert "circuit=surface_gkp_d3" in url


def test_default_share_base_from_env(monkeypatch, capsys):
    monkeypatch.setenv(
        "QEC_DEMO_BASE_URL",
        "https://huggingface.co/spaces/tunay/qec-playground",
    )
    base = default_share_base_url()
    print(f"env_base: {base}")
    assert base == "https://huggingface.co/spaces/tunay/qec-playground"


def test_launch_simulation_rates(capsys):
    res = run_simulation(shots=100, seed=99)
    print(f"sim_rates_ok: {'logical_error_rate' in res.get('gkp', {})}")
    assert "logical_error_rate" in res["gkp"]
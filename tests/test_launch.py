"""Launch / publish artifact checks (README, assets, share URL)."""

from __future__ import annotations

from pathlib import Path

from core.simulator import run_simulation
from launch_contract import (
    HERO_PATH,
    LICENSE_PATH,
    README_PATH,
    SPEC_PATH,
    check_assets,
    check_license,
    check_positioning,
    check_readme,
    check_source_claims,
    check_ui_source_claims,
    find_unqualified_swiper_sim_claims,
)
from ui.export import build_share_url, default_share_base_url, figure_to_png
from ui.hero_compose import build_dashboard_hero_figure
from ui.sim_params import SimulationParams

ROOT = Path(__file__).resolve().parent.parent


def test_readme_contains_launch_sections(capsys):
    text = README_PATH.read_text(encoding="utf-8")
    checks = check_readme(text)
    print("readme_checks:", " ".join(f"{k}={v}" for k, v in checks.items()))
    assert all(checks.values())


def test_source_has_no_unqualified_swiper_sim_claims(capsys):
    violations = find_unqualified_swiper_sim_claims()
    checks = check_source_claims()
    print(f"source_violations: {violations}")
    print(f"source_checks: {checks}")
    assert violations == []
    assert all(checks.values())
    assert checks["core_files_scanned"] is True
    assert checks["test_files_scanned"] is True


def test_license_and_first_open_source_positioning(capsys):
    license_checks = check_license()
    readme = README_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    pos_readme = check_positioning(readme)
    pos_spec = check_positioning(spec)
    print(f"license_checks: {license_checks}")
    print(f"pos_readme: {pos_readme}")
    print(f"pos_spec: {pos_spec}")
    assert LICENSE_PATH.exists()
    assert all(license_checks.values())
    assert all(pos_readme.values())
    assert all(pos_spec.values())


def test_hero_asset_exists_and_referenced(capsys):
    readme = README_PATH.read_text(encoding="utf-8")
    checks = check_assets(readme)
    assets = sorted(p.name for p in (ROOT / "assets").glob("*") if p.is_file())
    print(f"hero_exists: {HERO_PATH.exists()} size: {HERO_PATH.stat().st_size if HERO_PATH.exists() else 0}")
    print(f"assets_list: {assets}")
    assert all(checks.values())


def test_dashboard_hero_compose(capsys):
    result = run_simulation(seed=42)
    fig = build_dashboard_hero_figure(result)
    png = figure_to_png(fig)
    print(f"dashboard_hero_bytes: {len(png)} subplot_count: {len(fig.data)}")
    assert len(fig.data) >= 4
    assert len(png) > 10000


def test_build_share_url_custom_base(capsys):
    params = SimulationParams(
        processor_count=4,
        cycle_time_us=1.0,
        speculation_accuracy=0.9,
        decoder_latency_rounds=2,
        ordering_strategy="shallow_first",
        window_strategy="parallel",
        seed=1,
        schedule_id="three_t_injection",
        schedule_name="Three parallel T-gate injections",
    )
    url = build_share_url(params, base_url="https://example.com/demo")
    print(f"share_custom: {url[:50]}...")
    assert url.startswith("https://example.com/demo?")
    assert "schedule=three_t_injection" in url


def test_default_share_base_from_env(monkeypatch, capsys):
    monkeypatch.setenv("QEC_DEMO_BASE_URL", "https://example.com/live")
    base = default_share_base_url()
    print(f"env_base: {base}")
    assert base == "https://example.com/live"


def test_launch_simulation_metrics(capsys):
    res = run_simulation(seed=99)
    print(f"sim_metrics_ok: {'average_conditional_wait_time_us' in res['speculative']}")
    assert "average_conditional_wait_time_us" in res["speculative"]
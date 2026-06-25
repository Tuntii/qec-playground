"""Single source of truth for launch README/assets acceptance checks."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
README_PATH = ROOT / "README.md"
SPEC_PATH = ROOT / "spec.md"
LICENSE_PATH = ROOT / "LICENSE"
HERO_PATH = ROOT / "assets" / "hero.png"
ASSETS_DIR = ROOT / "assets"

DEMO_URL = "https://huggingface.co/spaces/Tunti35/qec-playground"
DEMO_PLACEHOLDER = "YOUR_DEMO_URL"  # legacy marker; live demo uses DEMO_URL
STAR_CTA = "Star'ını ver ki quantum dünyasında ilk senin tool'un ünlensin 🔥"
PAPER_TITLE = "An Analysis of Speculative Window Decoders for Quantum Error Correction"
PAPER_AUTHORS = "Jocelyn Li and Margaret Martonosi"
PAPER_ARXIV = "arXiv:2606.24048"
SWIPER_REPO_MARKER = "github.com/jviszlai/swiper"
FIRST_OSS_MARKER = "first open-source"
FULL_SWIPER_MARKER = "full SWIPER-SIM"
BEHAVIORAL_MODEL_MARKER = "behavioral model"
CLI_CMD = "python app.py"
HERO_MARKDOWN_REF = "assets/hero.png"
LICENSE_MARKDOWN_REF = "LICENSE"

CLI_REQUIRED_MARKERS = (
    "QEC-Playground Simulation Results",
    "Conditional wait reduction",
    "Total decoding time",
    "Max concurrent decoders",
    "Completed",
)

OVERCLAIM_MARKERS = (
    "official SWIPER-SIM release",
    "exact reproduction of the paper",
    "line-for-line port",
)

UI_SOURCE_PATHS = (ROOT / "app.py",) + tuple(sorted((ROOT / "ui").glob("*.py")))
CORE_SOURCE_PATHS = (
    ROOT / "core" / "device_manager.py",
    ROOT / "core" / "window_manager.py",
    ROOT / "core" / "decoder_manager.py",
    ROOT / "core" / "syndrome_graph.py",
    ROOT / "core" / "matching_decoder.py",
    ROOT / "core" / "swiper_sim.py",
    ROOT / "core" / "simulator.py",
    ROOT / "core" / "schedule.py",
    ROOT / "core" / "decoder.py",
    ROOT / "core" / "__init__.py",
)
SYNDROME_GRAPH_MARKER = "syndrome graph"
MATCHING_DECODER_MARKER = "matching decoder"
MANAGER_MARKER = "DeviceManager"
TEST_SOURCE_PATHS = tuple(sorted((ROOT / "tests").glob("test_*.py")))
SOURCE_SCAN_PATHS = UI_SOURCE_PATHS + CORE_SOURCE_PATHS + TEST_SOURCE_PATHS

SWIPER_SIM_SCOPING = (
    "behavioral",
    "lightweight",
    "li & martonosi",
    "round-stepped",
    "arxiv",
    "isca 2025",
    "paper metrics",
    "jviszlai",
    "managers",
    "devicemanager",
    "reimplementation",
    "strategies",
    "manager modules",
)


def find_unqualified_swiper_sim_claims() -> list[str]:
    """Lines containing SWIPER-SIM without an approved scoping qualifier."""
    violations: list[str] = []
    for path in SOURCE_SCAN_PATHS:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "SWIPER-SIM" not in line:
                continue
            lower = line.lower()
            if any(qualifier in lower for qualifier in SWIPER_SIM_SCOPING):
                continue
            violations.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")
    return violations


def check_ui_source_claims() -> dict[str, bool]:
    return check_source_claims()


def check_source_claims() -> dict[str, bool]:
    violations = find_unqualified_swiper_sim_claims()
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    core_scanned = all(p.exists() for p in CORE_SOURCE_PATHS)
    tests_scanned = len(TEST_SOURCE_PATHS) > 0
    return {
        "no_unqualified_swiper_sim": len(violations) == 0,
        "core_files_scanned": core_scanned,
        "test_files_scanned": tests_scanned,
        "app_has_paper_title": PAPER_TITLE in app_text,
        "app_has_paper_authors": PAPER_AUTHORS in app_text,
        "app_has_paper_arxiv": PAPER_ARXIV in app_text,
        "app_has_full_swiper_scope": FULL_SWIPER_MARKER.lower() in app_text.lower()
        or BEHAVIORAL_MODEL_MARKER in app_text.lower(),
        "managers_present": MANAGER_MARKER in (ROOT / "core" / "device_manager.py").read_text(encoding="utf-8"),
    }


def check_license() -> dict[str, bool]:
    text = LICENSE_PATH.read_text(encoding="utf-8") if LICENSE_PATH.exists() else ""
    return {
        "license_exists": LICENSE_PATH.exists(),
        "mit_license": "MIT License" in text,
        "paper_citation": PAPER_ARXIV in text,
        "swiper_scope_note": FULL_SWIPER_MARKER.lower() in text.lower()
        or BEHAVIORAL_MODEL_MARKER in text.lower(),
    }


def check_positioning(text: str) -> dict[str, bool]:
    lower = text.lower()
    return {
        "first_open_source": FIRST_OSS_MARKER in lower,
        "full_swiper_implementation": FULL_SWIPER_MARKER.lower() in lower
        or "full swiper-sim behavioral" in lower,
        "swiper_repo_linked": SWIPER_REPO_MARKER in text,
        "behavioral_model_scoped": BEHAVIORAL_MODEL_MARKER in lower or "managers" in lower,
        "no_overclaim_official": "official swiper-sim release" not in lower,
        "no_overclaim_exact_paper": "exact reproduction of the paper" not in lower,
    }


def check_readme(text: str) -> dict[str, bool]:
    checks = {
        "hero_embed": "![QEC-Playground dashboard" in text and f"]({HERO_MARKDOWN_REF})" in text,
        "install": "pip install -r requirements.txt" in text and "streamlit run app.py" in text,
        "cli": CLI_CMD in text,
        "demo_linked": DEMO_URL in text,
        "star_cta": STAR_CTA in text,
        "paper_title": PAPER_TITLE in text,
        "paper_authors": PAPER_AUTHORS in text,
        "paper_arxiv": PAPER_ARXIV in text,
        "assets_path": HERO_MARKDOWN_REF in text,
        "license_linked": LICENSE_MARKDOWN_REF in text,
        "syndrome_graph_described": SYNDROME_GRAPH_MARKER in text.lower(),
        "matching_decoder_described": MATCHING_DECODER_MARKER in text.lower(),
        "managers_described": "devicemanager" in text.lower() or "device manager" in text.lower(),
    }
    checks.update(check_positioning(text))
    return checks


def check_assets(readme_text: str | None = None) -> dict[str, bool]:
    readme = readme_text if readme_text is not None else README_PATH.read_text(encoding="utf-8")
    assets = sorted(p.name for p in ASSETS_DIR.glob("*") if p.is_file())
    hero_size = HERO_PATH.stat().st_size if HERO_PATH.exists() else 0
    return {
        "hero_exists": HERO_PATH.exists(),
        "hero_is_png": HERO_PATH.suffix == ".png",
        "hero_size_ok": hero_size > 5000,
        "readme_references_hero": HERO_MARKDOWN_REF in readme,
        "hero_listed_in_assets": "hero.png" in assets,
        "has_image_asset": any(name.endswith((".png", ".gif")) for name in assets),
    }


def format_readme_checks(checks: dict[str, bool]) -> str:
    lines = ["README_READ_ASSERTIONS:"]
    for key, value in checks.items():
        lines.append(f"  {key}: {value}")
    if all(checks.values()):
        lines.append("README_READ_OK")
    else:
        lines.append("README_READ_FAIL")
    return "\n".join(lines)


def format_license_checks(checks: dict[str, bool]) -> str:
    lines = ["LICENSE_ASSERTIONS:"]
    for key, value in checks.items():
        lines.append(f"  {key}: {value}")
    if all(checks.values()):
        lines.append("LICENSE_OK")
    else:
        lines.append("LICENSE_FAIL")
    return "\n".join(lines)


def format_ui_source_checks(
    checks: dict[str, bool],
    *,
    violations: list[str],
) -> str:
    lines = ["UI_SOURCE_ASSERTIONS:", f"  violations: {violations}"]
    for key, value in checks.items():
        lines.append(f"  {key}: {value}")
    if all(checks.values()):
        lines.append("UI_SOURCE_OK")
    else:
        lines.append("UI_SOURCE_FAIL")
    return "\n".join(lines)


def format_positioning_checks(checks: dict[str, bool]) -> str:
    lines = ["POSITIONING_ASSERTIONS:"]
    for key, value in checks.items():
        lines.append(f"  {key}: {value}")
    if all(checks.values()):
        lines.append("POSITIONING_OK")
    else:
        lines.append("POSITIONING_FAIL")
    return "\n".join(lines)


def format_assets_checks(checks: dict[str, bool], *, assets: list[str]) -> str:
    lines = ["ASSETS_LS_ASSERTIONS:", f"  assets_list: {assets}"]
    for key, value in checks.items():
        lines.append(f"  {key}: {value}")
    if all(checks.values()):
        lines.append("ASSETS_LS_OK")
    else:
        lines.append("ASSETS_LS_FAIL")
    return "\n".join(lines)


STALE_SCRATCH_ARTIFACTS = (
    "readme_read.py",
    "streamlit_smoke.py",
    "cli_run1.log",
    "cli_run2.log",
    "streamlit_run.log",
)


def resolve_scratch_dir(explicit: Path | None = None) -> Path:
    """Portable evidence directory: --scratch > QEC_GATING_SCRATCH > .gating-evidence."""
    if explicit is not None:
        return explicit.expanduser().resolve()
    env = os.environ.get("QEC_GATING_SCRATCH")
    if env:
        return Path(env).expanduser().resolve()
    return (ROOT / ".gating-evidence").resolve()


def clean_stale_scratch_artifacts(scratch: Path) -> list[str]:
    removed: list[str] = []
    for name in STALE_SCRATCH_ARTIFACTS:
        path = scratch / name
        if path.exists():
            path.unlink()
            removed.append(name)
    return removed


def check_cli_output(text: str) -> dict[str, bool]:
    return {
        "header": CLI_REQUIRED_MARKERS[0] in text,
        "conditional_wait_reduction": CLI_REQUIRED_MARKERS[1] in text,
        "total_decoding_time": CLI_REQUIRED_MARKERS[2] in text,
        "max_concurrent_decoders": CLI_REQUIRED_MARKERS[3] in text,
        "completed_status": CLI_REQUIRED_MARKERS[4] in text,
        "has_numeric_values": any(ch.isdigit() for ch in text),
    }
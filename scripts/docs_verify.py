"""Capture README/spec/app doc verification evidence for launch gating."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.result_summary import PAPER_ARXIV, PAPER_AUTHORS, PAPER_TITLE  # noqa: E402

MARKERS = (PAPER_TITLE, PAPER_AUTHORS, PAPER_ARXIV)
GKP_PRIMARY_CLAIMS = (
    "Surface-GKP kodlarında",
    "QuTiP ile GKP simülasyonu",
    "Surface-GKP + Speculative Window Decoders",
)
FIRST_OSS_MARKERS = ("first open-source",)
SWIPER_MARKERS = ("full SWIPER-SIM", "DeviceManager", "behavioral model")
OVERCLAIM_MARKERS = ("official SWIPER-SIM release", "exact reproduction of the paper")
NEGATED_OLD_CLAIMS = ("not physical syndrome graphs", "not the full")


def main() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    spec = (ROOT / "spec.md").read_text(encoding="utf-8")
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")

    lines = ["DOCS_VERIFY_ASSERTIONS:"]
    for marker in MARKERS:
        lines.append(
            f"  {marker!r}: readme={marker in readme} spec={marker in spec} app={marker in app_src}"
        )
    for claim in GKP_PRIMARY_CLAIMS:
        lines.append(
            f"  gkp_primary_absent({claim!r}): readme={claim not in readme} spec={claim not in spec}"
        )
    for marker in FIRST_OSS_MARKERS:
        lines.append(f"  positioning({marker!r}): readme={marker in readme.lower()}")
    for marker in SWIPER_MARKERS:
        lines.append(
            f"  swiper_model({marker!r}): readme={marker in readme} spec={marker in spec}"
        )
    for claim in NEGATED_OLD_CLAIMS:
        lines.append(f"  old_scope_absent({claim!r}): readme={claim not in readme.lower()}")
    for marker in OVERCLAIM_MARKERS:
        lines.append(f"  no_overclaim({marker!r}): readme={marker.lower() not in readme.lower()}")
    lines.append(f"  LICENSE_exists: {(ROOT / 'LICENSE').exists()}")
    lines.append("README_EXCERPT:")
    lines.append(readme.splitlines()[0])
    lines.append(readme.splitlines()[2])
    lines.append("SPEC_EXCERPT:")
    lines.append(spec.splitlines()[3])
    docs_ok = all(marker in readme and marker in spec and marker in app_src for marker in MARKERS)
    if docs_ok:
        lines.append("DOCS_VERIFY_OK")
    else:
        lines.append("DOCS_VERIFY_FAIL")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Print authoritative CHANGED_FILES from git status; tag deletions in DEVIATIONS."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Delete-only paths — listed under DEVIATIONS, never CHANGED_FILES (plan.md Deviations).
DEVIATION_DELETES = frozenset({"cli.py"})

# Evidence scratch dirs must not appear in CHANGED_FILES.
EXCLUDE_PATHS = frozenset({".gating-evidence", ".gating-evidence/"})


def _parse_porcelain_path(raw: str) -> str:
    path = raw.strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path.replace("\\\\", "/")


def main() -> int:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    changed: list[str] = []
    deviations: list[str] = []

    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        path = _parse_porcelain_path(line[3:])
        if not path or path in EXCLUDE_PATHS or path.startswith(".gating-evidence/"):
            continue

        if "D" in xy and path in DEVIATION_DELETES:
            deviations.append(f"D {path} (consolidated into app.py)")
            continue
        if path in DEVIATION_DELETES:
            continue

        if xy == "??":
            changed.append(f"A {path}")
        elif xy.strip() == "D" or (xy[0] == " " and xy[1] == "D") or (xy[0] == "D" and xy[1] == " "):
            changed.append(f"D {path}")
        elif "M" in xy or "A" in xy or "R" in xy or "C" in xy:
            changed.append(f"M {path}")
        else:
            changed.append(f"? {path}")

    print("CHANGED_FILES:")
    for entry in sorted(changed):
        print(entry)
    if deviations:
        print("DEVIATIONS:")
        for entry in deviations:
            print(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
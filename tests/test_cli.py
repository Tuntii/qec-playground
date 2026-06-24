"""CLI entry point tests."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_cli_emits_simulation_results(capsys):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "cli.py")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=60,
    )
    out = proc.stdout
    print(f"cli_exit: {proc.returncode} stderr_len: {len(proc.stderr)}")
    print(f"cli_has_header: {'QEC-Playground Simulation Results' in out}")
    assert proc.returncode == 0
    assert proc.stderr == ""
    assert "QEC-Playground Simulation Results" in out
    assert "Logical error rate" in out
    assert "Wait reduction" in out
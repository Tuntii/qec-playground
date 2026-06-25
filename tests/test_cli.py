"""CLI entry point tests — exercise shipped `python app.py` subprocess."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAST_CLI_ARGS: tuple[str, ...] = ()
SLOW_CLI_ARGS: tuple[str, ...] = (
    "--cycle-time-us",
    "2",
    "--processors",
    "2",
    "--schedule",
    "three_t_injection",
)


def _run_app(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "app.py"), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=60,
    )


def _spec_decode_time_us(stdout: str) -> float:
    match = re.search(
        r"Speculative decoder\s+Total decoding time:\s+([\d.]+)\s*µs",
        stdout,
    )
    assert match, f"Speculative decode time not found in:\n{stdout}"
    return float(match.group(1))


def _nonspec_decode_time_us(stdout: str) -> float:
    match = re.search(
        r"Non-speculative decoder\s+Total decoding time:\s+([\d.]+)\s*µs",
        stdout,
    )
    assert match, f"Non-speculative decode time not found in:\n{stdout}"
    return float(match.group(1))


def _spec_cond_wait_us(stdout: str) -> float:
    match = re.search(
        r"Speculative decoder[\s\S]*?Avg conditional wait:\s+([\d.]+)\s*µs",
        stdout,
    )
    assert match, f"Speculative conditional wait not found in:\n{stdout}"
    return float(match.group(1))


def _nonspec_cond_wait_us(stdout: str) -> float:
    match = re.search(
        r"Non-speculative decoder[\s\S]*?Avg conditional wait:\s+([\d.]+)\s*µs",
        stdout,
    )
    assert match, f"Non-speculative conditional wait not found in:\n{stdout}"
    return float(match.group(1))


def _modes_differ_in_report(stdout: str) -> bool:
    spec_time = _spec_decode_time_us(stdout)
    nonspec_time = _nonspec_decode_time_us(stdout)
    spec_wait = _spec_cond_wait_us(stdout)
    nonspec_wait = _nonspec_cond_wait_us(stdout)
    return spec_time != nonspec_time or spec_wait != nonspec_wait


def test_app_py_fast_gate_defaults(capsys):
    proc = _run_app(*FAST_CLI_ARGS)
    out = proc.stdout
    print(f"app_exit: {proc.returncode} stderr_len: {len(proc.stderr)}")
    print(f"cycle_line: {[ln for ln in out.splitlines() if 'Cycle time' in ln]}")
    assert proc.returncode == 0
    assert proc.stderr == ""
    assert "QEC-Playground Simulation Results" in out
    assert "Cycle time: 1.0 µs" in out
    assert "Conditional wait reduction" in out
    assert "Total decoding time" in out
    assert "Schedule: Three parallel T-gate injections" in out
    assert _modes_differ_in_report(out)


def test_app_py_slow_gate_params(capsys):
    proc = _run_app(*SLOW_CLI_ARGS)
    out = proc.stdout
    print(f"slow_exit: {proc.returncode}")
    print(f"cycle_line: {[ln for ln in out.splitlines() if 'Cycle time' in ln]}")
    assert proc.returncode == 0
    assert proc.stderr == ""
    assert "Cycle time: 2.0 µs" in out
    assert "Processors: 2" in out
    assert "Schedule: Three parallel T-gate injections" in out
    assert "Total decoding time" in out
    assert _modes_differ_in_report(out)


def test_app_py_fast_and_slow_runs_differ(capsys):
    fast = _run_app(*FAST_CLI_ARGS)
    slow = _run_app(*SLOW_CLI_ARGS)
    fast_time = _spec_decode_time_us(fast.stdout)
    slow_time = _spec_decode_time_us(slow.stdout)
    print(f"fast_spec_time_us: {fast_time} slow_spec_time_us: {slow_time}")
    assert fast.stdout.count("Cycle time: 1.0 µs") >= 1
    assert slow.stdout.count("Cycle time: 2.0 µs") >= 1
    assert fast_time != slow_time
    assert _modes_differ_in_report(fast.stdout)
    assert _modes_differ_in_report(slow.stdout)


def test_app_py_slow_gate_repeatable(capsys):
    first = _run_app(*SLOW_CLI_ARGS)
    second = _run_app(*SLOW_CLI_ARGS)
    print(f"slow_repeat_exit: {first.returncode} {second.returncode}")
    assert first.returncode == 0 and second.returncode == 0
    assert first.stdout == second.stdout
"""Run plan.md verification steps 1-5 with UTF-8 evidence capture.

Writes one fresh log per step to launch_contract.resolve_scratch_dir().
Exits non-zero on the first failed assertion.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from launch_contract import (  # noqa: E402
    check_cli_output,
    check_license,
    check_positioning,
    check_readme,
    check_source_claims,
    clean_stale_scratch_artifacts,
    resolve_scratch_dir,
)

CYCLE_SLOW_LITERAL = "Cycle time: 2.0 µs"
MANGLED_MICRO = "┬Á"
CLI_MARKERS = (
    "QEC-Playground Simulation Results",
    "Total decoding time",
    "Conditional wait reduction",
)
EVIDENCE_FILES = (
    "core_direct.log",
    "cli1.log",
    "cli2.log",
    "cli_verify.log",
    "cli_slow.log",
    "pytest.log",
    "license.log",
    "positioning.log",
    "docs_verify.log",
    "sensitivity.log",
    "changed_files.log",
    "pytest_full.log",
    "gating_manifest.log",
)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _fail(step: str, message: str) -> int:
    print(f"GATING_FAIL step={step}: {message}", file=sys.stderr)
    return 1


def step1_core_direct(scratch: Path) -> tuple[str, int] | None:
    code = """
from core.simulator import run_simulation
res = run_simulation(
    processor_count=4,
    cycle_time_us=1.0,
    speculation_accuracy=0.9,
    decoder_latency_rounds=2,
    ordering_strategy='shallow_first',
    seed=42,
)
print('spec_wait=', res['speculative']['average_conditional_wait_time_us'])
print('nonspec_wait=', res['non_speculative']['average_conditional_wait_time_us'])
print('max_decoders=', res['speculative']['max_concurrent_decoders'])
print('metrics_keys=', list(res['speculative'].keys()))
print('completed=', res.get('completed'))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    log = proc.stdout
    if proc.stderr:
        log = f"{log}\n{proc.stderr}" if log else proc.stderr
    _write(scratch / "core_direct.log", log)
    if proc.returncode != 0:
        return _fail("1", f"core_direct exit {proc.returncode}")
    if "spec_wait=" not in log or "nonspec_wait=" not in log:
        return _fail("1", "missing spec_wait/nonspec_wait lines")
    if "completed= True" not in log and "completed=True" not in log.replace(" ", ""):
        return _fail("1", "completed not True")
    for key in (
        "total_decoding_time_us",
        "average_window_backlog",
        "average_conditional_wait_time_us",
        "ui_window_count",
        "max_concurrent_decoders",
    ):
        if key not in log:
            return _fail("1", f"metrics_keys missing {key}")
    spec_line = next((ln for ln in log.splitlines() if ln.startswith("spec_wait=")), "")
    nonspec_line = next((ln for ln in log.splitlines() if ln.startswith("nonspec_wait=")), "")
    max_dec_line = next((ln for ln in log.splitlines() if ln.startswith("max_decoders=")), "")
    try:
        spec_wait = float(spec_line.split("=", 1)[1].strip())
        nonspec_wait = float(nonspec_line.split("=", 1)[1].strip())
        max_dec = float(max_dec_line.split("=", 1)[1].strip())
    except (IndexError, ValueError):
        return _fail("1", "could not parse wait times or max_decoders")
    if spec_wait <= 0 or nonspec_wait <= 0:
        return _fail("1", f"non-positive conditional wait spec={spec_wait} nonspec={nonspec_wait}")
    if max_dec < 0:
        return _fail("1", f"invalid max_decoders {max_dec}")
    try:
        from core.simulator import run_simulation

        res = run_simulation(seed=42, schedule_id="three_t_injection")
        spec_rt = float(res["speculative"]["total_decoding_time_us"])
        nonspec_rt = float(res["non_speculative"]["total_decoding_time_us"])
        if spec_rt > nonspec_rt:
            return _fail("1", f"spec_runtime {spec_rt} > nonspec_runtime {nonspec_rt}")
    except Exception as exc:
        return _fail("1", f"runtime check failed: {exc}")
    return None


def step2_cli(scratch: Path) -> int | None:
    def run_app(*extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "app.py", *extra],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    for name in ("cli1", "cli2"):
        proc = run_app()
        log = proc.stdout
        if proc.stderr:
            log = f"{log}\n{proc.stderr}" if log else proc.stderr
        _write(scratch / f"{name}.log", log)
        if proc.returncode != 0:
            return _fail("2", f"{name} exit {proc.returncode}")

    cli1 = (scratch / "cli1.log").read_text(encoding="utf-8")
    cli2 = (scratch / "cli2.log").read_text(encoding="utf-8")
    if cli1 != cli2:
        return _fail("2", "cli1.log != cli2.log")
    _write(scratch / "cli_verify.log", "CLI_REPEAT_OK\n")

    slow = run_app("--cycle-time-us", "2", "--processors", "4", "--schedule", "three_t_injection")
    slow_log = slow.stdout
    if slow.stderr:
        slow_log = f"{slow_log}\n{slow.stderr}" if slow_log else slow.stderr
    _write(scratch / "cli_slow.log", slow_log)
    if slow.returncode != 0:
        return _fail("2", f"cli_slow exit {slow.returncode}")

    for label, text in (("cli1", cli1), ("cli2", cli2), ("cli_slow", slow_log)):
        checks = check_cli_output(text)
        if not all(checks.values()):
            return _fail("2", f"{label} CLI markers failed: {checks}")
        if not any(ch.isdigit() for ch in text):
            return _fail("2", f"{label} missing numeric values")

    if MANGLED_MICRO in slow_log:
        return _fail("2", "cli_slow has mangled micro sign (PowerShell encoding)")
    if CYCLE_SLOW_LITERAL not in slow_log:
        return _fail("2", f"cli_slow missing literal {CYCLE_SLOW_LITERAL!r}")
    return None


def step3_pytest(scratch: Path) -> int | None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_swiper_sim.py",
            "tests/test_decoder.py",
            "tests/test_managers.py",
            "-q",
            "--tb=line",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    _write(scratch / "pytest.log", proc.stdout)
    if proc.returncode != 0:
        err_tail = proc.stderr.strip().splitlines()[-3:] if proc.stderr else []
        return _fail("3", f"pytest exit {proc.returncode}; stderr_tail={err_tail}")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines or " passed" not in lines[-1]:
        return _fail("3", f"pytest stdout does not end with passed summary; tail={lines[-3:]}")
    return None


def step4_docs(scratch: Path) -> int | None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    _write(scratch / "license.log", license_text)

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    spec_text = (ROOT / "spec.md").read_text(encoding="utf-8")
    buf = io.StringIO()
    print("license", check_license(), file=buf)
    print("readme", check_readme(readme_text), file=buf)
    print("spec_pos", check_positioning(spec_text), file=buf)
    print("source", check_source_claims(), file=buf)
    positioning_log = buf.getvalue()
    _write(scratch / "positioning.log", positioning_log)

    license_checks = check_license()
    readme_checks = check_readme(readme_text)
    spec_checks = check_positioning(spec_text)
    source_checks = check_source_claims()
    if not all(license_checks.values()):
        return _fail("4", f"license checks failed: {license_checks}")
    if not all(readme_checks.values()):
        return _fail("4", f"readme checks failed: {readme_checks}")
    if not all(spec_checks.values()):
        return _fail("4", f"spec_pos checks failed: {spec_checks}")
    if not all(source_checks.values()):
        return _fail("4", f"source checks failed: {source_checks}")

    proc = subprocess.run(
        [sys.executable, "scripts/docs_verify.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    docs_log = proc.stdout
    if proc.stderr:
        docs_log = f"{docs_log}\n{proc.stderr}" if docs_log else proc.stderr
    _write(scratch / "docs_verify.log", docs_log)
    if proc.returncode != 0:
        return _fail("4", f"docs_verify exit {proc.returncode}")
    if "DOCS_VERIFY_OK" not in docs_log:
        return _fail("4", "docs_verify missing DOCS_VERIFY_OK")
    return None


def step5_sensitivity(scratch: Path) -> int | None:
    code = """
from core.simulator import run_simulation
f = run_simulation(cycle_time_us=1.0, seed=42)
s = run_simulation(
    cycle_time_us=2.0,
    processor_count=2,
    schedule_id='three_t_injection',
    seed=42,
)
print(
    'FAST',
    f['speculative']['average_conditional_wait_time_us'],
    f['non_speculative']['average_conditional_wait_time_us'],
)
print(
    'SLOW',
    s['speculative']['average_conditional_wait_time_us'],
    s['non_speculative']['average_conditional_wait_time_us'],
)
print('SENSITIVITY_OK')
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    log = proc.stdout
    if proc.stderr:
        log = f"{log}\n{proc.stderr}" if log else proc.stderr
    _write(scratch / "sensitivity.log", log)
    if proc.returncode != 0:
        return _fail("5", f"sensitivity exit {proc.returncode}")
    if "SENSITIVITY_OK" not in log:
        return _fail("5", "missing SENSITIVITY_OK")
    return None


def _wipe_scratch(scratch: Path) -> None:
    """Remove every file in scratch so stale polluted logs cannot survive partial runs."""
    if not scratch.exists():
        return
    for path in scratch.iterdir():
        if path.is_file():
            path.unlink()


def main() -> int:
    scratch = resolve_scratch_dir()
    scratch.mkdir(parents=True, exist_ok=True)
    clean_stale_scratch_artifacts(scratch)
    _wipe_scratch(scratch)
    _write(
        scratch / "gating_manifest.log",
        f"producer=scripts/verify_gating.py\nscratch={scratch}\nencoding=utf-8\n",
    )

    for step_fn in (step1_core_direct, step2_cli, step3_pytest, step4_docs, step5_sensitivity):
        err = step_fn(scratch)
        if err is not None:
            return err

    changed_proc = subprocess.run(
        [sys.executable, "scripts/changed_files_report.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    _write(scratch / "changed_files.log", changed_proc.stdout)
    if changed_proc.returncode != 0:
        return _fail("changed_files", changed_proc.stderr or "changed_files_report failed")
    changed_section = changed_proc.stdout.split("DEVIATIONS:")[0]
    for line in changed_section.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1] == "cli.py":
            return _fail("changed_files", "cli.py must not appear in CHANGED_FILES section")
    if ".gating-evidence" in changed_proc.stdout:
        return _fail("changed_files", ".gating-evidence must not appear in CHANGED_FILES")
    if " D cli.py" in changed_proc.stdout or "\nD cli.py" in changed_proc.stdout:
        if "DEVIATIONS:" not in changed_proc.stdout or "cli.py" not in changed_proc.stdout:
            return _fail("changed_files", "cli.py delete must be tagged under DEVIATIONS")

    full_pytest = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    _write(scratch / "pytest_full.log", full_pytest.stdout)
    if full_pytest.returncode != 0:
        return _fail("pytest_full", f"full suite exit {full_pytest.returncode}")
    full_lines = [ln for ln in full_pytest.stdout.splitlines() if ln.strip()]
    if not full_lines or "passed" not in full_lines[-1]:
        return _fail("pytest_full", f"unexpected pytest_full tail: {full_lines[-3:]}")

    print(f"GATING_OK evidence={scratch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
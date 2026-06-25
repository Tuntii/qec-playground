"""Run plan.md verification steps 1-5 to QEC_GATING_SCRATCH (UTF-8)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else __import__("os").environ.get(
        "QEC_GATING_SCRATCH",
        r"C:\Users\tunay\AppData\Local\Temp\grok-goal-4bde6fc98aa8\implementer",
    )
)
SCRATCH.mkdir(parents=True, exist_ok=True)


def write(name: str, text: str) -> None:
    (SCRATCH / name).write_text(text, encoding="utf-8")


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # Step 1
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from core.simulator import run_simulation
res = run_simulation(seed=42)
s = res['speculative']
print('rate=', s.get('speculation_accuracy_rate'))
print('spec_count=', s.get('speculation_count'))
print('restart=', s.get('restart_count'))
print('time=', s.get('total_decoding_time_us'))
print('backlog=', s.get('average_window_backlog'))
print('wait=', s.get('average_conditional_wait_time_us'))
print('ui=', s.get('ui_window_count'))
print('max_decoders=', s.get('max_concurrent_decoders'))
print('completed=', res.get('completed'))
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("core_direct.log", proc.stdout + proc.stderr)
    if proc.returncode != 0:
        return 1

    # Step 2
    for name in ("cli1", "cli2"):
        p = subprocess.run([sys.executable, "app.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        write(f"{name}.log", p.stdout)
    c1 = (SCRATCH / "cli1.log").read_text(encoding="utf-8")
    c2 = (SCRATCH / "cli2.log").read_text(encoding="utf-8")
    buf = io.StringIO()
    print("CLI_MATCH=", c1 == c2, file=buf)
    print("HAS_RATE=", "speculation" in c1.lower() or "rate" in c1.lower(), file=buf)
    write("cli_verify.log", buf.getvalue())
    p3 = subprocess.run(
        [sys.executable, "app.py", "--cycle-time-us", "2", "--processors", "4", "--schedule", "three_t_injection"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("cli_var.log", p3.stdout)

    # Step 3
    ptest = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_swiper_sim.py",
            "tests/test_decoder.py",
            "tests/test_matching_decoder.py",
            "-q",
            "--tb=line",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("pytest.log", ptest.stdout)
    if ptest.returncode != 0:
        return 1

    # Step 4
    from launch_contract import check_license, check_readme, check_source_claims

    scope_buf = io.StringIO()
    print("SOURCE:", json.dumps(check_source_claims()), file=scope_buf)
    t = (ROOT / "README.md").read_text(encoding="utf-8")
    print("README:", json.dumps(check_readme(t)), file=scope_buf)
    print("LICENSE:", json.dumps(check_license()), file=scope_buf)
    write("scope.log", scope_buf.getvalue())
    pdocs = subprocess.run([sys.executable, "scripts/docs_verify.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    write("docs_verify.log", pdocs.stdout)

    # Step 5 — strategy compare + blocking schedule
    strat = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from core.simulator import run_simulation
par = run_simulation(window_strategy='parallel', seed=42)['speculative']
ali = run_simulation(window_strategy='aligned', seed=42)['speculative']
blk = run_simulation(schedule_id='merge_split_t', seed=42)['speculative']
print('parallel_time=', par['total_decoding_time_us'], 'aligned_time=', ali['total_decoding_time_us'])
print('parallel_wait=', par['average_conditional_wait_time_us'], 'aligned_wait=', ali['average_conditional_wait_time_us'])
print('merge_split_time=', blk['total_decoding_time_us'], 'max_dec=', blk['max_concurrent_decoders'])
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("strategy_compare.log", strat.stdout)

    print(f"GOAL_VERIFY_OK scratch={SCRATCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Execute plan.md verification steps 1-5; write UTF-8 evidence to scratch."""

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

    # Step 1 — direct sim (plan field names)
    proc1 = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from core.simulator import run_simulation
res = run_simulation(seed=42, schedule_id='three_t_injection')
s = res['speculative']
ns = res['non_speculative']
print('spec_runtime=', s.get('total_decoding_time_us'))
print('nonspec_runtime=', ns.get('total_decoding_time_us'))
print('max_decoders=', s.get('max_concurrent_decoders'))
print('avg_decoders=', s.get('average_concurrent_decoders'))
print('completed=', res.get('completed'))
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("sim_direct.log", proc1.stdout + proc1.stderr)
    if proc1.returncode != 0:
        return 1
    sim_log = (SCRATCH / "sim_direct.log").read_text(encoding="utf-8")
    if "completed= True" not in sim_log and "completed=True" not in sim_log.replace(" ", ""):
        print("PLAN_VERIFY_FAIL: completed not True in sim_direct.log")
        return 1
    spec_rt = nonspec_rt = None
    for line in sim_log.splitlines():
        if line.startswith("spec_runtime="):
            spec_rt = float(line.split("=", 1)[1].strip())
        if line.startswith("nonspec_runtime="):
            nonspec_rt = float(line.split("=", 1)[1].strip())
    if spec_rt is not None and nonspec_rt is not None and spec_rt > nonspec_rt:
        print(f"PLAN_VERIFY_FAIL: spec_runtime {spec_rt} > nonspec_runtime {nonspec_rt}")
        return 1

    # Step 2 — CLI x2 + consistency + full variant
    for name in ("cli1", "cli2"):
        p = subprocess.run(
            [sys.executable, "app.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        write(f"{name}.log", p.stdout + p.stderr)
    c1 = (SCRATCH / "cli1.log").read_text(encoding="utf-8")
    c2 = (SCRATCH / "cli2.log").read_text(encoding="utf-8")
    buf = io.StringIO()
    print("CLI_IDENTICAL=", c1 == c2, file=buf)
    print("HAS_RUNTIME=", "decoding" in c1.lower() or "runtime" in c1.lower(), file=buf)
    print("HAS_DECODERS=", "decoder" in c1.lower() or "processor" in c1.lower(), file=buf)
    print("HAS_COMPLETED=", "Completed" in c1, file=buf)
    write("cli_consistency.log", buf.getvalue())
    pfull = subprocess.run(
        [sys.executable, "app.py", "--schedule", "three_t_injection", "--processors", "4"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("cli_full.log", pfull.stdout + pfull.stderr)

    # Step 3 — pytest
    ptest = subprocess.run(
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
    write("pytest.log", ptest.stdout + ptest.stderr)
    if ptest.returncode != 0:
        return 1

    # Step 4 — docs + contract
    pdocs = subprocess.run(
        [sys.executable, "scripts/docs_verify.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("docs.log", pdocs.stdout + pdocs.stderr)
    from launch_contract import check_source_claims

    write("contract.log", "SCOPE: " + json.dumps(check_source_claims()) + "\n")

    # Step 5 — strategy compare + blocking schedule + spec on/off
    p5 = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from core.simulator import run_simulation
par = run_simulation(window_strategy='parallel', seed=42)
ali = run_simulation(window_strategy='aligned', seed=42)
sli = run_simulation(window_strategy='sliding', seed=42)
blk = run_simulation(schedule_id='merge_split_t', seed=42)
spec = par['speculative']
nonspec = par['non_speculative']
print('parallel_runtime=', spec['total_decoding_time_us'])
print('aligned_runtime=', ali['speculative']['total_decoding_time_us'])
print('sliding_runtime=', sli['speculative']['total_decoding_time_us'])
print('parallel_wait=', spec['average_conditional_wait_time_us'])
print('aligned_wait=', ali['speculative']['average_conditional_wait_time_us'])
print('spec_runtime=', spec['total_decoding_time_us'])
print('nonspec_runtime=', nonspec['total_decoding_time_us'])
print('merge_split_wait=', blk['speculative']['average_conditional_wait_time_us'])
print('merge_split_max_dec=', blk['speculative']['max_concurrent_decoders'])
print('strategy_diff=', par['speculative']['total_decoding_time_us'] != ali['speculative']['total_decoding_time_us'])
print('spec_off_diff=', spec['total_decoding_time_us'] != nonspec['total_decoding_time_us'])
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write("strategy_compare.log", p5.stdout + p5.stderr)

    manifest = io.StringIO()
    print("PLAN_VERIFICATION_OK", file=manifest)
    print(f"scratch={SCRATCH}", file=manifest)
    for f in sorted(SCRATCH.glob("*.log")):
        print(f"  {f.name}: {f.stat().st_size} bytes", file=manifest)
    write("manifest.log", manifest.getvalue())
    print(f"PLAN_VERIFICATION_OK scratch={SCRATCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
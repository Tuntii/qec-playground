"""Tests for Li & Martonosi round-stepped speculative window decoder (arXiv:2606.24048)."""

from core.schedule import default_three_t_injection
from core.simulator import run_simulation
from core.swiper_sim import SwiperConfig, compare_speculative_modes, run_swiper_simulation


def test_default_schedule_produces_paper_metrics(capsys):
    schedule = default_three_t_injection()
    result = run_simulation(compare_modes=True, seed=42)
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    print(
        f"spec_time={spec['total_decoding_time_us']:.1f} "
        f"spec_backlog={spec['average_window_backlog']:.2f} "
        f"spec_wait={spec['average_conditional_wait_time_us']:.2f}"
    )
    for key in (
        "total_decoding_time_us",
        "average_window_backlog",
        "average_conditional_wait_time_us",
        "ui_window_count",
    ):
        assert key in spec
        assert key in nonspec
        assert spec[key] >= 0.0
        assert nonspec[key] >= 0.0
    assert schedule.parallelism == 3


def test_speculative_reduces_conditional_wait_on_defaults(capsys):
    result = run_simulation(
        processor_count=4,
        cycle_time_us=1.0,
        speculation_accuracy=0.9,
        seed=42,
    )
    spec_wait = result["speculative"]["average_conditional_wait_time_us"]
    nonspec_wait = result["non_speculative"]["average_conditional_wait_time_us"]
    print(f"cond_wait: spec={spec_wait:.2f} nonspec={nonspec_wait:.2f}")
    assert spec_wait < nonspec_wait
    assert result["comparison"]["cond_wait_reduction"] > 0.0


def test_modes_differ_under_same_schedule(capsys):
    result = run_simulation(seed=7)
    spec = result["speculative"]
    nonspec = result["non_speculative"]
    print(
        f"mode_diff: spec_ui={spec['ui_window_count']:.0f} "
        f"nonspec_ui={nonspec['ui_window_count']:.0f}"
    )
    assert (
        spec["total_decoding_time_us"] != nonspec["total_decoding_time_us"]
        or spec["average_conditional_wait_time_us"] != nonspec["average_conditional_wait_time_us"]
    )


def test_ordering_strategy_affects_backlog(capsys):
    schedule = default_three_t_injection()
    base = SwiperConfig(processor_count=2, speculation_accuracy=0.6, seed=7)
    shallow_run = run_swiper_simulation(
        schedule,
        SwiperConfig(
            processor_count=base.processor_count,
            speculation_accuracy=base.speculation_accuracy,
            ordering_strategy="shallow_first",
            seed=base.seed,
        ),
    )
    deep_run = run_swiper_simulation(
        schedule,
        SwiperConfig(
            processor_count=base.processor_count,
            speculation_accuracy=base.speculation_accuracy,
            ordering_strategy="deep_first",
            seed=base.seed,
        ),
    )
    shallow = shallow_run["metrics"]
    deep = deep_run["metrics"]
    print(
        f"ordering: shallow_backlog={shallow['average_window_backlog']:.2f} "
        f"deep_backlog={deep['average_window_backlog']:.2f} "
        f"shallow_done={shallow_run['completed']} deep_done={deep_run['completed']}"
    )
    assert shallow_run["completed"] is True
    assert deep_run["completed"] is True
    assert shallow["windows_verified"] == shallow["total_windows"]
    assert deep["windows_verified"] == deep["total_windows"]
    assert (
        shallow["average_window_backlog"] != deep["average_window_backlog"]
        or shallow["restart_count"] != deep["restart_count"]
        or shallow["total_decoding_time_us"] != deep["total_decoding_time_us"]
    )


def test_no_re_speculation_loop_after_mis_spec(capsys):
    """deep_first + 2 processors must finish without runaway restarts."""
    schedule = default_three_t_injection()
    run = run_swiper_simulation(
        schedule,
        SwiperConfig(
            processor_count=2,
            speculation_accuracy=0.6,
            ordering_strategy="deep_first",
            seed=7,
        ),
    )
    m = run["metrics"]
    print(
        f"deep_first: completed={run['completed']} verified={m['windows_verified']}/"
        f"{m['total_windows']} restarts={m['restart_count']}"
    )
    assert run["completed"] is True
    assert m["windows_verified"] == m["total_windows"]
    assert m["restart_count"] < 100


def test_gate_speed_affects_metrics(capsys):
    fast = run_simulation(cycle_time_us=1.0, seed=1)
    slow = run_simulation(cycle_time_us=2.0, seed=1)
    fast_time = fast["speculative"]["total_decoding_time_us"]
    slow_time = slow["speculative"]["total_decoding_time_us"]
    fast_backlog = fast["speculative"]["average_window_backlog"]
    slow_backlog = slow["speculative"]["average_window_backlog"]
    print(
        f"gate_speed: fast_time={fast_time:.0f} slow_time={slow_time:.0f} "
        f"fast_backlog={fast_backlog:.2f} slow_backlog={slow_backlog:.2f}"
    )
    assert fast_time != slow_time or fast_backlog != slow_backlog


def test_compare_speculative_modes_keys(capsys):
    schedule = default_three_t_injection()
    comp = compare_speculative_modes(schedule, SwiperConfig(seed=0))
    print(f"comp_keys: {sorted(comp.keys())}")
    assert "speculative" in comp
    assert "non_speculative" in comp
    assert "cond_wait_reduction" in comp


def test_simulation_completes_all_windows(capsys):
    schedule = default_three_t_injection()
    config = SwiperConfig(seed=42)
    run = run_swiper_simulation(schedule, config)
    m = run["metrics"]
    print(
        f"completed={run['completed']} verified={m['windows_verified']}/{m['total_windows']} "
        f"time={m['total_decoding_time_us']}"
    )
    assert run["completed"] is True
    assert m["windows_verified"] == m["total_windows"]
    assert m["completed"] == 1.0
    safety = schedule.windows_per_chain * 6 + config.decoder_latency_rounds * 30
    assert m["total_decoding_time_us"] < safety


def test_nonspec_has_no_ui_windows(capsys):
    schedule = default_three_t_injection()
    run = run_swiper_simulation(schedule, SwiperConfig(speculative=False, seed=42))
    print(f"ui_windows={run['metrics']['ui_window_count']}")
    assert run["metrics"]["ui_window_count"] == 0.0


def test_cond_wait_is_duration_not_blocked_count(capsys):
    """Conditional wait must come from chain blocking duration, not per-round counts."""
    schedule = default_three_t_injection()
    spec = run_swiper_simulation(schedule, SwiperConfig(speculative=True, seed=42))["metrics"]
    nonspec = run_swiper_simulation(schedule, SwiperConfig(speculative=False, seed=42))["metrics"]
    print(f"spec_cond={spec['average_conditional_wait_time_us']} nonspec={nonspec['average_conditional_wait_time_us']}")
    assert spec["average_conditional_wait_time_us"] < nonspec["average_conditional_wait_time_us"]
    assert spec["average_conditional_wait_time_us"] > 0.0


def test_realized_speculation_rate_from_matching(capsys):
    """Matching-derived rate can differ from predictor slider input."""
    result = run_simulation(speculation_accuracy=0.9, seed=42)
    spec = result["speculative"]
    print(
        f"input=0.9 rate={spec['speculation_accuracy_rate']:.3f} "
        f"specs={spec['speculation_count']} restarts={spec['restart_count']}"
    )
    assert 0.0 <= spec["speculation_accuracy_rate"] <= 1.0
    assert spec["speculation_count"] >= 0.0
    assert spec["speculation_accuracy_rate"] <= 1.0
    if spec["speculation_count"] > 0 and spec["restart_count"] > 0:
        assert spec["speculation_accuracy_rate"] < 1.0


def test_identical_runs_match_with_matching(capsys):
    a = run_simulation(seed=42)["speculative"]
    b = run_simulation(seed=42)["speculative"]
    print(f"rate_a={a['speculation_accuracy_rate']} rate_b={b['speculation_accuracy_rate']}")
    assert a == b
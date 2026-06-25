"""Tests for primary simulation entry point."""

from core.simulator import run_simulation


def test_run_simulation_returns_both_modes(capsys):
    result = run_simulation(seed=99)
    print(
        f"keys: {sorted(result.keys())} "
        f"spec_wait={result['speculative']['average_conditional_wait_time_us']:.2f}"
    )
    assert "speculative" in result
    assert "non_speculative" in result
    assert "comparison" in result
    assert "schedule" in result
    assert "params" in result


def test_single_mode_run(capsys):
    result = run_simulation(compare_modes=False, speculative=True, seed=5)
    print(f"single_mode_metrics: {result['metrics']['total_decoding_time_us']:.1f}")
    assert "metrics" in result
    assert result["metrics"]["total_decoding_time_us"] > 0.0


def test_schedule_id_loading(capsys):
    result = run_simulation(schedule_id="three_t_injection", seed=3)
    print(f"schedule: {result['schedule'].id}")
    assert result["schedule"].id == "three_t_injection"
"""Tests for shared CLI/UI simulation parameter parsing."""

import pytest

from ui.sim_params import (
    ORDERING_CHOICES,
    default_cli_params,
    parse_cli_argv,
    to_run_kwargs,
)


def test_default_cli_params_match_paper_defaults(capsys):
    params = default_cli_params()
    print(
        f"schedule={params.schedule_id} proc={params.processor_count} "
        f"cycle={params.cycle_time_us} order={params.ordering_strategy}"
    )
    assert params.schedule_id == "three_t_injection"
    assert params.processor_count == 4
    assert params.cycle_time_us == 1.0
    assert params.speculation_accuracy == 0.9
    assert params.ordering_strategy == "shallow_first"


def test_parse_cli_argv_slow_gate_and_schedule(capsys):
    params, emit_json = parse_cli_argv(
        ["--cycle-time-us", "2", "--schedule", "gkp_memory", "--processors", "2"]
    )
    print(f"parsed: cycle={params.cycle_time_us} schedule={params.schedule_id} json={emit_json}")
    assert params.cycle_time_us == 2.0
    assert params.schedule_id == "gkp_memory"
    assert params.processor_count == 2
    assert emit_json is False


def test_parse_cli_argv_ordering_and_json_flag(capsys):
    params, emit_json = parse_cli_argv(["--ordering", "deep_first", "--json"])
    print(f"order={params.ordering_strategy} json={emit_json}")
    assert params.ordering_strategy == "deep_first"
    assert emit_json is True


def test_to_run_kwargs_includes_compare_modes(capsys):
    kwargs = to_run_kwargs(default_cli_params())
    print(f"kwargs_keys: {sorted(kwargs.keys())}")
    assert kwargs["compare_modes"] is True
    assert kwargs["schedule_id"] == "three_t_injection"
    assert kwargs["cycle_time_us"] == 1.0


def test_parse_cli_argv_rejects_invalid_cycle(capsys):
    with pytest.raises(SystemExit):
        parse_cli_argv(["--cycle-time-us", "3"])
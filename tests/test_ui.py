"""Tests for MVP UI helper modules."""

from core.simulator import run_simulation
from ui.bootstrap import (
    init_schedule_select_from_query,
    schedule_name_from_query,
    take_query_restore,
)
from ui.export import (
    build_share_url,
    dataframe_to_csv,
    decode_config_payload,
    encode_config_payload,
    figure_to_png,
    results_to_dataframe,
)
from ui.schedule_loader import list_templates, load_template_by_id
from ui.sim_params import SimulationParams, params_from_query
from ui.visualizations import build_all_charts


def test_list_templates_returns_schedules(capsys):
    templates = list_templates()
    print(f"template_count: {len(templates)} names={[t.name for t in templates]}")
    assert len(templates) >= 5
    assert all(t.schedule.parallelism >= 1 for t in templates)


def test_load_template_by_id(capsys):
    template = load_template_by_id("three_t_injection")
    print(f"parallelism: {template.schedule.parallelism}")
    assert template.schedule.parallelism == 3
    assert template.schedule.windows_per_chain == 10


def test_build_all_charts_from_real_simulation(capsys):
    result = run_simulation(seed=123)
    charts = build_all_charts(result)
    print(f"charts_count: {len(charts)}")
    assert len(charts) == 4
    assert "decode_time" in charts
    assert result["speculative"]["total_decoding_time_us"] > 0.0


def test_export_csv_and_share_url(capsys):
    result = run_simulation(seed=7)
    params = SimulationParams(
        processor_count=4,
        cycle_time_us=1.0,
        speculation_accuracy=0.9,
        decoder_latency_rounds=2,
        ordering_strategy="shallow_first",
        window_strategy="parallel",
        seed=7,
        schedule_id="three_t_injection",
        schedule_name="Three parallel T-gate injections",
    )
    df = results_to_dataframe(result, params)
    csv_bytes = dataframe_to_csv(df)
    url = build_share_url(params)
    token = encode_config_payload(params)
    restored = decode_config_payload(token)
    print(f"csv_len: {len(csv_bytes)} share_url_ok: {url.startswith('http')} token_len: {len(token)}")
    assert len(csv_bytes) > 50
    assert url.startswith("http")
    assert len(token) > 10
    assert restored["schedule"] == "three_t_injection"


def test_params_from_query_overrides(capsys):
    template = load_template_by_id("gkp_memory")
    params = params_from_query(
        {
            "proc": "2",
            "cycle": "2.0",
            "specacc": "0.75",
            "latency": "3",
            "order": "deep_first",
            "seed": "99",
            "schedule": "surface_gkp_d5",
        },
        template,
    )
    print(
        f"query_params: proc={params.processor_count} cycle={params.cycle_time_us} "
        f"order={params.ordering_strategy} schedule={params.schedule_id}"
    )
    assert params.processor_count == 2
    assert params.cycle_time_us == 2.0
    assert params.speculation_accuracy == 0.75
    assert params.seed == 99
    assert params.ordering_strategy == "deep_first"
    assert params.schedule_id == "surface_gkp_d5"


def test_figure_to_png_exports_bytes(capsys):
    result = run_simulation(seed=5)
    charts = build_all_charts(result)
    png_decode = figure_to_png(charts["decode_time"])
    png_wait = figure_to_png(charts["cond_wait"])
    print(
        f"png_decode_len: {len(png_decode)} png_wait_len: {len(png_wait)} "
        f"png_decode_magic: {png_decode[:8]}"
    )
    assert len(png_decode) > 1000
    assert len(png_wait) > 1000
    assert png_decode[:8] == b"\x89PNG\r\n\x1a\n"


def test_schedule_name_from_query(capsys):
    templates = list_templates()
    name = schedule_name_from_query(templates, {"schedule": "surface_gkp_d5"})
    print(f"query_schedule_name: {name}")
    assert name == "Single-chain distance-5 workload"


def test_take_query_restore_once(capsys):
    session: dict = {}
    q = {"schedule": "gkp_memory", "proc": "4"}
    first = take_query_restore(session, q)
    second = take_query_restore(session, q)
    print(f"query_restore_first: {first is not None} second: {second is None}")
    assert first == q
    assert second is None


def test_init_schedule_select_from_query(capsys):
    templates = list_templates()
    session: dict = {}
    init_schedule_select_from_query(
        session,
        templates,
        {"schedule": "surface_gkp_d5"},
    )
    print(f"schedule_select_seed: {session.get('schedule_select')}")
    assert session["schedule_select"] == "Single-chain distance-5 workload"
    init_schedule_select_from_query(session, templates, {"schedule": "gkp_memory"})
    assert session["schedule_select"] == "Single-chain distance-5 workload"
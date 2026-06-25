"""QEC-Playground — Streamlit UI and CLI entry (`python app.py`)."""

from __future__ import annotations

import os
import sys
from typing import Any


def _has_streamlit_context() -> bool:
    if os.environ.get("STREAMLIT_SERVER_PORT"):
        return True
    if "streamlit" not in sys.modules:
        return False
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def _execute_simulation(params: Any) -> dict[str, Any]:
    from core.simulator import run_simulation
    from ui.sim_params import to_run_kwargs

    return run_simulation(**to_run_kwargs(params))


def _display_results(result: dict[str, Any], params: Any) -> None:
    import streamlit as st

    from ui.export import (
        build_share_url,
        dataframe_to_csv,
        default_share_base_url,
        encode_config_payload,
        figure_to_png,
        png_export_available,
        results_to_dataframe,
    )
    from ui.result_summary import result_metric_values
    from ui.visualizations import build_all_charts

    metrics = result_metric_values(result)
    comp = result["comparison"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spec decode time (µs)", metrics["Spec total decode time (µs)"])
    col2.metric("Non-spec decode time (µs)", metrics["Non-spec total decode time (µs)"])
    col3.metric("Spec avg backlog", metrics["Spec avg backlog"])
    col4.metric("Cond wait reduction", f"{comp['cond_wait_reduction']:.1%}")

    charts = build_all_charts(result)

    st.subheader("Decoder comparison")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(charts["decode_time"], use_container_width=True)
        st.plotly_chart(charts["cond_wait"], use_container_width=True)
    with right:
        st.plotly_chart(charts["backlog"], use_container_width=True)
        st.plotly_chart(charts["ui_windows"], use_container_width=True)

    st.subheader("Export")
    df = results_to_dataframe(result, params)
    csv_bytes = dataframe_to_csv(df)
    share_url = build_share_url(params, base_url=default_share_base_url())
    share_token = encode_config_payload(params)

    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="qec_playground_results.csv",
        mime="text/csv",
    )

    if png_export_available():
        png_decode = figure_to_png(charts["decode_time"])
        st.download_button(
            "Download decode-time PNG",
            data=png_decode,
            file_name="decode_time.png",
            mime="image/png",
        )
        png_wait = figure_to_png(charts["cond_wait"])
        st.download_button(
            "Download conditional-wait PNG",
            data=png_wait,
            file_name="conditional_wait.png",
            mime="image/png",
        )
    else:
        st.caption(
            "PNG chart export is unavailable here (Kaleido/Chrome not installed). "
            "CSV export and on-screen charts still work."
        )

    st.text_input("Share this config (URL)", value=share_url)
    st.text_input("Share token (base64)", value=share_token)


def run_streamlit() -> None:
    import streamlit as st

    from ui.bootstrap import (
        init_schedule_select_from_query,
        schedule_name_from_query,
        take_query_restore,
    )
    from ui.schedule_loader import list_templates
    from ui.sliders import render_sidebar

    st.set_page_config(page_title="QEC-Playground", page_icon="⚛️", layout="wide")
    st.title("QEC-Playground")
    st.caption(
        "First open-source lightweight playground — Jocelyn Li and Margaret Martonosi, "
        "An Analysis of Speculative Window Decoders for Quantum Error Correction "
        "(arXiv:2606.24048). Syndrome graph + matching decoder confirmation; "
        "round-stepped scheduling — not the full ISCA 2025 SWIPER-SIM or paper figure copy."
    )

    templates = list_templates()
    template_by_name = {t.name: t for t in templates}
    template_names = list(template_by_name.keys())
    query_restore = take_query_restore(st.session_state, dict(st.query_params))
    init_schedule_select_from_query(
        st.session_state,
        templates,
        query_restore,
        widget_key="schedule_select",
    )

    st.subheader("Lattice surgery schedule")
    col_sched, col_meta = st.columns([2, 1])
    with col_sched:
        selected_name = st.selectbox(
            "Built-in schedule template",
            options=template_names,
            key="schedule_select",
        )
        template = template_by_name[selected_name]

    with col_meta:
        sched = template.schedule
        st.markdown(f"**Parallel chains:** {sched.parallelism}")
        st.markdown(f"**Windows per chain:** {sched.windows_per_chain}")
        st.markdown(f"**Blocking window:** {sched.blocking_window_index}")
        st.markdown(f"**Source:** {sched.source}")

    params = render_sidebar(template, query=query_restore)

    if st.button("Run Simulation", type="primary"):
        with st.spinner("Running Li & Martonosi round-stepped speculative window decoder…"):
            st.session_state["result"] = _execute_simulation(params)
            st.session_state["params"] = params

    if "result" in st.session_state:
        _display_results(st.session_state["result"], st.session_state["params"])


def _cli_entry() -> int:
    import json

    from core.simulator import run_simulation
    from ui.result_summary import format_cli_report
    from ui.sim_params import parse_cli_argv, to_run_kwargs

    params, emit_json = parse_cli_argv(sys.argv[1:])
    result = run_simulation(**to_run_kwargs(params))
    print(format_cli_report(result))

    if emit_json:
        print()
        print(json.dumps(result, indent=2, default=str))

    return 0


if os.environ.get("STREAMLIT_SERVER_PORT") or _has_streamlit_context():
    run_streamlit()
elif __name__ == "__main__":
    raise SystemExit(_cli_entry())
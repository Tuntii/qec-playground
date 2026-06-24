"""QEC-Playground — Streamlit MVP + CLI entry point."""

from __future__ import annotations

import json
import sys
from typing import Any

from core.simulator import run_simulation


def _is_streamlit_runtime() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def run_cli() -> int:
    """Headless CLI simulation (python app.py)."""
    result = run_simulation(
        squeezing_db=10.0,
        noise_p=0.02,
        skip_threshold=0.7,
        shots=1000,
        window_size=4,
        seed=42,
    )

    gkp = result["gkp"]
    dec = result["decoder"]

    print("QEC-Playground Simulation Results")
    print("=" * 40)
    print(f"GKP squeezing:        {gkp['squeezing_db']:.1f} dB")
    print(f"Noise level:          {gkp['noise_p']:.4f}")
    print(f"Logical error rate:   {gkp['logical_error_rate']:.4f}")
    print(f"Physical error rate:  {gkp['physical_error_rate']:.4f}")
    print(f"Mean fidelity:        {gkp['mean_fidelity']:.4f}")
    print()
    print("Speculative Decoder")
    print(f"  Success probability: {dec['speculative']['success_probability']:.4f}")
    print(f"  Mean wait cycles:    {dec['speculative']['mean_wait_cycles']:.2f}")
    print(f"  Speculation rate:    {dec['speculative']['speculation_rate']:.4f}")
    print()
    print("Naive Decoder")
    print(f"  Success probability: {dec['naive']['success_probability']:.4f}")
    print(f"  Mean wait cycles:    {dec['naive']['mean_wait_cycles']:.2f}")
    print()
    print(f"Wait reduction:       {dec['wait_reduction']:.2%}")
    print(f"Success delta:        {dec['success_delta']:+.4f}")

    if "--json" in sys.argv:
        print()
        print(json.dumps(result, indent=2))

    return 0


def _execute_simulation(params: Any) -> dict[str, Any]:
    return run_simulation(
        squeezing_db=params.squeezing_db,
        noise_p=params.noise_p,
        skip_threshold=params.skip_threshold,
        shots=params.shots,
        window_size=params.window_size,
        surface_distance=params.surface_distance,
        seed=params.seed,
        include_syndromes=True,
    )


def _display_results(result: dict[str, Any], params: Any, *, compare_focus: bool) -> None:
    import streamlit as st

    from ui.export import (
        build_share_url,
        dataframe_to_csv,
        encode_config_payload,
        figure_to_png,
        results_to_dataframe,
    )
    from ui.visualizations import build_all_charts

    gkp = result["gkp"]
    dec = result["decoder"]
    syndromes = result.get("syndromes", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Logical error rate", f"{gkp['logical_error_rate']:.4f}")
    col2.metric("Physical error rate", f"{gkp['physical_error_rate']:.4f}")
    col3.metric("Mean fidelity", f"{gkp['mean_fidelity']:.4f}")
    col4.metric("Wait reduction", f"{dec['wait_reduction']:.1%}")

    charts = build_all_charts(result, syndromes)

    if compare_focus:
        st.subheader("Decoder comparison")
        st.plotly_chart(charts["success_probability"], use_container_width=True)
        st.plotly_chart(charts["decoder_comparison"], use_container_width=True)
    else:
        st.subheader("Simulation charts")
        left, right = st.columns(2)
        with left:
            st.plotly_chart(charts["error_rate"], use_container_width=True)
        with right:
            st.plotly_chart(charts["syndrome_heatmap"], use_container_width=True)
        st.plotly_chart(charts["success_probability"], use_container_width=True)
        st.plotly_chart(charts["decoder_comparison"], use_container_width=True)

    st.subheader("Export")
    df = results_to_dataframe(result, params)
    csv_bytes = dataframe_to_csv(df)
    share_url = build_share_url(params)  # honors QEC_DEMO_BASE_URL when set
    share_token = encode_config_payload(params)

    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="qec_playground_results.csv",
        mime="text/csv",
    )

    png_error = figure_to_png(charts["error_rate"])
    st.download_button(
        "Download error-rate PNG",
        data=png_error,
        file_name="error_rate.png",
        mime="image/png",
    )
    png_success = figure_to_png(charts["success_probability"])
    st.download_button(
        "Download success-probability PNG",
        data=png_success,
        file_name="success_probability.png",
        mime="image/png",
    )

    st.text_input("Share this config (URL)", value=share_url)
    st.text_input("Share token (base64)", value=share_token)


def run_streamlit() -> None:
    import streamlit as st

    from ui.bootstrap import (
        clear_qasm_state,
        init_circuit_select_from_query,
        resolve_active_template,
        take_query_restore,
    )
    from ui.circuit_loader import list_templates
    from ui.sliders import render_sidebar

    st.set_page_config(page_title="QEC-Playground", page_icon="⚛️", layout="wide")
    st.title("QEC-Playground")
    st.caption(
        "Surface-GKP codes — when to skip? Live speculative window decoder simulation."
    )

    templates = list_templates()
    template_by_name = {t.name: t for t in templates}
    template_names = list(template_by_name.keys())
    query_restore = take_query_restore(st.session_state, dict(st.query_params))
    init_circuit_select_from_query(
        st.session_state,
        templates,
        query_restore,
        widget_key="circuit_select",
    )

    st.subheader("Circuit")
    col_circuit, col_meta = st.columns([2, 1])
    with col_circuit:
        def _on_circuit_change() -> None:
            clear_qasm_state(st.session_state)

        selected_name = st.selectbox(
            "Built-in GKP-surface template",
            options=template_names,
            key="circuit_select",
            on_change=_on_circuit_change,
        )
        use_qasm = st.checkbox(
            "Override with QASM import",
            key="use_qasm_import",
        )
        qasm_text = st.text_area(
            "QASM import (optional)",
            height=100,
            placeholder="Paste OpenQASM 2.0 to override template metadata…",
            key="qasm_text",
            disabled=not use_qasm,
        )
        template, qasm_error = resolve_active_template(
            template_by_name,
            selected_name,
            use_qasm=use_qasm,
            qasm_text=qasm_text,
        )
        if use_qasm and qasm_text.strip() and qasm_error is None:
            st.success("QASM parsed — using imported circuit metadata.")
        elif qasm_error:
            st.error(qasm_error)

    with col_meta:
        st.markdown(f"**Distance:** {template.surface_distance}")
        st.markdown(f"**Window size:** {template.window_size}")
        st.markdown(f"**Source:** {template.source}")

    params = render_sidebar(template, query=query_restore)

    btn_run, btn_compare = st.columns(2)
    run_clicked = btn_run.button("Run Simulation", type="primary")
    compare_clicked = btn_compare.button("Compare with naive decoder")

    if run_clicked or compare_clicked:
        with st.spinner("Running QuTiP GKP + decoder simulation…"):
            st.session_state["result"] = _execute_simulation(params)
            st.session_state["params"] = params
            st.session_state["compare_focus"] = compare_clicked and not run_clicked

    if "result" in st.session_state:
        _display_results(
            st.session_state["result"],
            st.session_state["params"],
            compare_focus=st.session_state.get("compare_focus", False),
        )


if _is_streamlit_runtime():
    run_streamlit()
elif __name__ == "__main__":
    raise SystemExit(run_cli())
"""Headless Streamlit AppTest integration for the shipped app.py."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_apptest_loads_without_exception(capsys):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    print(f"exception_count: {len(at.exception)}")
    print(f"title: {at.title[0].value if at.title else 'none'}")
    print(f"buttons: {[b.label for b in at.button]}")
    assert len(at.exception) == 0
    assert at.title[0].value == "QEC-Playground"
    labels = [b.label for b in at.button]
    assert "Run Simulation" in labels
    assert len(at.selectbox) >= 1


def test_apptest_query_restores_schedule_select(capsys):
    at = AppTest.from_file(str(APP_PATH))
    at.query_params["schedule"] = "surface_gkp_d5"
    at.run(timeout=30)
    print(f"query_exception_count: {len(at.exception)}")
    print(f"query_select_value: {at.selectbox[0].value}")
    assert len(at.exception) == 0
    assert at.selectbox[0].value == "Single-chain distance-5 workload"
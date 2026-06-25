# QEC-Playground

**First open-source implementation** of an interactive lightweight round-stepped playground for the speculative window decoder analysis framework in *An Analysis of Speculative Window Decoders for Quantum Error Correction* — Jocelyn Li and Margaret Martonosi ([arXiv:2606.24048](https://arxiv.org/abs/2606.24048)).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-49%20passed-brightgreen.svg)](#tests)

![QEC-Playground dashboard — sliders, Run Simulation, and charts](assets/hero.png)

> **Scope:** This repo implements the paper's analysis mechanics (processor-limited speculative window scheduling, lattice-surgery workloads, sensitivity axes) as a pure Python round-stepped model. Distinct from the full SWIPER-SIM in [jviszlai/swiper](https://github.com/jviszlai/swiper) (ISCA 2025 SWIPER) — Li & Martonosi do not publish their modified SWIPER-SIM source; this project is the first open-source tool aimed specifically at their workshop analysis.

**What you get:** compare speculative vs non-speculative parallel window decoding on representative schedules (e.g. three parallel T-gate injections with blocking Conditional-S instructions). Tune processors, gate speed (1µs / 2µs), speculation accuracy, decoder latency, and ordering strategies — see decoding time, backlog, conditional wait, and UI window count in microseconds.

**What this is not:** a full SWIPER-SIM reproduction, physical syndrome-graph decoder, or exact replication of paper figures.

## Quick start

```bash
git clone https://github.com/Tuntii/qec-playground.git
cd qec-playground
pip install -r requirements.txt
streamlit run app.py
```

Headless CLI (same simulator, terminal output):

```bash
python app.py
python app.py --cycle-time-us 2 --processors 4 --schedule three_t_injection
```

## Interactive demo

**Live demo:** `YOUR_DEMO_URL` *(replace after Hugging Face Spaces or Streamlit Cloud deploy)*

Example after deploy:

```text
https://huggingface.co/spaces/YOUR_USERNAME/qec-playground
```

Share links in the app use `build_share_url(params, base_url=...)` — set the deployed base via env or pass explicitly:

```bash
# Windows
set QEC_DEMO_BASE_URL=YOUR_DEMO_URL
streamlit run app.py

# macOS / Linux
export QEC_DEMO_BASE_URL=YOUR_DEMO_URL
streamlit run app.py
```

### Deploy to Hugging Face Spaces

1. New Space → SDK: **Streamlit**
2. Connect this repo (`app.py` + `requirements.txt` at repo root)
3. Copy the Space URL into `YOUR_DEMO_URL` above and `QEC_DEMO_BASE_URL`

### Deploy to Streamlit Community Cloud

1. [share.streamlit.io](https://share.streamlit.io) → select repo, main file `app.py`
2. Use the deployed URL as `YOUR_DEMO_URL` / `QEC_DEMO_BASE_URL`

## Features

- **First open-source** interactive playground for Li & Martonosi (arXiv:2606.24048) speculative window decoder sensitivity analysis
- Lattice surgery schedule templates (three parallel T-injection default + stress workloads)
- Paper parameters: decoder processors, gate speed (1µs / 2µs), speculation accuracy, decoder latency, ordering strategy
- Speculative vs non-speculative comparison (Plotly): total decoding time, window backlog, conditional wait, UI windows
- Export: CSV, PNG charts, shareable config URL / token

## Citations

**Primary paper (this playground implements its analysis framework):**

```bibtex
@article{li2026speculative,
  title={An Analysis of Speculative Window Decoders for Quantum Error Correction},
  author={Li, Jocelyn and Martonosi, Margaret},
  journal={arXiv preprint arXiv:2606.24048},
  year={2026}
}
```

**Underlying algorithm (SWIPER, ISCA 2025):** [github.com/jviszlai/swiper](https://github.com/jviszlai/swiper)

## Project layout

```
app.py              # Streamlit UI and `python app.py` CLI
core/               # Round-stepped SWIPER-SIM-style speculative window decoder
  schedule.py       # Lattice-surgery schedule templates
  swiper_sim.py     # Round-stepped window state machine + metrics
  simulator.py      # run_simulation() entry point
ui/                 # Sliders, charts, export, schedule loader
examples/           # JSON lattice-surgery schedule templates
scripts/            # Hero capture, gating verification, docs checks
tests/              # pytest suite (49 tests)
LICENSE             # MIT + academic citation note
```

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
```

Regenerate `assets/hero.png` from a live Streamlit screenshot (optional; needs dev deps + Chromium):

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/generate_hero_asset.py
```

Launch verification (UTF-8 evidence capture — recommended):

```bash
python scripts/verify_gating.py
```

Or via PowerShell wrapper:

```powershell
$env:QEC_GATING_SCRATCH = ".gating-evidence"
powershell -File scripts/run_gating_verification.ps1
```

## Star

Star'ını ver ki quantum dünyasında ilk senin tool'un ünlensin 🔥

## License

MIT — see [LICENSE](LICENSE). Research prototype — not production fault-tolerance tooling.
# QEC-Playground

**First open-source implementation** of an interactive lightweight round-stepped playground for the speculative window decoder analysis framework in *An Analysis of Speculative Window Decoders for Quantum Error Correction* — Jocelyn Li and Margaret Martonosi ([arXiv:2606.24048](https://arxiv.org/abs/2606.24048)).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-58%20passed-brightgreen.svg)](#tests)

![QEC-Playground dashboard — sliders, Run Simulation, and charts](assets/hero.png)

> **Scope:** Round-stepped speculative window scheduling with **real syndrome graph construction** and a **matching decoder** (MWPM on 1D check paths) to confirm or reject speculation. **Not the full** SWIPER-SIM in [jviszlai/swiper](https://github.com/jviszlai/swiper) (ISCA 2025 SWIPER) — not an exact copy of Li & Martonosi paper figures or numeric results.

**What you get:** compare speculative vs non-speculative parallel window decoding on representative schedules (e.g. three parallel T-gate injections with blocking Conditional-S instructions). The **speculation accuracy slider** gates attempt probability; the **realized speculation rate** comes from matching outcomes and can differ. Tune processors, gate speed (1µs / 2µs), decoder latency, and ordering — see decoding time, backlog, conditional wait, UI windows, and restart stats.

**What this is not:** a full SWIPER-SIM reproduction, large-scale surface-code compilation, or exact replication of paper figures/tables.

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

**Live demo:** [huggingface.co/spaces/Tunti35/qec-playground](https://huggingface.co/spaces/Tunti35/qec-playground)

Share links in the app use `build_share_url(params, base_url=...)` — set the deployed base via env or pass explicitly:

```bash
# Windows
set QEC_DEMO_BASE_URL=https://huggingface.co/spaces/Tunti35/qec-playground
streamlit run app.py

# macOS / Linux
export QEC_DEMO_BASE_URL=https://huggingface.co/spaces/Tunti35/qec-playground
streamlit run app.py
```

### Redeploy to Hugging Face Spaces

```bash
set HF_TOKEN=your_hf_token
python scripts/deploy_hf_space.py
```

### Deploy to Streamlit Community Cloud (alternative)

1. [share.streamlit.io](https://share.streamlit.io) → select repo, main file `app.py`
2. Set `QEC_DEMO_BASE_URL` to your deployed Streamlit URL

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
core/               # Syndrome graph + matching decoder + round-stepped scheduler
  syndrome_graph.py # Defect syndromes per decode round
  matching_decoder.py # MWPM confirmation of speculation
  schedule.py       # Lattice-surgery schedule templates
  swiper_sim.py     # Window state machine + metrics
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
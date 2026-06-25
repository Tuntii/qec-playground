# QEC-Playground

**First open-source full SWIPER-SIM behavioral model** for the speculative window decoder analysis framework in *An Analysis of Speculative Window Decoders for Quantum Error Correction* — Jocelyn Li and Margaret Martonosi ([arXiv:2606.24048](https://arxiv.org/abs/2606.24048)).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-73%20passed-brightgreen.svg)](#tests)

![QEC-Playground dashboard — sliders, Run Simulation, and charts](assets/hero.png)

> **Scope:** Full SWIPER-SIM behavioral model — **DeviceManager**, **WindowManager**, **DecoderManager**, boundary predictor, matching verification, optimistic restart, blocking Conditional-S delays, and **parallel / aligned / sliding** window strategies. Lightweight Python reimplementation of [jviszlai/swiper](https://github.com/jviszlai/swiper) (ISCA 2025) manager behaviors — not a line-for-line C++ port or exact paper figure reproduction.

**What you get:** compare speculative vs non-speculative parallel window decoding on lattice surgery programs (three parallel T-gate injections, merge/split workloads). **Syndrome graph** construction and **matching decoder** (MWPM) confirm or reject speculation. The **speculation accuracy slider** gates attempt probability; the **realized speculation rate** comes from matching outcomes. Tune processors, gate speed (1µs / 2µs), decoder latency, ordering, and window strategy — see runtime, backlog, conditional wait, max concurrent decoders, UI windows, and restart stats.

**What this is not:** the original C++ SWIPER-SIM release, large-scale surface-code compilation, or exact replication of paper figures/tables.

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

- **First open-source** full SWIPER-SIM behavioral model for Li & Martonosi (arXiv:2606.24048)
- DeviceManager / WindowManager / DecoderManager round-stepped simulation
- Lattice surgery programs: patches, merge/split, blocking Conditional-S (`three_t_injection`, `merge_split_t`)
- Paper parameters: processors, gate speed, speculation accuracy, decoder latency, ordering + window strategy
- Speculative vs non-speculative comparison: runtime, backlog, conditional wait, max/mean decoders, UI windows
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
core/               # Full SWIPER-SIM behavioral model
  device_manager.py # Per-round patches + syndromes + blocking
  window_manager.py # Parallel/aligned/sliding windows
  decoder_manager.py # Predictor + verify + optimistic restart
  syndrome_graph.py # Defect syndromes per decode round
  matching_decoder.py # MWPM confirmation of speculation
  schedule.py       # Lattice surgery programs
  swiper_sim.py     # Manager orchestrator + metrics
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
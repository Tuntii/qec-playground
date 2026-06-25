# QEC-Playground — Project Specification
**Version:** 3.0 (25 June 2026)  
**Owner:** Tunay  
**Goal:** First open-source implementation of an interactive lightweight round-stepped playground for the speculative window decoder analysis framework in *An Analysis of Speculative Window Decoders for Quantum Error Correction* (Jocelyn Li and Margaret Martonosi, arXiv:2606.24048).

## 1. Project definition
**Name:** QEC-Playground  
**Tagline:** First open-source interactive playground for Li & Martonosi speculative window decoder sensitivity analysis.

**Positioning (accurate scope):**
- **This project:** first open-source tool implementing the Li & Martonosi (arXiv:2606.24048) analysis framework with real syndrome graph construction and matching-decoder speculation confirmation, plus Streamlit/CLI.
- **Distinct from the full SWIPER-SIM** in [jviszlai/swiper](https://github.com/jviszlai/swiper) (ISCA 2025 SWIPER); Li & Martonosi used a modified SWIPER-SIM internally and do not publish that source.
- **Model level:** round-stepped scheduling (window states, processor queue, conditional wait) wired to MWPM on 1D syndrome graphs — not a full SWIPER-SIM port or exact paper figure reproduction.

**Why:**  
- Li & Martonosi paper is fresh (submitted 23 Jun 2026) and releases no code for their modified SWIPER-SIM experiments.  
- Researchers need an open playground to explore processor count, gate speed, speculation accuracy, and ordering strategies.  
- CLI + Streamlit drive the same `run_simulation()` entry point for reproducible metrics.

## 2. Target users
- Quantum error correction students and researchers
- Architects studying speculative window decoders and lattice surgery workloads
- Anyone comparing speculative vs non-speculative parallel decoding under paper sensitivity axes

## 3. Features

### MVP (first open-source playground)
- [x] Lattice surgery schedule loading (JSON templates; default three parallel T-gate injections)
- [x] Paper parameter sliders/CLI: processors, gate speed (1µs / 2µs), speculation accuracy, decoder latency, ordering strategy
- [x] Round-stepped speculative window simulator (speculative + non-speculative modes)
- [x] Plotly charts: total decoding time, window backlog, conditional wait, UI window count
- [x] `python app.py` CLI with argparse flags matching paper inputs
- [x] Export: PNG + CSV + shareable config URL
- [x] MIT LICENSE with academic citation note

### Core status (25 June 2026)
- **Core:** `core/schedule.py`, `core/swiper_sim.py`, `core/simulator.py`
- **UI:** `streamlit run app.py` — schedule picker, paper sliders, Plotly charts, export
- **CLI:** `python app.py` — headless text report via `ui/sim_params.py`
- **Legacy:** `core/legacy_gkp.py` — isolated QuTiP GKP module (not primary path)

### Future
- Additional benchmark schedules from the paper
- Program trace / window graph visualization
- Batch parameter sweeps and CSV export

## 4. Tech stack
- **Simulation:** NumPy (round-stepped SWIPER-SIM-style model)
- **UI:** Streamlit + Plotly
- **Deploy:** Streamlit Community Cloud / Hugging Face Spaces
- **Setup:** `pip install -r requirements.txt && streamlit run app.py`

## 5. Folder layout
```
qec-playground/
├── LICENSE
├── app.py
├── core/
│   ├── schedule.py
│   ├── swiper_sim.py
│   ├── simulator.py
│   └── legacy_gkp.py
├── ui/
│   ├── sim_params.py
│   ├── sliders.py
│   ├── visualizations.py
│   └── export.py
├── examples/
└── tests/
```

## 6. Paper metrics (acceptance)
| Metric | Description |
|--------|-------------|
| `total_decoding_time_us` | Rounds × cycle time until all windows verified |
| `average_window_backlog` | Mean count of active (non-verified) windows |
| `average_conditional_wait_time_us` | Mean blocking wait on Conditional-S deps |
| `ui_window_count` | Speculative decode sessions on unverified deps |

Under default fast-gate parameters (4 processors, 1µs, 90% accuracy, shallow_first), speculative mode must complete and report lower average conditional wait than non-speculative.

## 7. References
- Li & Martonosi, *An Analysis of Speculative Window Decoders for Quantum Error Correction*, arXiv:2606.24048 (QCCC-26 workshop)
- Viszlai et al., SWIPER (ISCA 2025) — [github.com/jviszlai/swiper](https://github.com/jviszlai/swiper)
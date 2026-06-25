# QEC-Playground — Project Specification
**Version:** 4.0 (25 June 2026)  
**Owner:** Tunay  
**Goal:** First open-source full SWIPER-SIM behavioral model for the speculative window decoder analysis framework in *An Analysis of Speculative Window Decoders for Quantum Error Correction* (Jocelyn Li and Margaret Martonosi, arXiv:2606.24048).

## 1. Project definition
**Name:** QEC-Playground  
**Tagline:** First open-source interactive full SWIPER-SIM behavioral model for Li & Martonosi speculative window decoder sensitivity analysis.

**Positioning (accurate scope):**
- **This project:** first open-source implementation of the Li & Martonosi (arXiv:2606.24048) analysis framework as a **full SWIPER-SIM behavioral model** — DeviceManager, WindowManager, DecoderManager, boundary predictor, matching verification, optimistic restart, blocking Conditional-S delays, and parallel/aligned/sliding window strategies.
- **Distinct from** the original C++ [jviszlai/swiper](https://github.com/jviszlai/swiper) (ISCA 2025 SWIPER) in implementation size and exact benchmark numbers; this is a lightweight Python reimplementation of core manager behaviors, not a line-for-line port.
- **Model level:** round-stepped lattice surgery programs with real syndrome graph construction and matching decoder (MWPM on 1D check paths).

**Why:**  
- Li & Martonosi paper is fresh (submitted 23 Jun 2026) and releases no code for their modified SWIPER-SIM experiments.  
- Researchers need an open playground to explore processor count, gate speed, speculation accuracy, window strategies, and ordering.  
- CLI + Streamlit drive the same `run_simulation()` entry point for reproducible metrics.

## 2. Target users
- Quantum error correction students and researchers
- Architects studying speculative window decoders and lattice surgery workloads
- Anyone comparing speculative vs non-speculative parallel decoding under paper sensitivity axes

## 3. Features

### Core (full SWIPER-SIM behavioral model)
- [x] Lattice surgery program loading (patches, ops, blocking; JSON templates)
- [x] DeviceManager — per-round active patches and syndrome emission
- [x] WindowManager — parallel, aligned, sliding window strategies
- [x] DecoderManager — boundary predictor, matching verify, optimistic restart
- [x] Paper parameter sliders/CLI: processors, gate speed, speculation accuracy, decoder latency, ordering + window strategy
- [x] Round-stepped speculative window simulator (speculative + non-speculative modes)
- [x] Metrics: runtime, backlog, conditional wait, UI windows, restarts, max/mean concurrent decoders
- [x] Plotly charts + `python app.py` CLI + export

### Core status (25 June 2026)
- **Managers:** `core/device_manager.py`, `core/window_manager.py`, `core/decoder_manager.py`
- **Orchestrator:** `core/swiper_sim.py`, `core/simulator.py`
- **Schedules:** `core/schedule.py`, `examples/` (three_t_injection, merge_split_t)
- **UI:** `streamlit run app.py`
- **CLI:** `python app.py`

### Future
- Additional benchmark schedules from the paper
- Interactive program trace / window graph visualization
- Batch parameter sweeps

## 4. Tech stack
- **Simulation:** NumPy (round-stepped full SWIPER-SIM behavioral model)
- **UI:** Streamlit + Plotly
- **Deploy:** Hugging Face Spaces / Streamlit Community Cloud
- **Setup:** `pip install -r requirements.txt && streamlit run app.py`

## 5. Folder layout
```
qec-playground/
├── app.py
├── core/
│   ├── device_manager.py
│   ├── window_manager.py
│   ├── decoder_manager.py
│   ├── schedule.py
│   ├── syndrome_graph.py
│   ├── matching_decoder.py
│   ├── swiper_sim.py
│   └── simulator.py
├── ui/
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
| `max_concurrent_decoders` | Peak classical decoder occupancy |
| `average_concurrent_decoders` | Mean decoder occupancy per round |

## 7. References
- Li & Martonosi, *An Analysis of Speculative Window Decoders for Quantum Error Correction*, arXiv:2606.24048
- Viszlai et al., SWIPER (ISCA 2025) — [github.com/jviszlai/swiper](https://github.com/jviszlai/swiper)
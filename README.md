# QEC-Playground

**Surface-GKP kodlarında "Ne zaman skip etsem?" sorusunun canlı cevabı.**

![QEC-Playground dashboard — sliders, Run Simulation, and charts](assets/hero.png)

> **24 Haziran 2026** arXiv makalesinin (*Surface-GKP + Speculative Window Decoders*) **ilk açık kaynak implementasyonu**. QuTiP ile GKP simülasyonu, speculative window decoder ve naive baseline karşılaştırması — 2 dakikada parametre denemesi.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Headless CLI (terminal çıktısı, Streamlit import etmez):

```bash
python cli.py
```

## Interactive demo

**Live demo:** `YOUR_DEMO_URL` *(replace after Hugging Face Spaces or Streamlit Cloud deploy)*

Example after deploy:

```text
https://huggingface.co/spaces/YOUR_USERNAME/qec-playground
```

Share links in the app use `build_share_url(params, base_url=...)` — set the deployed base via env or pass explicitly:

```bash
set QEC_DEMO_BASE_URL=YOUR_DEMO_URL
streamlit run app.py
```

### Hugging Face Spaces

1. New Space → SDK: **Streamlit**
2. Connect this repo (`app.py` + `requirements.txt` at repo root)
3. Copy the Space URL into `YOUR_DEMO_URL` above and `QEC_DEMO_BASE_URL`

### Streamlit Community Cloud

1. [share.streamlit.io](https://share.streamlit.io) → select repo, main file `app.py`
2. Use the deployed URL as `YOUR_DEMO_URL` / `QEC_DEMO_BASE_URL`

## Features

- 5 hazır GKP-surface circuit template + OpenQASM metadata import
- Slider'lar: GKP squeezing (dB), skip threshold, noise, shot count
- Speculative vs naive decoder karşılaştırması (Plotly)
- Export: CSV, PNG grafikler, paylaşılabilir config URL / token

## Project layout

```
app.py              # Streamlit UI + CLI entry
core/               # QuTiP GKP + decoder simulation
ui/                 # Sliders, charts, export, circuit loader
examples/           # 5 JSON circuit templates
assets/             # README hero dashboard screenshot
tests/              # pytest suite
```

## Tests

```bash
python -m pytest tests/ -q
```

## Star

Star'ını ver ki quantum dünyasında ilk senin tool'un ünlensin 🔥

## License

MIT (see repository defaults). Research prototype — not production fault-tolerance tooling.
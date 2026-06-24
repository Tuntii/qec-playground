# QEC-Playground — Project Specification
**Versiyon:** 1.0 (25 Haziran 2026)  
**Sahip:** Tunay  
**Amaç:** 24 Haziran 2026 quant-ph makalesini (Surface-GKP + Speculative Window Decoders) herkesin kullanabileceği interaktif bir tool’a dönüştürmek.

## 1. Proje Tanımı
**Adı:** QEC-Playground (alternatif: SkipGKP, GKP-Visualizer)  
**Tagline:** "Surface-GKP kodlarında 'Ne zaman skip etsem?' sorusunun canlı cevabı. QuTiP + güzel UI ile 2 dakikada simülasyon."

**Neden yapıyoruz?**  
- Makale çok taze, henüz implementasyon yok → ilk olmak büyük avantaj.  
- Quantum meraklıları ve eğitimciler için playground tarzı tool’lar çok paylaşılıyor.  
- 8-10 günde MVP bitirip demo video atınca 7-18k star gerçekçi.

## 2. Hedef Kullanıcılar
- Quantum computing öğrencileri ve hobi sahipleri
- Qiskit/Cirq kullanan geliştiriciler
- Araştırmacılar (hızlı parametre denemek isteyenler)

## 3. Özellikler

### MVP (Gün 8-10’da bitmeli)
- [x] Circuit yükleme (hazır 5 tane GKP-surface template + QASM import)
- [x] Parametre slider’ları: GKP squeezing (dB), skip threshold, noise level, shot sayısı
- [x] Speculative Window Decoder simülasyonu (makaledeki ana algoritma)
- [x] Gerçek zamanlı grafikler: Logical error rate, syndrome heatmap, success probability chart (Plotly)
- [x] “Run Simulation” + “Compare with naive decoder” butonu
- [x] Sonuç export (PNG + CSV + “Share this config” linki)

### MVP Durum (25 Haziran 2026)
- **Çekirdek:** `core/simulator.py`, `core/decoder.py` — QuTiP GKP + speculative/naive karşılaştırma
- **UI:** `streamlit run app.py` — slider’lar, 5 template, QASM import, Plotly grafikler, export
- **CLI:** `python app.py` — headless metin çıktısı
- **Launch:** `README.md`, `assets/hero.png`, `.streamlit/config.toml`, HF/Streamlit Cloud deploy hazır (`QEC_DEMO_BASE_URL` share linkleri)

### v1.0 (Sonraki 1 hafta)
- Karşılaştırma modu (distance-5 vs distance-7)
- Preset’ler + “Random circuit generator”
- Dark theme + quantum aesthetic
- “Export as Qiskit/Cirq code” butonu

### Gelecek (contributor çekmek için)
- Adversarial error enjeksiyonu
- Leaderboard (“En iyi threshold’u bulanlar”)
- Multi-user collab modu

## 4. Tech Stack
- **Simülasyon:** QuTiP (temel) + NumPy/SciPy  
- **UI:** Streamlit (en hızlı) → istersen Next.js + shadcn + Plotly  
- **Grafikler:** Plotly + Matplotlib animasyon  
- **Diğer:** Streamlit Community Cloud / Hugging Face Spaces (ücretsiz deploy)  
- **Kurulum:** `pip install -r requirements.txt && streamlit run app.py`

## 5. Klasör Yapısı
```
qec-playground/
├── app.py
├── core/
│   ├── simulator.py      # QuTiP GKP + surface
│   ├── decoder.py        # Speculative window logic
│   └── metrics.py
├── ui/
│   ├── sliders.py
│   ├── circuit_loader.py
│   └── visualizations.py
├── examples/             # 5 hazır JSON
├── assets/               # README GIF’leri
├── requirements.txt
├── README.md
└── spec.md               # ← bu dosya
```

## 6. 10 Gün Roadmap
- **Gün 1-2:** QuTiP kurulumu + basit GKP sim + slider’lar  
- **Gün 3-4:** Speculative decoder kodlaması + heatmap  
- **Gün 5-6:** Plotly grafikleri + UI polish  
- **Gün 7:** Örnekler + export  
- **Gün 8:** README + ilk demo video  
- **Gün 9:** Hugging Face deploy + test  
- **Gün 10:** X + Reddit paylaşımı

## 7. README İçeriği (kopyala-yapıştır hazır)
- Hero GIF (slider oynatınca grafik değişiyor)
- “24 Haziran 2026 arXiv makalesinin ilk açık implementasyonu”
- Install komutu
- Interactive demo linki
- “Star’ını ver ki quantum dünyasında ilk senin tool’un ünlensin 🔥”

## 8. Launch Planı (Stars için)
1. Repo aç + bu spec + README  
2. İlk X thread’i: “24 Haziran makalesini 9 günde tool yaptım → canlı oynatın” + GIF  
3. Paylaşılacak yerler: r/QuantumComputing, Qiskit Discord, Cirq repo, Quantum Computing StackExchange  
4. İlk hafta hedef: 500-1k star

## 9. Riskler & Çözümler
- QuTiP yavaşlar → küçük circuit’lerle başla, sonra optimize et.  
- Makale detayı eksik → ilk versiyonda basit threshold simülasyonu, sonra derinleştir.  
- Görsellik zayıf kalırsa → Plotly + custom CSS ile çöz.

# 🚦 Smart Traffic Light Digital Twin — Delhi

A machine learning-powered traffic signal optimization system that predicts
congestion and dynamically adjusts traffic light timings for 4 real Delhi
junctions in real time.

Built from scratch using Python, Scikit-learn, and Streamlit.

🌐 **Live Demo:** https://smart-traffic-digital-twin.streamlit.app

---

## 📌 Project Overview

This project simulates a smart traffic control system inspired by real Delhi
junctions. It combines machine learning, proportional signal optimization,
connected junction modeling, and direction-based signal allocation to create
a realistic traffic management simulation.

---

## 📊 Model Results

| Metric | Value |
|--------|-------|
| Dataset | 48,120 real traffic records |
| Junctions | 4 (ITO, Connaught Place, Lajpat Nagar, NH-48) |
| Time period | 2015 – 2017 |
| ML Model | Random Forest Classifier |
| Model Accuracy | 77.7% |
| Baseline Accuracy | 40.7% |
| Improvement over baseline | +37.1% |
| Data Leakage | None |
| Train-Test Split | Chronological (80/20) |

---

## 🎯 Features

### Core ML & Optimization
- ✅ Random Forest model — 77.7% accuracy, +37.1% over baseline
- ✅ Zero data leakage — label and features computed separately
- ✅ Chronological train-test split — train on past, test on future
- ✅ Dynamic cycle time — total vehicles determine cycle length
- ✅ Proportional green time — each junction gets share of cycle
- ✅ ML bonus — busiest junction gets extra green when congestion > 70%

### Delhi Junction Modeling
- ✅ ITO — major commercial intersection, highest rush hour multiplier (2.5x)
- ✅ Connaught Place — central business district, busy throughout day (2.0x)
- ✅ Lajpat Nagar — residential area, moderate peaks (1.8x)
- ✅ NH-48 — national highway, consistent steady flow (1.5x)
- ✅ Weekend traffic automatically reduced by 35%

### Connected Junctions
- ✅ Vehicles flow between junctions (ITO → CP → LN → NH48)
- ✅ Simulates real-world traffic spillback effect
- ✅ Flow rates: ITO→CP: 30% | CP→LN: 20% | LN→NH48: 25% | NH48→ITO: 15%

### Direction-Based Signals
- ✅ Each junction splits traffic into N, S, E, W directions
- ✅ Each direction gets proportional green time based on vehicle load
- ✅ Live intersection diagram showing which direction has green signal

### Dashboard Modes
- ✅ Manual mode — sliders to set traffic at each junction
- ✅ Historical simulation — replays 2 years of real data in sequence
- ✅ Live simulation — auto-generates realistic Delhi traffic every few seconds
- 🚨 Peak hour indicator — detects morning (8-10am) and evening (5-8pm)
- 📊 ML confidence display — shows prediction probability as progress bar
- 📐 Optimization logic explanation — shows exactly why each decision was made

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.11 | Core programming language |
| Pandas | Data loading and manipulation |
| NumPy | Numerical operations |
| Matplotlib | Data visualization |
| Scikit-learn | Random Forest ML model |
| Streamlit | Interactive web dashboard |
| Pickle | Saving and loading trained model |

---

## 📁 Project Structure

```
smart-traffic-dt/
├── data/
│   ├── traffic.csv               # Raw Kaggle dataset
│   ├── traffic_model.pkl         # Trained ML model
│   ├── model_stats.pkl           # Accuracy metrics
│   ├── hourly_avg.csv            # Historical hour averages
│   ├── junction_avg.csv          # Historical junction averages
│   └── hourday_avg.csv           # Hour + day combination averages
├── explore_data.py               # Phase 2 — data exploration
├── analyze_data.py               # Phase 3 — data analysis
├── train_model.py                # Phase 4 — ML training
├── optimize_signals.py           # Phase 5 — signal optimization
├── delhi_traffic.py              # Delhi junction definitions & traffic generation
├── signal_optimizer.py           # Proportional signal optimization logic
├── traffic_flow.py               # Connected junctions & direction-based signals
├── dashboard.py                  # Phase 6 — Streamlit dashboard
├── requirements.txt              # All required libraries
└── README.md                     # This file
```

---

## 🚀 How to Run Locally

**1. Clone the repository**
```bash
git clone https://github.com/medha3001-hash/smart-traffic-twin.git
cd smart-traffic-twin
```

**2. Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install libraries**
```bash
pip install -r requirements.txt
```

**4. Train the model**
```bash
python3 train_model.py
```

**5. Launch the dashboard**
```bash
streamlit run dashboard.py
```

Open your browser at `http://localhost:8501`

---

## 🤖 How the ML Works

### Features used (no current vehicle counts — avoids leakage)
| Feature | Meaning |
|---------|---------|
| hour | Hour of day (0–23) |
| day_of_week | 0=Monday to 6=Sunday |
| month | Month of year |
| is_weekend | 1 if Saturday/Sunday |
| hist_hour_avg | Historical avg vehicles at this hour |
| hist_hourday_avg | Historical avg at this hour + day combo |
| hist_junction_avg | Historical avg at this junction |
| hour_vs_day_ratio | Is this hour busier than the daily average? |

### How signal timing is decided
```
Step 1 — ML model predicts congestion probability (0% to 100%)

Step 2 — Total vehicles sets cycle time:
  > 300 vehicles → 160s  EXTENDED
  > 200 vehicles → 120s  NORMAL
  > 100 vehicles → 100s  MODERATE
  ≤ 100 vehicles →  80s  REDUCED

Step 3 — Green time allocated proportionally:
  green_time = (my_vehicles / total_vehicles) × cycle_time

Step 4 — ML bonus:
  If congestion probability > 70%
  → busiest junction gets 10% extra green time

Step 5 — Direction split (N, S, E, W):
  Each direction gets green time proportional to its vehicle share
```

### Why chronological split matters
Traffic data is time-series. Random splitting lets the model see future data
during training — inflating accuracy dishonestly. Training on 2015–mid2017
and testing on mid2017–2017 simulates real deployment correctly.

---

## 🗺️ Delhi Junction Profiles

| Junction | Type | Description | Morning Multiplier | Evening Multiplier |
|----------|------|-------------|-------------------|-------------------|
| ITO | Commercial | Major intersection — highest rush hour traffic | 2.5x | 2.8x |
| Connaught Place | Commercial | Central business district — busy all day | 2.0x | 2.2x |
| Lajpat Nagar | Residential | Market area — moderate peaks | 1.8x | 1.9x |
| NH-48 | Highway | National highway — consistent flow | 1.5x | 1.6x |

---

## 🔗 Connected Junction Flow

Vehicles flow between junctions simulating real-world spillback:

```
ITO → (30%) → Connaught Place → (20%) → Lajpat Nagar → (25%) → NH-48
 ↑                                                                  |
 └──────────────────────── (15%) ───────────────────────────────────┘
```

---

## ⚠️ Known Limitations

- ML prediction uses historical time patterns only — not live vehicle counts
- No weather, holiday, or incident data included
- No inter-junction signal coordination (green wave optimization)
- Dataset is from 2015–2017 — real Delhi patterns may have shifted
- No connection to real traffic hardware

---

## 🔮 Future Improvements

- [ ] Add weather data as a feature via API
- [ ] Add public holiday calendar feature
- [ ] Try XGBoost or LSTM for better sequential prediction
- [ ] Connect to live Delhi traffic data feed
- [ ] Implement green wave coordination across junctions
- [ ] Add emergency vehicle override logic
- [ ] Deploy with real-time sensor integration

---

## 📄 Dataset

**Traffic Flow Forecasting Dataset**
Source: [Kaggle](https://www.kaggle.com/datasets/fedesoriano/traffic-flow-forecasting-dataset)
Records: 48,120 hourly vehicle counts
Period: November 2015 – June 2017
Junctions: 4

---

## 👩‍💻 Author

**Medha Bhardwaj**

Built as a complete end-to-end ML project — from raw data to live deployed
dashboard — including audit, leakage fix, Delhi junction modeling, connected
junction simulation, and direction-based signal optimization.

- GitHub: [medha3001-hash](https://github.com/medha3001-hash)

---

## 📄 License

This project is open source and available under the MIT License.
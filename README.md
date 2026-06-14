# 🚦 DriveLegal India

> Location-specific traffic laws, violations, and challan calculator for all Indian states & UTs.

---

## 📌 Overview

**DriveLegal India** is a web application that provides citizens with
location-specific traffic law information, fine schedules, and an automated challan
calculator covering all **28 states** and **8 Union Territories** of India.

All data is embedded directly in the application — **no external APIs, no internet
connection required after installation**.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

```bash
# 1. Clone or download the project


# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## 🗂️ Project Structure

```
drivelegal/
├── app.py              # Main application (all logic + UI)
├── requirements.txt    # Python dependencies
└── README.md           
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧮 Challan Calculator | Select violation + vehicle type + state → instant fine breakdown |
| 📋 Traffic Laws | Full MV Act 1988/2019 section reference |
| 🗺️ State-wise Rules | Searchable state/UT specific rules, speed limits, surcharges |
| ⚡ Offline Mode | No API calls — works without internet |
| 🔁 Repeat Offence | Double-fine calculation for repeat offenders |
| 🚗 Vehicle Types | 7 vehicle categories with adjusted fine multipliers |


---

## ⚖️ Legal Data Sources

- Motor Vehicles Act, 1988
- Motor Vehicles (Amendment) Act, 2019
- MoRTH (Ministry of Road Transport & Highways) speed limit notifications
- State Transport Department rules (surcharges, local enforcement notes)

---



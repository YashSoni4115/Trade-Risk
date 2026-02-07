# TariffShock Project Context

> **Last Updated:** February 7, 2026  
> **Status:** Risk Engine MVP Complete ✅

---

## 📋 Project Overview

**TariffShock** is an explainable, scenario-based tariff risk engine for Canadian industries. It quantifies how U.S. and other tariffs impact Canadian export sectors.

### Hackathon Tracks
- Best Use of Data Visualization
- Best Use of AI for Good
- Best Use of Gemini API

---

## 🏗️ Project Structure

```
cxc/
├── app.py                      # Entry point (Flask server on port 5001)
├── prd.txt                     # Product Requirements Document
├── README.md                   # Documentation
├── context.md                  # THIS FILE - project context
├── .gitignore                  # Ignores raw data (local only)
├── data/
│   ├── processed/              # Preprocessed datasets (tracked in git)
│   │   ├── sector_risk_dataset.csv     # 98 sectors, 21 features
│   │   ├── partner_trade_data.csv      # Trade by partner
│   │   └── supplier_change_data.csv    # Industry supplier changes
│   ├── 2024_EXP_HS2/           # Raw export data (LOCAL ONLY - not in git)
│   ├── 2024_IMP_HS2/           # Raw import data (LOCAL ONLY - not in git)
│   ├── Business_Supplier_Change_*.csv  # (LOCAL ONLY - not in git)
├── scripts/
│   └── prepare_tariff_risk_dataset.py  # Data preprocessing
├── src/
│   ├── __init__.py
│   ├── schemas.py              # Input validation schemas
│   ├── load_data.py            # Data loading module
│   ├── risk_engine.py          # Core risk calculation engine
│   ├── tariff_data.py          # Actual tariff rates on Canada
│   └── routes.py               # Flask API endpoints
└── tests/
    └── test_risk_engine.py     # 37 unit tests (all passing)
```

---

## 🔢 Risk Calculation Formula

```
Risk Score = (w_exposure × exposure + w_concentration × concentration) × shock × 100

Where:
- w_exposure = 0.6
- w_concentration = 0.4
- exposure = sum of partner shares for target partners (0-1)
- concentration = top_partner_share (0-1)
- shock = tariff_percent / 25 (0-1)
```

---

## 🌐 API Endpoints (Port 5001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/sectors` | List all 98 sectors |
| GET | `/api/sector/<id>` | Get sector details (HS2 code) |
| GET | `/api/baseline` | Get baseline risk scores |
| POST | `/api/scenario` | Calculate risk for simulated tariff scenario |
| POST | `/api/compare` | Compare baseline vs shocked scenario |
| GET | `/api/actual-tariffs` | **Risk using ACTUAL tariffs on Canada** |
| GET | `/api/tariff-rates` | View actual tariff rates by sector |
| GET | `/api/partners` | List valid partners (US, China, EU) |
| GET | `/api/config` | Get engine configuration |

---

## 📊 Actual Tariffs on Canada (Included)

| Sector | HS2 | US Tariff | China Tariff | EU Tariff |
|--------|-----|-----------|--------------|-----------|
| Iron & Steel | 72, 73 | 25% | - | 5% |
| Vehicles | 87 | 25% | - | - |
| Wood/Lumber | 44 | 20% | - | - |
| Aluminum | 76 | 10% | - | 5% |
| Cereals | 10 | 10% | 25% | - |
| Oil Seeds | 12 | - | 25% | - |
| Dairy | 04 | 15% | - | - |
| Machinery | 84, 85 | 10% | - | - |
| Mineral Fuels | 27 | 10% | - | - |
| Furniture | 94 | 15% | - | - |

---

## 🎯 Top Risk Sectors (Actual Tariffs)

| Rank | Sector | Risk Score | Tariff | Affected Exports |
|------|--------|------------|--------|------------------|
| 1 | Iron & steel articles | 92.6 | 25% | $7.5B |
| 2 | Vehicles | 91.3 | 25% | $66.6B |
| 3 | Iron & steel | 87.2 | 25% | $9.9B |
| 4 | Wood | 69.1 | 20% | $11.8B |
| 5 | Furniture | 57.8 | 15% | $4.5B |

---

## ✅ Completed Tasks

- [x] Data preprocessing script
- [x] Sector risk dataset (98 sectors, 21 features)
- [x] Input validation schemas
- [x] Risk engine core logic
- [x] Flask API endpoints
- [x] Unit tests (37 passing)
- [x] Actual tariff rates on Canada
- [x] `/api/actual-tariffs` endpoint
- [x] `/api/tariff-rates` endpoint

---

## 🔜 Next Steps / TODO

- [ ] Frontend visualization (React/D3.js)
- [ ] Gemini API integration for explanations
- [ ] Scenario comparison UI
- [ ] Historical trend analysis
- [ ] Company-level data (stretch goal)

---

## 🚀 Quick Start

```bash
# Start server
/Users/yash/Desktop/cxc/.venv/bin/python app.py

# Test actual tariffs on Canada
curl http://localhost:5001/api/actual-tariffs

# Test simulated scenario
curl -X POST http://localhost:5001/api/scenario \
  -H "Content-Type: application/json" \
  -d '{"tariff_percent": 10, "target_partners": ["US"]}'
```

---

## 📝 Session Notes

### February 7, 2026
- Created TariffShock risk engine from scratch
- Processed Canadian trade data (exports/imports at HS2 level)
- Built deterministic risk calculation per PRD spec
- Added actual US/China/EU tariff rates on Canada
- All 37 unit tests passing
- Server running on port 5001

---

## 🔗 Key Files to Reference

| Purpose | File |
|---------|------|
| Requirements | `prd.txt` |
| Risk logic | `src/risk_engine.py` |
| Tariff rates | `src/tariff_data.py` |
| API routes | `src/routes.py` |
| Tests | `tests/test_risk_engine.py` |

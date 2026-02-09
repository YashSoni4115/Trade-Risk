# TradeRisk Risk Engine

A deterministic computation module for quantifying tariff exposure risk for Canadian sectors.

## Project Structure

```
cxc/
├── app.py                  # Application entry point
├── prd.txt                 # Product Requirements Document
├── data/
│   ├── processed/          # Processed datasets
│   │   ├── sector_risk_dataset.csv
│   │   ├── partner_trade_data.csv
│   │   └── supplier_change_data.csv
│   └── ...                 # Raw data files
├── scripts/
│   └── prepare_tariff_risk_dataset.py  # Data preprocessing
├── src/
│   ├── __init__.py
│   ├── schemas.py          # Input validation schemas
│   ├── load_data.py        # Data loading module
│   ├── risk_engine.py      # Core risk calculation engine
│   └── routes.py           # HTTP API endpoints
└── tests/
    └── test_risk_engine.py # Unit tests
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Data

```bash
python scripts/prepare_tariff_risk_dataset.py
```

### 3. Run Tests

```bash
pytest tests/test_risk_engine.py -v
```

### 4. Start the API Server

```bash
python app.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/sectors` | List all sectors |
| GET | `/api/sector/<id>` | Get sector details |
| GET | `/api/baseline` | Get baseline risk scores |
| POST | `/api/scenario` | Calculate scenario risk |
| POST | `/api/compare` | Compare two scenarios |
| GET | `/api/partners` | List valid partners |
| GET | `/api/config` | Get engine configuration |
| POST | `/api/chat/context` | Chatbot-ready context via Backboard cache |
| POST | `/api/chat/explanation` | Store Gemini explanations in Backboard |

## Example Scenario Request

```bash
curl -X POST http://localhost:5000/api/scenario \
  -H "Content-Type: application/json" \
  -d '{
    "tariff_percent": 10,
    "target_partners": ["US"]
  }'
```

## Backboard Integration

### Environment Variables

- `BACKBOARD_BASE_URL` (required for caching)
- `BACKBOARD_API_KEY` (required for caching)
- `ENGINE_VERSION` (bump when risk math or ML model changes)

The API server loads variables from `backend/.env` at startup.

Optional:
- `BACKBOARD_TIMEOUT` (seconds, default 5)
- `BACKBOARD_MAX_RETRIES` (default 2)

### Caching Behavior

- Scenario inputs are normalized and hashed (`scenario_id`).
- Cached results are reused only if `engine_version` matches.
- If Backboard is unavailable, the API computes locally and returns `cached=false` with a warning.

### Example Chat Context Request

```bash
curl -X POST http://localhost:5001/api/chat/context \
  -H "Content-Type: application/json" \
  -d '{
    "tariff_percent": 15,
    "target_partners": ["US"],
    "sector_id": "72",
    "model_mode": "deterministic",
    "explanation_type": "explanation"
  }'
```

## Risk Calculation Formula

```
Risk = (w_exposure × exposure + w_concentration × concentration) × shock

Where:
- w_exposure = 0.6
- w_concentration = 0.4
- exposure = sum of partner shares for target partners
- concentration = top_partner_share
- shock = tariff_percent / 25
```

## Testing

The test suite includes:
- Schema validation tests
- Exposure calculation correctness
- Risk monotonicity (higher tariffs → higher risk)
- Risk bounds (0-100)
- Golden test (fixed inputs → fixed outputs)

Run all tests:
```bash
pytest tests/ -v
```

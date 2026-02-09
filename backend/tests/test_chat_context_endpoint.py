from src.routes import create_app


class FakeDataLayer:
    def __init__(self):
        self.calls = []

    def get_or_compute_chat_context(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "scenario": {"scenario_id": "abc", "engine_version": "1"},
            "sector": {"sector_id": "72", "sector_name": "Iron"},
            "risk": {
                "baseline_risk": 0.0,
                "scenario_risk": 48.2,
                "delta": 48.2,
                "exposure": 0.62,
                "concentration": 0.62,
                "shock": 0.6,
                "affected_export_value": 1850000000,
            },
            "drivers": [
                {"name": "Exposure", "value": 0.62},
                {"name": "Concentration", "value": 0.62},
                {"name": "Shock", "value": 0.6},
            ],
            "leaderboard_snippet": [],
            "cached": True,
            "existing_explanation": "cached explanation",
        }


def test_chat_context_endpoint_shape():
    app = create_app()
    app.config["BACKBOARD_DATA_LAYER"] = FakeDataLayer()

    client = app.test_client()
    resp = client.post(
        "/api/chat/context",
        json={
            "tariff_percent": 15,
            "target_partners": ["US"],
            "sector_id": "72",
            "model_mode": "deterministic",
            "explanation_type": "explanation",
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "scenario" in data
    assert "sector" in data
    assert "risk" in data
    assert "drivers" in data
    assert "leaderboard_snippet" in data
    assert data["cached"] is True
    assert data["existing_explanation"] == "cached explanation"

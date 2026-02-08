import json

from src.backboard_client import BackboardClient


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, req, timeout):
        self.calls.append({
            "url": req.full_url,
            "method": req.method,
            "data": req.data.decode("utf-8") if req.data else None,
            "headers": dict(req.header_items()),
            "timeout": timeout,
        })
        payload = json.dumps({"ok": True}).encode("utf-8")
        return 200, payload


def test_create_get_query_upsert():
    transport = FakeTransport()
    client = BackboardClient(base_url="https://backboard.local", api_key="test", transport=transport)

    client.create("scenarios", {"a": 1})
    client.get("scenarios", "abc")
    client.query("risk_results", {"filter": "x"})
    client.upsert("sectors", "01", {"sector_id": "01"})

    assert len(transport.calls) == 4
    assert transport.calls[0]["method"] == "POST"
    assert transport.calls[0]["url"].endswith("/collections/scenarios/documents")

    assert transport.calls[1]["method"] == "GET"
    assert transport.calls[1]["url"].endswith("/collections/scenarios/documents/abc")

    assert transport.calls[2]["method"] == "POST"
    assert transport.calls[2]["url"].endswith("/collections/risk_results/query")

    assert transport.calls[3]["method"] == "PUT"
    assert transport.calls[3]["url"].endswith("/collections/sectors/documents/01")

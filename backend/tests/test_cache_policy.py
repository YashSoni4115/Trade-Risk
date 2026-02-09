from src.data_layer import BackboardDataLayer

class FakeClient:
    def __init__(self, scenario_doc=None, risk_doc=None):
        self.scenario_doc = scenario_doc
        self.risk_doc = risk_doc

    def get(self, collection, document_id):
        if collection == "scenarios":
            return self.scenario_doc
        if collection == "risk_results":
            return self.risk_doc
        return None


class FakeEngine:
    pass


def test_cache_hit_when_version_matches():
    client = FakeClient(
        scenario_doc={"engine_version": "1"},
        risk_doc={"engine_version": "1"},
    )
    layer = BackboardDataLayer(client=client, risk_engine=FakeEngine(), ml_model=None, engine_version="1")

    cached = layer.get_cached_result("abc", "deterministic")
    assert cached is not None


def test_cache_miss_when_version_differs():
    client = FakeClient(
        scenario_doc={"engine_version": "1"},
        risk_doc={"engine_version": "2"},
    )
    layer = BackboardDataLayer(client=client, risk_engine=FakeEngine(), ml_model=None, engine_version="1")

    cached = layer.get_cached_result("abc", "deterministic")
    assert cached is None

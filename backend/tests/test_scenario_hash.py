from src.data_layer import scenario_hash


def test_scenario_hash_deterministic():
    h1 = scenario_hash(10, ["US", "China"], ["72", "10"], "deterministic")
    h2 = scenario_hash(10.0, ["China", "US"], ["10", "72"], "deterministic")
    assert h1 == h2


def test_scenario_hash_differs_on_inputs():
    h1 = scenario_hash(10, ["US"], None, "deterministic")
    h2 = scenario_hash(15, ["US"], None, "deterministic")
    assert h1 != h2

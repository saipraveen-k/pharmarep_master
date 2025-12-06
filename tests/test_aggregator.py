from backend.aggregator import aggregate_and_score


def test_aggregate_empty():
    res = aggregate_and_score(
        {"papers": [], "clinical_trials": [], "patents": [], "market": []}
    )
    assert res == []

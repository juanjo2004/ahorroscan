from instagram_insights import extract


def test_extracts_current_media_metrics():
    payload = {
        "data": [
            {"name": "views", "values": [{"value": 123}]},
            {"name": "reach", "values": [{"value": 77}]},
            {"name": "likes", "values": [{"value": 9}]},
            {"name": "comments", "values": [{"value": 2}]},
            {"name": "saved", "values": [{"value": 4}]},
            {"name": "shares", "values": [{"value": 3}]},
            {"name": "total_interactions", "values": [{"value": 18}]},
        ]
    }
    assert extract(payload) == {
        "views": 123, "reach": 77, "likes": 9, "comments": 2,
        "saved": 4, "shares": 3, "total_interactions": 18,
    }


def test_extract_uses_latest_value():
    payload = {"data": [{"name": "views", "values": [{"value": 1}, {"value": 8}]}]}
    assert extract(payload)["views"] == 8


def test_extract_ignores_missing_values():
    payload = {"data": [{"name": "reach", "values": []}, {"name": "likes"}]}
    assert extract(payload) == {}

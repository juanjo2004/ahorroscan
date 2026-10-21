import aggregator

def test_blocked_title():
    assert aggregator._bad_title("Funda para iPhone")
    assert aggregator._bad_title("Cable USB-C")
    assert not aggregator._bad_title("Logitech G305 Ratón Gaming")

def test_live_selection():
    selected, ranked = aggregator.rank_candidates()
    assert len(ranked) >= len(selected)
    assert len(selected) <= aggregator.MAX_PER_RUN
    assert len({r["source"]+":"+r["external_id"] for r in selected}) == len(selected)
    assert all(r["global_score"] >= aggregator.MIN_SCORE for r in selected)
    assert all(not aggregator._bad_title(r["title"]) for r in selected)

def test_global_score_uses_clicks():
    row={"score":60,"discount":20,"rating":4.0,"reviews":10,"published_at":"2026-09-20T10:00:00+00:00","product_id":1}
    a,_=aggregator._candidate_score(row,{("tech",1):0},"tech")
    b,_=aggregator._candidate_score(row,{("tech",1):3},"tech")
    assert b > a

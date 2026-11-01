from fastapi.testclient import TestClient

from trueshelf.api import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["ok"]


def test_search_returns_ranked_hotels():
    r = client.get("/api/search", params={"city": "BKK", "limit": 5}).json()
    assert [x["rank"] for x in r["results"]] == [1, 2, 3, 4, 5]
    assert r["hotels"] < r["supplier_records"]


def test_match_endpoint_merges_obvious_pair_and_separates_sisters():
    a = {"supplier": "ATL", "city": "DXB", "name": "QASR AL TWR INN", "lat": 25.2711, "lon": 55.3075, "stars": 4,
         "address": "12 Al Rigga Rd, Deira", "phone": "+97142223333"}
    b = {**a, "supplier": "BLU", "name": "Kasr El Tower Inn", "lat": 25.2713, "lon": 55.3077, "phone": "04 222 3333"}
    sis = {**a, "supplier": "BLU", "name": "Qasr Al Tower Suites", "lat": 25.2725, "lon": 55.3090, "phone": "04 999 1111",
           "address": "20 Al Rigga Rd, Deira"}
    same = client.post("/api/match", json={"a": a, "b": b}).json()
    diff = client.post("/api/match", json={"a": a, "b": sis}).json()
    assert same["decision"] == "merge" and same["p_same"] > diff["p_same"]
    assert diff["decision"] != "merge"
    assert same["why"]


def test_input_validation():
    bad = {"supplier": "ATL", "city": "XXX", "name": "x", "lat": 0, "lon": 0}
    assert client.post("/api/match", json={"a": bad, "b": bad}).status_code == 422


def test_l4l_endpoint():
    r = client.post("/api/l4l", json={"sell_inr": 20000, "board": "BB", "cancel_free_until_days": None, "supplier": "MER", "city": "DXB"}).json()
    c = r["components"]
    assert c["meals"] < 0 and c["cancellation"] > 0 and c["supplier_risk"] > 0


def test_review_decision_is_logged():
    q = client.get("/api/review", params={"limit": 1}).json()
    assert "truth_same" not in q[0]
    r = client.post(f"/api/review/{q[0]['pair']}", json={"same": True, "reviewer": "ops.demo"}).json()
    assert r["logged"] and r["reviewer"] == "ops.demo"


def test_static_ui_served():
    assert "TrueShelf" in client.get("/").text

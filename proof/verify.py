"""In-browser verification driver for TrueShelf (runs under Pyodide).

Every step is a separate call so the page can show progress between steps.
Nothing here is precomputed: the synthetic world is regenerated from its
seeds, features are computed, the model is trained on Dubai + Bangkok and
scored on Paris, exactly as in trueshelf/pipeline.py.
"""
import io
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["RAPIDFUZZ_IMPLEMENTATION"] = "python"  # pure-Python RapidFuzz, verified identical to native
for p in (os.path.join(ROOT, "vendor"), ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

S = {}


def env():
    import numpy, scipy, sklearn, rapidfuzz
    return json.dumps({"python": sys.version.split()[0], "numpy": numpy.__version__, "scipy": scipy.__version__,
                       "sklearn": sklearn.__version__, "rapidfuzz": rapidfuzz.__version__ + " (pure Python)"})


def unit_tests():
    import pytest
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    t = time.time()
    try:
        code = pytest.main(["-q", "-p", "no:cacheprovider", "--rootdir", ROOT, os.path.join(ROOT, "tests", "test_units.py")])
    finally:
        sys.stdout = old
    return json.dumps({"exit": int(code), "seconds": round(time.time() - t, 1), "log": buf.getvalue()[-6000:]})


def world():
    from trueshelf.synth.world import generate_hotels
    from trueshelf.synth.suppliers import generate_supplier_feeds, to_dicts
    t = time.time()
    hotels = generate_hotels(seed=7)
    hrecs, _ = generate_supplier_feeds(hotels, seed=11)
    S["recs"] = to_dicts(hrecs)
    S["D"], S["idf"] = {}, {}
    return json.dumps({"hotels": len(hotels), "records": len(S["recs"]), "seconds": round(time.time() - t, 1)})


def features(city):
    import numpy as np
    from trueshelf.hotel_match import prepare_all, build_candidates
    t = time.time()
    R = prepare_all([r for r in S["recs"] if r["city"] == city])
    cands, idf = build_candidates(R)
    X = np.array([c.feats for c in cands])
    y = np.array([int(R[c.a]["true_hotel_id"] == R[c.b]["true_hotel_id"]) for c in cands])
    S["D"][city] = (R, cands, X, y)
    S["idf"][city] = idf
    return json.dumps({"city": city, "records": len(R), "pairs": len(cands), "true_pairs": int(y.sum()), "seconds": round(time.time() - t, 1)})


def train(test_city="PAR"):
    import numpy as np
    from trueshelf.hotel_match import HotelMatcher
    t = time.time()
    tr = [c for c in S["D"] if c != test_city]
    S["model"] = HotelMatcher().fit(np.vstack([S["D"][c][2] for c in tr]), np.concatenate([S["D"][c][3] for c in tr]))
    S["test_city"] = test_city
    return json.dumps({"trained_on": tr, "rows": int(sum(len(S["D"][c][3]) for c in tr)), "seconds": round(time.time() - t, 1)})


def evaluate():
    from trueshelf.hotel_match import cluster, baseline_rule_cluster
    from trueshelf.metrics import pairwise_prf, exact_cluster_rate
    t = time.time()
    c = S["test_city"]
    R, cands, X, y = S["D"][c]
    p = S["model"].predict_proba(X)
    truth = [r["true_hotel_id"] for r in R]
    lab = cluster(R, cands, p, 0.90)
    base = baseline_rule_cluster(R)
    a, b = pairwise_prf(lab, truth), pairwise_prf(base, truth)
    review = int(((p >= 0.30) & (p < 0.90)).sum())
    return json.dumps({"city": c, "f1": a["f1"], "precision": a["precision"], "recall": a["recall"], "false_merges": a["false_merges"],
                       "missed_merges": a["missed_merges"], "exact": exact_cluster_rate(lab, truth), "baseline_f1": b["f1"],
                       "baseline_false": b["false_merges"], "baseline_missed": b["missed_merges"], "review_pairs": review,
                       "listings": len(set(lab)), "true_hotels": len(set(truth)), "seconds": round(time.time() - t, 1)})


def match(a_json, b_json):
    import numpy as np
    from trueshelf.hotel_match import pair_features
    from trueshelf.normalize import prepare
    a, b = json.loads(a_json), json.loads(b_json)
    city = a.get("city", "DXB")
    idf = S["idf"].get(city) or next(iter(S["idf"].values()))
    for r, rid in ((a, "a"), (b, "b")):
        r["rec_id"], r["city"] = rid, city
        for k in ("lat", "lon", "stars"):
            r[k] = float(r[k]) if r.get(k) not in (None, "") else None
    x = pair_features(prepare(a), prepare(b), idf)
    p = float(S["model"].predict_proba(np.array([x]))[0])
    decision = "merge" if p >= 0.90 else "review" if p >= 0.30 else "keep apart"
    return json.dumps({"p": p, "decision": decision, "why": S["model"].explain(x, top=6)})

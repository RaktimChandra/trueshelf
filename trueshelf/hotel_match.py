"""Layer 1 of TrueShelf: "Is this the same place?"

Pipeline: normalize -> block (geo cells + rare-token index) -> pairwise features
-> calibrated gradient-boosted classifier -> constrained clustering.

The constraint that makes clustering robust: a supplier almost never lists the
same building twice, so two records from one supplier are only allowed in one
cluster when their own direct match score is near-certain. This single rule
stops most chain-reaction merges of sister properties.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier

from .normalize import haversine, prepare

FEATURES = [
    "name_token_set", "name_sort_ratio", "name_jw", "name_partial", "idf_jaccard", "core_len_diff",
    "type_conflict", "type_equal", "digit_conflict",
    "log_dist", "dist_lt_100", "dist_lt_400",
    "phone_match", "phone_missing", "street_no_match", "street_no_missing", "street_jaccard",
    "star_diff", "star_missing", "chain_match", "chain_missing", "same_supplier", "coord_fixed",
]

# Plain-language labels used by the Review Desk to explain a score.
FEATURE_LABELS = {
    "name_token_set": "Name words overlap", "name_sort_ratio": "Name spelling similarity", "name_jw": "Name prefix similarity",
    "name_partial": "One name contains the other", "idf_jaccard": "Rare-word overlap", "core_len_diff": "Name length gap",
    "type_conflict": "Property-type words differ (Suites vs Hotel...)", "type_equal": "Property-type words agree",
    "digit_conflict": "Numbers in names differ", "log_dist": "Distance", "dist_lt_100": "Within 100 m", "dist_lt_400": "Within 400 m",
    "phone_match": "Phone number match", "phone_missing": "Phone missing", "street_no_match": "Street number match",
    "street_no_missing": "Street number missing", "street_jaccard": "Street words overlap", "star_diff": "Star-rating gap",
    "star_missing": "Stars missing", "chain_match": "Chain match", "chain_missing": "Chain missing",
    "same_supplier": "Both from one supplier", "coord_fixed": "Coordinates were repaired",
}


@dataclass
class Candidate:
    a: int
    b: int
    feats: list[float]


def _idf(recs: list[dict]) -> dict:
    df = defaultdict(int)
    for r in recs:
        for t in set(r["_core"]):
            df[t] += 1
    n = len(recs)
    return {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}


# How to read a yes/no signal when it is "no" (value 0).
FEATURE_LABELS_OFF = {
    "type_conflict": "No property-type conflict", "type_equal": "Property-type words differ",
    "digit_conflict": "No conflicting numbers in names", "dist_lt_100": "More than 100 m apart", "dist_lt_400": "More than 400 m apart",
    "phone_match": "Phone numbers differ", "phone_missing": "Both have a phone", "street_no_match": "Street numbers differ or missing",
    "street_no_missing": "Both have a street number", "star_missing": "Both have stars", "chain_match": "Chain not confirmed",
    "chain_missing": "Both name a chain", "same_supplier": "From different suppliers", "coord_fixed": "Coordinates as sent",
}
BINARY = set(FEATURE_LABELS_OFF)


def _cell(lat, lon, size_deg=0.012):
    return (int(math.floor(lat / size_deg)), int(math.floor(lon / size_deg)))


def block(recs: list[dict], idf: dict, max_dist_m: float = 1500, rare_idf: float = 2.6) -> set[tuple[int, int]]:
    """Candidate pairs within a city. Two independent keys keep recall high:
    nearby in space (3x3 grid cells), or sharing a rare name word (catches bad coordinates)."""
    pairs: set[tuple[int, int]] = set()
    grid = defaultdict(list)
    for i, r in enumerate(recs):
        grid[_cell(r["_lat"], r["_lon"])].append(i)
    for i, r in enumerate(recs):
        cx, cy = _cell(r["_lat"], r["_lon"])
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if j > i and haversine(r["_lat"], r["_lon"], recs[j]["_lat"], recs[j]["_lon"]) <= max_dist_m:
                        pairs.add((i, j))
    inv = defaultdict(list)
    for i, r in enumerate(recs):
        rare = sorted(set(r["_core"]), key=lambda t: (-idf.get(t, 0), t))[:2]
        for t in rare:
            if idf.get(t, 0) >= rare_idf:
                inv[t].append(i)
    for t, ids in inv.items():
        if len(ids) > 40:
            continue
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                pairs.add((min(ids[x], ids[y]), max(ids[x], ids[y])))
    return pairs


def pair_features(r1: dict, r2: dict, idf: dict) -> list[float]:
    c1, c2 = r1["_core_sorted"], r2["_core_sorted"]
    s1, s2 = set(r1["_core"]), set(r2["_core"])
    inter = sum(idf.get(t, 1) for t in sorted(s1 & s2))
    union = sum(idf.get(t, 1) for t in sorted(s1 | s2)) or 1
    t1, t2 = set(r1["_types"]), set(r2["_types"])
    d1 = {t for t in s1 if t.isdigit()}
    d2 = {t for t in s2 if t.isdigit()}
    dist = haversine(r1["_lat"], r1["_lon"], r2["_lat"], r2["_lon"])
    p1, p2 = r1["_phone"], r2["_phone"]
    n1, n2 = r1["_street_no"], r2["_street_no"]
    st1, st2 = set(r1["_street"]), set(r2["_street"])
    sj = len(st1 & st2) / (len(st1 | st2) or 1)
    sa, sb = r1.get("stars"), r2.get("stars")
    ch1, ch2 = r1.get("chain"), r2.get("chain")
    return [
        fuzz.token_set_ratio(c1, c2) / 100, fuzz.ratio(c1, c2) / 100, JaroWinkler.similarity(r1["_core_str"], r2["_core_str"]),
        fuzz.partial_ratio(c1, c2) / 100, inter / union, abs(len(s1) - len(s2)),
        float(len(t1 ^ t2) > 0), float(t1 == t2), float(bool(d1 or d2) and d1 != d2),
        math.log10(1 + dist), float(dist < 100), float(dist < 400),
        float(p1 is not None and p1 == p2), float(p1 is None or p2 is None),
        float(n1 is not None and n1 == n2), float(n1 is None or n2 is None), sj,
        abs(sa - sb) if sa is not None and sb is not None else 0.0, float(sa is None or sb is None),
        float(ch1 is not None and ch1 == ch2), float(ch1 is None or ch2 is None),
        float(r1["supplier"] == r2["supplier"]), float(r1["_coord_fixed"] or r2["_coord_fixed"]),
    ]


def build_candidates(recs: list[dict]) -> tuple[list[Candidate], dict]:
    idf = _idf(recs)
    pairs = block(recs, idf)
    return [Candidate(a, b, pair_features(recs[a], recs[b], idf)) for a, b in sorted(pairs)], idf


class HotelMatcher:
    """Calibrated pairwise model. Probabilities, not raw scores, drive the
    merge / review / keep-apart decision so thresholds mean the same thing in
    every city."""

    def __init__(self, seed: int = 0):
        base = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=24,
                                              l2_regularization=1.0, early_stopping=False, random_state=seed)
        self.model = CalibratedClassifierCV(base, method="isotonic", cv=3)
        self._explainer = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.model.fit(X, y)
        # Simple, faithful local explanation: a logistic model on the same
        # features, used only to say *which signals* pushed a pair up or down.
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        self._scaler = StandardScaler().fit(X)
        self._explainer = LogisticRegression(max_iter=2000, C=0.5).fit(self._scaler.transform(X), y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def explain(self, x: list[float], top: int = 5) -> list[dict]:
        z = self._scaler.transform(np.array([x]))[0]
        contrib = z * self._explainer.coef_[0]
        order = np.argsort(-np.abs(contrib))[:top]
        out = []
        for i in order:
            f = FEATURES[i]
            lbl = FEATURE_LABELS_OFF[f] if f in BINARY and x[i] == 0 else FEATURE_LABELS[f]
            val = ("yes" if x[i] else "no") if f in BINARY else round(float(x[i]), 3)
            if f == "log_dist":
                lbl, val = "Distance between pins", f"{round(10 ** x[i] - 1):,} m"
            out.append({"feature": f, "label": lbl, "value": val, "push": round(float(contrib[i]), 2)})
        return out


def cluster(recs: list[dict], cands: list[Candidate], probs: np.ndarray, auto: float,
            same_supplier_min: float = 0.97) -> list[int]:
    """Greedy constrained agglomeration over auto-merge edges, strongest first."""
    parent = list(range(len(recs)))
    members = {i: {i} for i in range(len(recs))}
    sups = {i: {recs[i]["supplier"]: 1} for i in range(len(recs))}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edge_p = {}
    for c, p in zip(cands, probs):
        edge_p[(c.a, c.b)] = p
    for idx in np.argsort(-probs):
        p = probs[idx]
        if p < auto:
            break
        c = cands[idx]
        ra, rb = find(c.a), find(c.b)
        if ra == rb:
            continue
        clash = set(sups[ra]) & set(sups[rb])
        if clash:
            # allow only if every clashing pair is itself near-certain
            ok = True
            for s in clash:
                for i in members[ra]:
                    if recs[i]["supplier"] != s:
                        continue
                    for j in members[rb]:
                        if recs[j]["supplier"] != s:
                            continue
                        if edge_p.get((min(i, j), max(i, j)), 0.0) < same_supplier_min:
                            ok = False
            if not ok:
                continue
        parent[rb] = ra
        members[ra] |= members.pop(rb)
        for s, n in sups.pop(rb).items():
            sups[ra][s] = sups[ra].get(s, 0) + n
    return [find(i) for i in range(len(recs))]


def baseline_rule_cluster(recs: list[dict], name_min: float = 85, dist_max: float = 300) -> list[int]:
    """The usual hand-written rule: similar name AND close by -> same hotel."""
    from .normalize import fold
    idf = _idf(recs)
    pairs = block(recs, idf)
    parent = list(range(len(recs)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        r1, r2 = recs[a], recs[b]
        if fuzz.token_sort_ratio(fold(r1["name"]), fold(r2["name"])) >= name_min and \
                haversine(r1["lat"], r1["lon"], r2["lat"], r2["lon"]) <= dist_max:
            parent[find(b)] = find(a)
    return [find(i) for i in range(len(recs))]


def prepare_all(hotel_recs: list[dict]) -> list[dict]:
    return [prepare(r) for r in hotel_recs]

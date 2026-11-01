"""ShelfRank: listing order for consolidated hotel shelves.

Score = value of the best like-for-like deal vs comparable hotels
      + quality (stars, reviews, content richness)
      + expected gross profit for TBO (margin x probability the booking succeeds)
      + trust (supplier reliability of the winning offer)
then a diversity pass (maximal marginal relevance) so the first screen is not
ten near-identical hotels in one street at one price, and a bounded, visible
Platinum lift (a commercial lever that can never bury a better deal by more
than a fixed number of slots).
"""
from __future__ import annotations

from .config import RankParams


def _pct_rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    for r, i in enumerate(order):
        out[i] = r / max(1, len(values) - 1)
    return out


def score_shelves(shelves: list[dict], params: RankParams) -> list[dict]:
    if not shelves:
        return []
    # value: L4L relative to hotels of the same star band
    by_star: dict[int, list[int]] = {}
    for i, s in enumerate(shelves):
        by_star.setdefault(s["stars"], []).append(i)
    value = [0.0] * len(shelves)
    for star, idx in by_star.items():
        ranks = _pct_rank([shelves[i]["best"]["l4l_per_night"] for i in idx])
        for j, i in enumerate(idx):
            value[i] = 1 - ranks[j]
    gp = [s["best"]["exp_gp"] for s in shelves]
    gmax = max(gp) or 1
    for i, s in enumerate(shelves):
        quality = 0.45 * (s["stars"] - 2) / 3 + 0.35 * (s["review_score"] - 6) / 4 + 0.20 * s["content_score"]
        trust = 1 - min(1.0, s["best"]["p_fail"] / 0.12)
        parts = {"value": params.w_value * value[i], "quality": params.w_quality * quality,
                 "margin": params.w_margin * gp[i] / gmax, "trust": params.w_trust * trust}
        s["score_parts"] = {k: round(v, 4) for k, v in parts.items()}
        s["score"] = round(sum(parts.values()), 4)
    return shelves


def _sim(a: dict, b: dict) -> float:
    same_area = a["area"] == b["area"]
    p1, p2 = a["best"]["l4l_per_night"], b["best"]["l4l_per_night"]
    close_price = abs(p1 - p2) / max(p1, p2) < 0.12
    return 0.5 * same_area + 0.3 * close_price + 0.2 * (a["stars"] == b["stars"])


def rank(shelves: list[dict], params: RankParams, top_k: int = 60) -> list[dict]:
    pool = sorted(shelves, key=lambda s: -s["score"])
    chosen: list[dict] = []
    while pool and len(chosen) < top_k:
        best_i, best_v = 0, -1e9
        for i, s in enumerate(pool[:40]):
            div = max((_sim(s, c) for c in chosen[-8:]), default=0.0)
            v = s["score"] - params.diversity_lambda * div * 0.1
            if v > best_v:
                best_i, best_v = i, v
        chosen.append(pool.pop(best_i))
    chosen += pool
    # bounded Platinum lift, applied last and visibly
    for pos in range(len(chosen)):
        s = chosen[pos]
        if s.get("platinum") and not s.get("_lifted"):
            new = max(0, pos - params.platinum_max_lift)
            s["_lifted"] = pos - new
            chosen.insert(new, chosen.pop(pos))
    for i, s in enumerate(chosen):
        s["rank"] = i + 1
        s["platinum_lift"] = s.pop("_lifted", 0)
    return chosen

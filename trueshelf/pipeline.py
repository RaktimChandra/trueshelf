"""End-to-end pipeline: supplier feeds -> shelves, review queue, evidence.

Evaluation discipline: the hotel matcher used for a city is always trained on
the *other* cities only (leave-one-city-out), so every number reported for a
city is a held-out number.
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from statistics import median

import numpy as np

from .config import CITIES, DEFAULT, Config
from .hotel_match import FEATURE_LABELS, FEATURES, HotelMatcher, baseline_rule_cluster, build_candidates, cluster, prepare_all
from .l4l import l4l
from .metrics import exact_cluster_rate, listing_counts, pairwise_prf
from .reliability import ledger
from .room_map import canonical_label, map_rooms
from .shelfrank import rank, score_shelves
from .sightseeing import build_shelves as build_ss_shelves, diff_chips, LABELS as SS_LABELS
from .synth.sightseeing import ATTRACTIONS, SS_SUPPLIERS, generate_sightseeing
from .synth.suppliers import SUPPLIERS, generate_booking_log, generate_offers, generate_supplier_feeds, to_dicts
from .synth.world import generate_hotels

CITY_ORDER = ["DXB", "BKK", "PAR"]


def _canonical_name(recs: list[dict], tokfreq: Counter | None = None) -> str:
    """Display name for a merged hotel: the spelling most suppliers agree on,
    written the way a person would write it (not ALL CAPS, accents kept,
    no city suffix or star rating glued on)."""
    import re
    from rapidfuzz import fuzz
    from .normalize import ABBREV, fold

    cands = []
    for r in recs:
        n = r["name"]
        n = re.sub(r"\s+-\s+" + re.escape(CITIES[r["city"]]["name"]) + r"$", "", n)
        n = re.sub(r"\s*\d(\.\d)?\s*\*$", "", n).strip()
        key = " ".join(ABBREV.get(t, t) for t in re.findall(r"[a-z0-9&]+", fold(n)))
        cands.append({"name": n, "key": key, "upper": n.isupper(), "accents": sum(ord(ch) > 127 for ch in n),
                      "by": " by " in n})
    freq = Counter(c["key"] for c in cands)

    import math as _m

    def spelled_right(c):
        # typos produce tokens nobody else uses; real words recur across the catalogue
        toks = c["key"].split()
        return sum(_m.log(1 + (tokfreq or {}).get(t, 0)) for t in toks) / max(1, len(toks))

    def score(c):
        closeness = sum(fuzz.ratio(c["key"], o["key"]) for o in cands) / len(cands)
        return (freq[c["key"]], round(spelled_right(c), 2), not c["upper"], not c["by"], c["accents"], closeness)

    best = max(cands, key=score)
    if best["upper"]:
        # every supplier shouts: rebuild a readable form from the majority key
        return " ".join(w if w in ("&",) else w.capitalize() for w in best["key"].split())
    return best["name"]


def _match_city(D: dict, test: str, thresholds) -> dict:
    tr = [c for c in D if c != test]
    model = HotelMatcher().fit(np.vstack([D[c]["X"] for c in tr]), np.concatenate([D[c]["y"] for c in tr]))
    R, cands, X, y = D[test]["R"], D[test]["cands"], D[test]["X"], D[test]["y"]
    p = model.predict_proba(X)
    labels = cluster(R, cands, p, thresholds.auto_merge)
    truth = [r["true_hotel_id"] for r in R]
    review = (p >= thresholds.review_floor) & (p < thresholds.auto_merge)
    p_h = p.copy()
    p_h[review] = y[review].astype(float)  # what the clusters look like after reviewers decide
    labels_h = cluster(R, cands, p_h, thresholds.auto_merge)
    base = baseline_rule_cluster(R)
    return {"model": model, "p": p, "labels": labels, "review_mask": review,
            "eval": {"auto": pairwise_prf(labels, truth), "auto_exact": exact_cluster_rate(labels, truth),
                     "with_review": pairwise_prf(labels_h, truth), "with_review_exact": exact_cluster_rate(labels_h, truth),
                     "baseline": pairwise_prf(base, truth), "baseline_exact": exact_cluster_rate(base, truth),
                     "listings": listing_counts(labels, truth), "baseline_listings": len(set(base)),
                     "review_pairs": int(review.sum()), "candidate_pairs": len(cands),
                     "blocking_recall": float(y.sum()) / max(1, sum(len(v) * (len(v) - 1) // 2 for v in _groups(truth).values())),
                     "coords_repaired": int(sum(r["_coord_fixed"] for r in R))}}


def _groups(labels):
    g = defaultdict(list)
    for i, l in enumerate(labels):
        g[l].append(i)
    return g


def run(cfg: Config = DEFAULT, seed: int = 7) -> dict:
    t0 = time.time()
    hotels = generate_hotels(seed=seed)
    hrecs, rrecs = generate_supplier_feeds(hotels, seed=seed + 4)
    hrecs, rrecs = to_dicts(hrecs), to_dicts(rrecs)
    truth_hotel = {h.hotel_id: h for h in hotels}
    rel = ledger(generate_booking_log(seed=seed + 24))

    # ---------------------------------------------------------- hotel identity
    D = {}
    for c in CITY_ORDER:
        R = prepare_all([r for r in hrecs if r["city"] == c])
        cands, _ = build_candidates(R)
        X = np.array([cd.feats for cd in cands])
        y = np.array([int(R[cd.a]["true_hotel_id"] == R[cd.b]["true_hotel_id"]) for cd in cands])
        D[c] = {"R": R, "cands": cands, "X": X, "y": y}
    t_match = time.time()
    M = {c: _match_city(D, c, cfg.match) for c in CITY_ORDER}
    t_match = time.time() - t_match

    cluster_of = {}
    for c in CITY_ORDER:
        for r, lab in zip(D[c]["R"], M[c]["labels"]):
            cluster_of[r["rec_id"]] = f"{c}-L{lab:04d}"

    # ---------------------------------------------------------- rooms
    room_key, dq, parsed = map_rooms(rrecs, cluster_of)
    room_truth = [r["true_room_id"] for r in rrecs]
    room_eval = pairwise_prf([room_key[r["rec_id"]] for r in rrecs], room_truth)
    by_cluster_beds = defaultdict(set)
    for r in rrecs:
        p = parsed[r["rec_id"]]
        if p["bed"]:
            by_cluster_beds[room_key[r["rec_id"]]].add(p["bed"])

    out = {"config": cfg.to_dict(), "suppliers": {k: {"name": v["name"], "pay_later": v["pay_later"]} for k, v in SUPPLIERS.items()},
           "cities": {c: CITIES[c]["name"] for c in CITY_ORDER}, "reliability": rel, "data_quality": dq,
           "feature_labels": FEATURE_LABELS, "search": {}, "review": [], "evidence": {}}

    # ---------------------------------------------------------- per-city search
    from .normalize import ABBREV as _AB, fold as _fold
    import re as _re
    tokfreq = Counter(_AB.get(t, t) for r in hrecs for t in _re.findall(r"[a-z0-9&]+", _fold(r["name"])))
    for c in CITY_ORDER:
        offers = generate_offers(hotels, hrecs, rrecs, c, cfg.nights, seed=seed + 16 + CITY_ORDER.index(c))
        listings = defaultdict(list)
        for r in D[c]["R"]:
            listings[cluster_of[r["rec_id"]]].append(r)
        shelves = []
        headline_not_best = 0
        raw_cards = 0
        room_cmp = {"rooms_multi_offer": 0, "cheapest_not_best": 0, "l4l_gap_sum": 0.0}
        for lid, recs in listings.items():
            loffers = [o for o in offers if cluster_of[o["hotel_rec_id"]] == lid]
            if not loffers:
                continue
            raw_cards += len({o["hotel_rec_id"] for o in loffers})
            stars = int(round(median([r["stars"] for r in recs if r["stars"] is not None] or [3])))
            true_ids = Counter(r["true_hotel_id"] for r in recs)
            th = truth_hotel[true_ids.most_common(1)[0][0]]  # content fields a content team would hold (area, reviews)
            rooms = defaultdict(list)
            for o in loffers:
                rk = room_key[o["room_rec_id"]]
                relx = rel.get(f"{o['supplier']}|{c}")
                comp = l4l(o, stars, relx, cfg.l4l, cfg.occupancy_adults, cfg.nights, cfg.lead_days)
                p_fail = relx["p_any_failure"] if relx else 0.03
                rooms[rk].append({
                    "id": o["offer_id"], "sup": o["supplier"], "raw": o["raw_room_name"], "board": o["board"],
                    "cancel": o["cancel_free_until_days"], "paylater": o["pay_later"], "sell": o["sell_inr"], "net": o["net_inr"],
                    "l4l": comp, "p_fail": round(p_fail, 4), "leaks": parsed[o["room_rec_id"]]["rate_leaks"],
                })
            room_list = []
            for rk, ros in rooms.items():
                p0 = parsed[[o for o in loffers if room_key[o["room_rec_id"]] == rk][0]["room_rec_id"]]
                ros.sort(key=lambda x: x["l4l"]["l4l"])
                room_list.append({"key": rk, "label": canonical_label(p0, by_cluster_beds[rk]), "room_class": p0["room_class"],
                                  "view": p0["view"], "suppliers": sorted({x["sup"] for x in ros}), "offers": ros,
                                  "best_l4l": ros[0]["l4l"]["l4l"], "min_sell": min(x["sell"] for x in ros)})
            for r in room_list:
                if len(r["offers"]) >= 2:
                    room_cmp["rooms_multi_offer"] += 1
                    ch = min(r["offers"], key=lambda x: (x["sell"], x["l4l"]["l4l"]))
                    if ch["id"] != r["offers"][0]["id"] and ch["l4l"]["l4l"] > r["offers"][0]["l4l"]["l4l"]:
                        room_cmp["cheapest_not_best"] += 1
                        room_cmp["l4l_gap_sum"] += ch["l4l"]["l4l"] - r["offers"][0]["l4l"]["l4l"]
            room_list.sort(key=lambda r: r["best_l4l"])
            all_offers = [o for r in room_list for o in r["offers"]]
            best = min(all_offers, key=lambda x: x["l4l"]["l4l"])
            cheapest = min(all_offers, key=lambda x: x["sell"])
            if cheapest["id"] != best["id"] and cheapest["l4l"]["l4l"] > best["l4l"]["l4l"]:
                headline_not_best += 1
            best_room = next(r for r in room_list if any(o["id"] == best["id"] for o in r["offers"]))
            shelves.append({
                "id": lid, "name": _canonical_name(recs, tokfreq), "stars": stars, "area": th.area, "lat": round(median(r["_lat"] for r in recs), 5),
                "lon": round(median(r["_lon"] for r in recs), 5), "review_score": th.review_score, "content_score": th.content_score,
                "platinum": th.platinum, "chain": next((r["chain"] for r in recs if r["chain"]), None),
                "records": [{"rec": r["rec_id"], "sup": r["supplier"], "name": r["name"], "stars": r["stars"], "addr": r["address"],
                             "phone": r["phone"], "lat": r["lat"], "lon": r["lon"], "fixed": r["_coord_fixed"]} for r in recs],
                "suppliers": sorted({r["supplier"] for r in recs}), "rooms": room_list, "n_offers": len(all_offers),
                "cheapest": {"id": cheapest["id"], "sell": cheapest["sell"], "l4l": cheapest["l4l"]["l4l"], "sup": cheapest["sup"]},
                "best": {"id": best["id"], "sup": best["sup"], "sell": best["sell"], "l4l": best["l4l"]["l4l"],
                         "l4l_per_night": best["l4l"]["l4l"] / cfg.nights, "room": best_room["label"], "p_fail": best["p_fail"],
                         "exp_gp": round((best["sell"] - best["net"]) * (1 - best["p_fail"]))},
                "true_ids": sorted(true_ids),
            })
        for i, sh in enumerate(shelves):
            sh["ord"] = i
        shelves = rank(score_shelves(shelves, cfg.rank), cfg.rank)

        # baseline listing for contrast: every supplier record is its own card, cheapest headline first
        raw = []
        for r in D[c]["R"]:
            ro = [o for o in offers if o["hotel_rec_id"] == r["rec_id"]]
            if ro:
                cheap = min(ro, key=lambda o: o["sell_inr"])
                raw.append({"rec": r["rec_id"], "sup": r["supplier"], "name": r["name"], "stars": r["stars"], "sell": cheap["sell_inr"],
                            "board": cheap["board"], "cancel": cheap["cancel_free_until_days"], "room": cheap["raw_room_name"],
                            "listing": cluster_of[r["rec_id"]]})
        raw.sort(key=lambda x: x["sell"])

        out["search"][c] = {"shelves": shelves, "raw": raw, "n_offers": len(offers), "raw_cards": raw_cards,
                            "headline_not_best": headline_not_best, "room_compare": room_cmp}

        # ---------------------------------------------------------- review queue
        R, cands, p, mask = D[c]["R"], D[c]["cands"], M[c]["p"], M[c]["review_mask"]
        value_by_rec = defaultdict(float)
        for o in offers:
            value_by_rec[o["hotel_rec_id"]] += o["sell_inr"]
        for i in np.where(mask)[0]:
            cd = cands[i]
            a, b = R[cd.a], R[cd.b]
            out["review"].append({
                "pair": f"{a['rec_id']}~{b['rec_id']}", "city": c, "p": round(float(p[i]), 3),
                "gtv_at_risk": round(value_by_rec[a["rec_id"]] + value_by_rec[b["rec_id"]]),
                "a": {k: a[k] for k in ("rec_id", "supplier", "name", "stars", "address", "phone", "lat", "lon")},
                "b": {k: b[k] for k in ("rec_id", "supplier", "name", "stars", "address", "phone", "lat", "lon")},
                "distance_m": round(10 ** cd.feats[FEATURES.index("log_dist")] - 1),
                "why": M[c]["model"].explain(cd.feats, top=6),
                "truth_same": a["true_hotel_id"] == b["true_hotel_id"],  # used only to score reviewer answers in the demo
            })
        out["evidence"][c] = M[c]["eval"]
    out["review"].sort(key=lambda r: -r["gtv_at_risk"])

    # ---------------------------------------------------------- sightseeing
    prods = generate_sightseeing(seed=seed + 34)
    ss = build_ss_shelves(prods)
    ss_truth = {p["product_id"]: p["true_variant"] for p in prods}
    lab = {}
    for i, s in enumerate(ss):
        for o in s["offers"]:
            lab[o["product_id"]] = i
    ss_eval = pairwise_prf([lab[p["product_id"]] for p in prods], [ss_truth[p["product_id"]] for p in prods])
    attr_acc = sum(1 for s in ss for o in s["offers"] if o["attraction"] == o["true_attraction"]) / len(prods)
    ss_out = {}
    for c in CITY_ORDER:
        for attr_id, name, _, _ in ATTRACTIONS[c]:
            variants = [s for s in ss if s["attraction"] == attr_id]
            variants.sort(key=lambda s: s["core_price"])
            ref = variants[0]["atoms"] if variants else None
            ss_out[attr_id] = {"name": name, "city": c, "n_products": sum(len(v["offers"]) for v in variants),
                               "variants": [{"atoms": v["atoms"], "offers": [{k: o[k] for k in ("product_id", "supplier", "title", "price_inr", "duration_h", "cancellation")} for o in v["offers"]],
                                             "best_price": v["best_price"], "inclusion_value": v["inclusion_value"], "core_price": v["core_price"],
                                             "chips": diff_chips(ref, v["atoms"]) if ref else []} for v in variants]}
    out["sightseeing"] = {"attractions": ss_out, "suppliers": SS_SUPPLIERS, "labels": SS_LABELS}

    # ---------------------------------------------------------- evidence summary
    out["evidence"]["rooms"] = room_eval
    out["evidence"]["sightseeing"] = {"variant_pairs": ss_eval, "attraction_accuracy": attr_acc, "products": len(prods),
                                      "shelves": len(ss)}
    out["evidence"]["runtime_s"] = {"matching_all_cities": round(t_match, 2), "total": round(time.time() - t0, 2)}
    out["evidence"]["world"] = {"hotels": len(hotels), "supplier_hotel_records": len(hrecs), "supplier_room_records": len(rrecs)}
    return out

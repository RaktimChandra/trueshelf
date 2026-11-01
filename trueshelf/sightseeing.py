"""Sightseeing: same attraction is not the same product.

Each supplier product is resolved to an attraction (from a point-of-interest
master list with aliases) and decomposed into "experience atoms": access type,
transfer, meal, guide, private/shared, cancellation. Products with identical
atoms are merged into one shelf entry; products that differ keep their own
entry with explicit difference chips.
"""
from __future__ import annotations

import re
from collections import defaultdict

from rapidfuzz import fuzz

from .normalize import fold
from .synth.sightseeing import ATTRACTIONS

ATOM_RULES = {
    "access": [("skip_line", r"skip.the.line|fast track|priority"), ("prime", r"prime|sunset slot|peak"),
               ("premium", r"premium|vip|summit")],
    "transfer": [("private", r"private (transfer|car|4x4)"), ("shared", r"pickup|shared transfer|sharing transfer|return transfer")],
    "meal": [("dinner", r"dinner"), ("lunch", r"\blunch\b"), ("snacks", r"refreshment|snack")],
    "guide": [("live", r"guided|live guide|with guide"), ("audio", r"audio")],
}
INCLUSION_VALUE_INR = {  # what an inclusion is worth when comparing prices (editable assumption)
    ("transfer", "shared"): 650, ("transfer", "private"): 1300, ("meal", "dinner"): 2100, ("meal", "snacks"): 700,
    ("meal", "lunch"): 1400, ("guide", "live"): 500,
}
LABELS = {"skip_line": "Skip-the-line", "prime": "Prime-time slot", "premium": "Premium level", "general": "General entry",
          "shared": "Shared transfer", "private": "Private transfer", "none": "—", "dinner": "Dinner", "lunch": "Lunch",
          "snacks": "Snacks", "live": "Live guide", "audio": "Audio guide"}


def resolve_attraction(title: str, city: str) -> tuple[str | None, float]:
    t = fold(title)
    best, score = None, 0.0
    for attr_id, name, aliases, _ in ATTRACTIONS[city]:
        for a in [name] + aliases:
            s = fuzz.partial_ratio(fold(a), t) / 100 if len(a) > 4 else (1.0 if re.search(rf"\b{re.escape(fold(a))}\b", t) else 0)
            # longer aliases are more specific evidence
            s *= min(1.0, 0.75 + len(a) / 60)
            if s > score:
                best, score = attr_id, s
    return (best, round(score, 3)) if score >= 0.72 else (None, round(score, 3))


def atoms(p: dict) -> dict:
    t = fold(p["title"])
    a = {"access": "general", "transfer": "none", "meal": "none", "guide": "none"}
    for k, rules in ATOM_RULES.items():
        for val, pat in rules:
            if re.search(pat, t):
                a[k] = val
                break
    a["private"] = a["transfer"] == "private" or "private tour" in t
    c = fold(p.get("cancellation") or "")
    a["cancel_24h"] = not ("non-refundable" in t or "non-refundable" in c or c == "nr")
    return a


def build_shelves(products: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for p in products:
        attr, conf = resolve_attraction(p["title"], p["city"])
        a = atoms(p)
        p2 = {**p, "attraction": attr, "attraction_conf": conf, "atoms": a}
        key = (attr, a["access"], a["transfer"], a["meal"], a["guide"], a["private"], a["cancel_24h"])
        groups[key].append(p2)
    shelves = []
    for key, items in groups.items():
        inc_value = sum(INCLUSION_VALUE_INR.get((k, items[0]["atoms"][k]), 0) for k in ("transfer", "meal", "guide"))
        best = min(items, key=lambda x: x["price_inr"])
        shelves.append({"key": "|".join(map(str, key)), "attraction": key[0], "city": items[0]["city"], "atoms": items[0]["atoms"],
                        "offers": sorted(items, key=lambda x: x["price_inr"]), "best_price": best["price_inr"],
                        "inclusion_value": inc_value, "core_price": best["price_inr"] - inc_value})
    return shelves


def diff_chips(a: dict, b: dict) -> list[str]:
    """Plain-language differences between two products of the same attraction."""
    chips = []
    for k in ("access", "transfer", "meal", "guide"):
        if a[k] != b[k]:
            chips.append(f"{LABELS.get(b[k], b[k])} vs {LABELS.get(a[k], a[k])}")
    if a["private"] != b["private"]:
        chips.append("Private group" if b["private"] else "Shared group")
    if a["cancel_24h"] != b["cancel_24h"]:
        chips.append("Free cancellation" if b["cancel_24h"] else "Non-refundable")
    return chips

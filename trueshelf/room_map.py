"""Layer 2a of TrueShelf: "Is this the same room?"

Room names are parsed with a small deterministic grammar into canonical
attributes (class, bed, view, balcony). Rate-plan words that suppliers leak into
room names ("Breakfast Included", "NRF") are stripped and reported as a data
quality issue for that supplier rather than silently creating a new "room".
"""
from __future__ import annotations

import re
from collections import defaultdict

from .normalize import fold

CLASS_PATTERNS = [
    ("Junior Suite", r"\b(jr\.?\s*ste|junior\s+suite|jr\.?\s*suite)\b"),
    ("Family Room", r"\b(fam|family)\b"),
    ("Executive", r"\b(exec|executive)\b"),
    ("Premier", r"\b(prm|premier|premium)\b"),
    ("Deluxe", r"\b(dlx|deluxe|delux)\b"),
    ("Superior", r"\b(sup|superior)\b"),
    ("Standard", r"\b(std|standard|classic)\b"),
    ("Studio", r"\b(stu|studio)\b"),
    ("Suite", r"\b(ste|suite)\b"),
]
BED_PATTERNS = [
    ("Twin", r"\b(twn|twin|2\s*twin|two\s*beds?)\b"),
    ("King", r"\b(king|kg)\b"),
    ("Queen", r"\b(queen|qn)\b"),
    ("Double", r"\b(dbl|double)\b"),
]
VIEW_PATTERNS = [
    ("Eiffel Tower", r"eiffel\s*tower\s*(vw|view)|eiffeltowerview|eiffel\s*(vw|view)?"), ("Sea", r"\b(sea|ocean)\s*(vw|view)?|seaview"), ("Marina", r"\b(marina|mar)\s*(vw|view)|marinaview"),
    ("Creek", r"\b(creek|crk)\s*(vw|view)?|creekview"), ("River", r"\b(river|riv)\s*(vw|view)?|riverview"),
    ("Pool", r"\bpool\s*(vw|view)?|poolview"), ("Garden", r"\b(garden|gdn)\s*(vw|view)?|gardenview"),
    ("Courtyard", r"\b(crtyd|courtyard)\b|courtyardview"), ("Street", r"\bstreet\b|streetview"), ("City", r"\bcity\s*(vw|view)?|cityview"),
]
# Words that carry no room information once class/bed/view are read.
FILLER = {"room", "rooms", "bed", "beds", "with", "and", "the", "1", "2", "one", "two", "view", "vw", "balc", "balcony", "a"}

RATE_LEAKS = [
    ("breakfast", r"\b(bb|breakfast\s+included|with\s+breakfast|b&b)\b"), ("room_only", r"\b(ro|room\s+only)\b"),
    ("non_refundable", r"\b(nrf|non[\s-]?refundable)\b"), ("promo", r"\(?\bpromo\)?"),
]


def parse_room(raw: str) -> dict:
    s = fold(raw).replace(",", " ").replace("-", " ").replace("&", " and ")
    leaks = []
    for name, pat in RATE_LEAKS:
        if re.search(pat, s):
            leaks.append(name)
            s = re.sub(pat, " ", s)
    cls = bed = view = None
    for c, pat in CLASS_PATTERNS:
        if re.search(pat, s):
            cls = c
            s = re.sub(pat, " ", s, count=1)
            break
    for b, pat in BED_PATTERNS:
        if re.search(pat, s):
            bed = b
            s = re.sub(pat, " ", s, count=1)
            break
    for v, pat in VIEW_PATTERNS:
        if re.search(pat, s):
            view = v
            s = re.sub(pat, " ", s, count=1)
            break
    balcony = bool(re.search(r"\b(balc|balcony)\b", s))
    # Anything left that we could not read might change the product ("Côté Cour", "Club").
    residual = [t for t in re.findall(r"[a-z0-9]+", s) if t not in FILLER]
    found = sum(x is not None for x in (cls, bed)) + 1
    return {"room_class": cls, "bed": bed, "bed_bucket": None if bed is None else ("TWO" if bed == "Twin" else "ONE"),
            "view": view, "balcony": balcony, "rate_leaks": leaks, "residual": residual,
            "parse_conf": round(found / 3, 2) if not residual else 0.0}


def map_rooms(room_recs: list[dict], hotel_cluster_of: dict) -> tuple[dict, dict]:
    """Group supplier room records into canonical rooms inside each hotel listing.

    Returns (room_rec_id -> canonical_room_key, supplier -> data-quality stats).
    Balcony is shown to the agent but not used as a grouping key, because some
    suppliers never mention it (absence is "unknown", not "no").
    """
    parsed = {r["rec_id"]: parse_room(r["raw_name"]) for r in room_recs}
    dq = defaultdict(lambda: {"rooms": 0, "rate_words_in_room_name": 0, "unparsed_class": 0, "ambiguous_bed": 0, "unmapped": 0})
    groups: dict = {}
    out = {}
    for r in room_recs:
        p = parsed[r["rec_id"]]
        d = dq[r["supplier"]]
        d["rooms"] += 1
        d["rate_words_in_room_name"] += bool(p["rate_leaks"])
        d["unparsed_class"] += p["room_class"] is None
        d["ambiguous_bed"] += p["bed"] == "Double"
        hc = hotel_cluster_of[r["hotel_rec_id"]]
        if p["room_class"] is None or p["bed"] is None or p["residual"]:
            # Fail safe: a name we cannot fully read is never grouped with anything.
            # It stays a room of its own, flagged for a person to map.
            d["unmapped"] += 1
            key = (hc, "UNMAPPED", r["rec_id"], None)
        else:
            key = (hc, p["room_class"], p["bed_bucket"], p["view"])
        groups.setdefault(key, []).append(r["rec_id"])
        out[r["rec_id"]] = "|".join(str(x) for x in key)
    return out, {k: dict(v) for k, v in dq.items()}, parsed


def canonical_label(p: dict, known_beds: set[str]) -> str:
    """Human label for a canonical room, using the most specific bed any supplier gave."""
    bed = p["bed"]
    if p["bed_bucket"] == "ONE":
        spec = [b for b in ("King", "Queen") if b in known_beds]
        bed = spec[0] if spec else "Double"
    parts = [p["room_class"] or "Room"]
    if bed:
        parts.append(f"· {bed}")
    if p["view"]:
        parts.append(f"· {p['view']} view")
    return " ".join(parts)

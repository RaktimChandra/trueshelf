"""Deterministic cleaning of supplier hotel records.

Rules live in code (cheap, testable, explainable); learning is reserved for the
pairwise decision where the rules run out.
"""
from __future__ import annotations

import math
import re
import unicodedata

from .config import CITIES

ABBREV = {"htl": "hotel", "stes": "suites", "ste": "suites", "apts": "apartments", "apt": "apartments",
          "rst": "resort", "res": "residence", "btq": "boutique", "intl": "international", "grd": "grand",
          "gdn": "garden", "twr": "tower", "st": "saint", "ste.": "sainte"}
# Transliteration families collapse to one canonical spelling.
TRANSLIT = {"el": "al", "kasr": "qasr", "ban": "baan", "chaophraya": "chao phraya", "sukhumwit": "sukhumvit",
            "safron": "saffron", "zafaran": "zaafaran", "beit": "bayt", "nur": "noor", "sayam": "siam",
            "harbor": "harbour", "theater": "theatre"}
# Words that describe the *kind* of property. They are not noise: a "Suites"
# and a "Hotel" with the same core name 150 m apart are usually different
# buildings, so these are kept aside and compared explicitly.
TYPE_TOKENS = {"hotel", "suites", "resort", "spa", "apartments", "boutique", "inn", "grand", "residence",
               "annexe", "residences", "hostel", "villa", "lodge", "rive", "gauche"}
STOP = {"the", "and", "by", "de", "des", "du", "la", "le", "les", "of", "&", "a"}
STREET_ABBR = {"rd": "road", "st": "street", "bd": "boulevard", "blvd": "boulevard", "av": "avenue", "ave": "avenue"}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", fold(s))


def _repair_type_typo(t: str) -> str:
    """Supplier typos inside property-type words ("Hoel", "Rsort", "Garnd") would
    otherwise erase the Suites-vs-Hotel signal, so repair them deterministically."""
    from rapidfuzz.distance import OSA
    if len(t) < 4 or t in TYPE_TOKENS:
        return t
    for w in sorted(TYPE_TOKENS):
        if len(w) >= 4 and abs(len(w) - len(t)) <= 1 and OSA.distance(t, w) <= 1:
            return w
    return t


def clean_name(name: str, city_code: str) -> dict:
    """Return core tokens, type tokens and a canonical string for a hotel name."""
    city_name = fold(CITIES[city_code]["name"])
    s = fold(name)
    s = re.sub(r"\b\d(\.\d)?\s*(\*+|stars?\b)", " ", s)  # "4*", "4 star"
    s = re.sub(r"\s-\s" + re.escape(city_name) + r"\b", " ", s)  # "X - Dubai"
    s = s.replace("&", " and ")
    raw = re.findall(r"[a-z0-9]+", s)
    out: list[str] = []
    for t in raw:
        t = ABBREV.get(t, t)
        t = TRANSLIT.get(t, t)
        t = _repair_type_typo(t)
        out.extend(t.split())
    core = [t for t in out if t not in TYPE_TOKENS and t not in STOP and t != city_name]
    types = sorted({t for t in out if t in TYPE_TOKENS})
    return {"core": core, "types": types, "core_str": " ".join(core), "core_sorted": " ".join(sorted(core))}


def phone_key(phone: str | None) -> str | None:
    if not phone:
        return None
    d = re.sub(r"\D", "", phone)
    return d[-7:] if len(d) >= 7 else None


def address_parts(addr: str | None) -> dict:
    if not addr:
        return {"no": None, "street": []}
    t = tokens(addr)
    no = None
    m = re.match(r"\s*(\d{1,4})\s", addr)
    if m:
        no = int(m.group(1))
    street = [STREET_ABBR.get(x, x) for x in t if not x.isdigit() and x not in ("p", "o", "box")]
    return {"no": no, "street": street}


def repair_coords(lat: float, lon: float, city_code: str) -> tuple[float, float, bool]:
    """Fix the swapped-lat/lon bug when swapping lands inside the city."""
    c = CITIES[city_code]
    if haversine(lat, lon, c["lat"], c["lon"]) > 80_000 and haversine(lon, lat, c["lat"], c["lon"]) < 80_000:
        return lon, lat, True
    return lat, lon, False


def haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def prepare(rec: dict) -> dict:
    """Attach normalized fields to a supplier hotel record (dict)."""
    n = clean_name(rec["name"], rec["city"])
    lat, lon, fixed = repair_coords(rec["lat"], rec["lon"], rec["city"])
    a = address_parts(rec.get("address"))
    return {**rec, "_core": n["core"], "_types": n["types"], "_core_str": n["core_str"], "_core_sorted": n["core_sorted"],
            "_lat": lat, "_lon": lon, "_coord_fixed": fixed, "_phone": phone_key(rec.get("phone")),
            "_street_no": a["no"], "_street": a["street"]}

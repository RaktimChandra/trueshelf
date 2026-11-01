"""Synthetic sightseeing feeds from three suppliers, with ground-truth product atoms."""
from __future__ import annotations

import random

ATTRACTIONS = {
    "DXB": [
        ("dxb-burj", "Burj Khalifa observation deck", ["burj khalifa", "at the top", "burj"], 4800),
        ("dxb-safari", "Red-dune desert safari", ["desert safari", "dune bashing", "safari"], 3900),
        ("dxb-frame", "Dubai Frame", ["dubai frame", "frame"], 1300),
        ("dxb-dhow", "Marina dhow cruise", ["dhow cruise", "dhow", "marina cruise"], 2600),
        ("dxb-motf", "Museum of the Future", ["museum of the future", "motf"], 3400),
    ],
    "BKK": [
        ("bkk-palace", "Grand Palace & Wat Phra Kaew", ["grand palace", "wat phra kaew", "emerald buddha"], 1900),
        ("bkk-cruise", "Chao Phraya river dinner cruise", ["chao phraya", "river cruise", "dinner cruise"], 2800),
        ("bkk-float", "Damnoen Saduak floating market", ["floating market", "damnoen saduak"], 2300),
        ("bkk-ayut", "Ayutthaya day trip", ["ayutthaya", "ancient capital"], 3600),
        ("bkk-sky", "Mahanakhon SkyWalk", ["mahanakhon", "skywalk", "king power"], 2100),
    ],
    "PAR": [
        ("par-eiffel", "Eiffel Tower", ["eiffel tower", "eiffel", "tour eiffel"], 4200),
        ("par-louvre", "Louvre Museum", ["louvre", "mona lisa"], 3300),
        ("par-seine", "Seine river cruise", ["seine", "bateaux", "river cruise"], 2100),
        ("par-versailles", "Palace of Versailles day trip", ["versailles", "chateau de versailles"], 6800),
        ("par-montmartre", "Montmartre walking tour", ["montmartre", "sacre coeur", "sacré-cœur"], 2500),
    ],
}

ACCESS = {"general": 0, "prime": 0.35, "skip_line": 0.25, "premium": 1.1}
TRANSFER = {"none": 0, "shared": 1, "private": 2}
MEAL = {"none": 0, "snacks": 1, "lunch": 2, "dinner": 3}
GUIDE = {"none": 0, "audio": 1, "live": 2}

SS_SUPPLIERS = {"ATX": "Atlas Experiences", "TGR": "TourGrid", "LLP": "LocalLoop"}


def _variants(attr_id: str, rng: random.Random) -> list[dict]:
    """Ground-truth product variants that exist in the market for one attraction."""
    out = []
    base = {"access": "general", "transfer": "none", "meal": "none", "guide": "none", "private": False, "cancel_24h": True}
    combos = [dict(base), {**base, "transfer": "shared"}, {**base, "access": "skip_line", "guide": "live"},
              {**base, "access": "prime"}, {**base, "transfer": "private", "private": True, "guide": "live"},
              {**base, "meal": "dinner", "transfer": "shared"}, {**base, "access": "premium", "meal": "snacks"},
              {**base, "cancel_24h": False}]
    if "safari" in attr_id or "cruise" in attr_id or "dhow" in attr_id:
        combos = [{**base, "transfer": "shared", "meal": "dinner"}, {**base, "transfer": "private", "meal": "dinner", "private": True},
                  {**base, "transfer": "none", "meal": "dinner"}, {**base, "transfer": "shared", "meal": "none"},
                  {**base, "transfer": "shared", "meal": "dinner", "access": "premium"}, {**base, "transfer": "shared", "meal": "dinner", "cancel_24h": False}]
    rng.shuffle(combos)
    for i, c in enumerate(combos[: rng.randint(4, len(combos))]):
        dur = {"none": 0, "shared": 1.0, "private": 1.0}[c["transfer"]] + (2.5 if "trip" in attr_id or "ayut" in attr_id or "versailles" in attr_id or "float" in attr_id else 1.5)
        if c["meal"] == "dinner":
            dur += 1.5
        out.append({**c, "duration_h": round(dur * 2) / 2, "variant_id": f"{attr_id}-V{i + 1}"})
    return out


def _title(sup: str, attr_name: str, aliases: list[str], v: dict, rng: random.Random) -> str:
    alias = rng.choice([attr_name] + aliases[:2]).title() if sup != "ATX" else attr_name
    bits = []
    if v["access"] == "skip_line":
        bits.append(rng.choice(["Skip-the-Line", "Fast Track", "Priority Entry"]))
    if v["access"] == "prime":
        bits.append(rng.choice(["Prime Hours", "Sunset Slot", "Peak-Time"]))
    if v["access"] == "premium":
        bits.append(rng.choice(["Premium", "VIP", "Summit Level"]))
    inc = []
    if v["transfer"] == "shared":
        inc.append(rng.choice(["Hotel Pickup", "Shared Transfers", "Sharing Transfer", "Return Transfers"]))
    if v["transfer"] == "private":
        inc.append(rng.choice(["Private Transfer", "Private Car", "Private 4x4"]))
    if v["meal"] == "dinner":
        inc.append(rng.choice(["BBQ Dinner", "Buffet Dinner", "Dinner Included", "with Dinner"]))
    if v["meal"] == "snacks":
        inc.append(rng.choice(["Refreshments", "Snacks & Coffee"]))
    if v["meal"] == "lunch":
        inc.append("Lunch")
    if v["guide"] == "live":
        inc.append(rng.choice(["Guided Tour", "Live Guide", "with Guide"]))
    if v["private"] and v["transfer"] != "private":
        inc.append("Private Tour")
    if sup == "ATX":
        t = f"{alias}: {' '.join(bits)} Ticket".replace(":  Ticket", ": Entry Ticket").replace(":  ", ": ")
        if inc:
            t += " with " + " & ".join(inc)
    elif sup == "TGR":
        t = f"{' '.join(bits)} {alias}" + (f" (incl. {', '.join(inc)})" if inc else " Admission")
    else:
        t = f"{alias} – {' / '.join(bits + inc) or 'Standard Entry'}"
    if not v["cancel_24h"] and rng.random() < 0.5:
        t += " [Non-Refundable]"
    return " ".join(t.split())


def generate_sightseeing(seed: int = 41):
    rng = random.Random(seed)
    products = []
    for city, attrs in ATTRACTIONS.items():
        for attr_id, name, aliases, base_price in attrs:
            for v in _variants(attr_id, rng):
                for sup in SS_SUPPLIERS:
                    if rng.random() < 0.3:
                        continue
                    price = base_price * (1 + ACCESS[v["access"]]) + 650 * TRANSFER[v["transfer"]] + 700 * MEAL[v["meal"]] \
                        + 500 * GUIDE[v["guide"]] + (1500 if v["private"] else 0)
                    price *= rng.uniform(0.88, 1.12) * (0.93 if not v["cancel_24h"] else 1.0)
                    products.append({
                        "product_id": f"{sup}-{len(products) + 1:04d}", "supplier": sup, "city": city,
                        "title": _title(sup, name, aliases, v, rng),
                        "duration_h": v["duration_h"] if sup != "LLP" else None,  # LocalLoop omits structured duration
                        "cancellation": ("Free cancellation up to 24h" if v["cancel_24h"] else "Non-refundable") if sup != "TGR" else
                                        ("24h" if v["cancel_24h"] else "NR"),
                        "price_inr": round(price / 10) * 10,
                        "true_attraction": attr_id, "true_variant": v["variant_id"],
                    })
    return products

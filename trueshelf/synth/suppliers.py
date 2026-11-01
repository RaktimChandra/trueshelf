"""Supplier feeds: how five fictional suppliers describe, price and fulfil the same hotels."""
from __future__ import annotations

import random
from dataclasses import dataclass, asdict

from .world import Hotel, Room, offset, strip_accents

ABBREV = {"Hotel": "HTL", "Suites": "STES", "Apartments": "APTS", "Resort": "RST", "Residence": "RES",
          "Boutique": "BTQ", "International": "INTL", "Grand": "GRD", "Garden": "GDN", "Tower": "TWR"}
TRANSLIT = [("Al ", "El "), ("Qasr", "Kasr"), ("Baan", "Ban"), ("Chao Phraya", "Chaophraya"), ("Sukhumvit", "Sukhumwit"),
            ("Saffron", "Safron"), ("Zaafaran", "Zafaran"), ("Bayt", "Beit"), ("Noor", "Nur"), ("Siam", "Sayam"),
            ("Saint", "St"), ("Hôtel", "Hotel"), ("Harbour", "Harbor"), ("Theatre", "Theater")]

SUPPLIERS = {
    # code: display name, cities covered with coverage share, price bias, markup TBO earns, pay-later support
    "ATL": {"name": "Atlas Beds", "cover": {"DXB": 0.82, "BKK": 0.78, "PAR": 0.85}, "bias": 1.00, "markup": 0.085, "pay_later": True},
    "MER": {"name": "Meridian Wholesale", "cover": {"DXB": 0.74, "BKK": 0.70, "PAR": 0.80}, "bias": 0.94, "markup": 0.10, "pay_later": False},
    "BLU": {"name": "BlueRoute", "cover": {"DXB": 0.66, "BKK": 0.72, "PAR": 0.62}, "bias": 0.98, "markup": 0.09, "pay_later": True},
    "SAH": {"name": "Sahara Direct", "cover": {"DXB": 0.70}, "bias": 1.03, "markup": 0.11, "pay_later": True},
    "ORL": {"name": "OrientLink", "cover": {"BKK": 0.76, "PAR": 0.10}, "bias": 0.97, "markup": 0.095, "pay_later": False},
}

# Hidden ground-truth fulfilment behaviour, per supplier x city:
# (p_price_jump_at_book, p_confirmation_fail, p_post_confirm_cancel, bookings_in_log)
TRUE_RELIABILITY = {
    ("ATL", "DXB"): (0.015, 0.006, 0.004, 1800), ("ATL", "BKK"): (0.020, 0.008, 0.005, 1200), ("ATL", "PAR"): (0.012, 0.005, 0.003, 1500),
    ("MER", "DXB"): (0.095, 0.032, 0.012, 1400), ("MER", "BKK"): (0.060, 0.020, 0.010, 900), ("MER", "PAR"): (0.040, 0.015, 0.008, 1100),
    ("BLU", "DXB"): (0.030, 0.012, 0.007, 700), ("BLU", "BKK"): (0.025, 0.010, 0.006, 950), ("BLU", "PAR"): (0.035, 0.014, 0.009, 600),
    ("SAH", "DXB"): (0.010, 0.004, 0.003, 2100),
    ("ORL", "BKK"): (0.018, 0.007, 0.004, 1300), ("ORL", "PAR"): (0.020, 0.010, 0.005, 14),
}


@dataclass
class SupplierHotel:
    rec_id: str
    supplier: str
    supplier_hotel_code: str
    city: str
    name: str
    stars: float | None
    lat: float
    lon: float
    address: str
    postcode: str | None
    phone: str | None
    chain: str | None
    true_hotel_id: str  # evaluation only


@dataclass
class SupplierRoom:
    rec_id: str
    supplier: str
    hotel_rec_id: str
    raw_name: str
    true_room_id: str  # evaluation only


def _apply_translit(name: str, rng: random.Random, p: float) -> str:
    for a, b in TRANSLIT:
        if a in name and rng.random() < p:
            name = name.replace(a, b)
    return name


def _typo(s: str, rng: random.Random) -> str:
    if len(s) < 6:
        return s
    i = rng.randint(2, len(s) - 3)
    ops = ["swap", "drop", "double"]
    op = rng.choice(ops)
    if op == "swap" and s[i].isalpha() and s[i + 1].isalpha():
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    if op == "drop" and s[i].isalpha():
        return s[:i] + s[i + 1:]
    if s[i].isalpha():
        return s[:i] + s[i] + s[i:]
    return s


def _hotel_name(code: str, h: Hotel, city_name: str, rng: random.Random) -> str:
    n = h.name
    if code == "ATL":
        n = strip_accents(n)
        if rng.random() < 0.6:
            for k, v in ABBREV.items():
                n = n.replace(k, v)
        return n.upper()
    if code == "MER":
        if n.endswith(" Hotel") and rng.random() < 0.5:
            n = "Hotel " + n[: -len(" Hotel")]
        n = _apply_translit(n, rng, 0.25)
        return f"{n} - {city_name}" if rng.random() < 0.7 else n
    if code == "BLU":
        if h.chain and n.startswith(h.chain) and rng.random() < 0.6:
            n = n[len(h.chain):].strip() + f" by {h.chain}"
        n = _apply_translit(n, rng, 0.6)
        n = strip_accents(n) if rng.random() < 0.7 else n
        return _typo(n, rng) if rng.random() < 0.12 else n
    if code == "SAH":
        n = f"{n} {h.stars}*" if rng.random() < 0.65 else n
        return n.replace("&", "and")
    if code == "ORL":
        n = _apply_translit(n, rng, 0.7)
        n = _typo(n, rng) if rng.random() < 0.18 else n
        return n.replace("Hotel", "Hotel").title() if rng.random() < 0.5 else n
    return n


def _address(code: str, h: Hotel, rng: random.Random) -> str:
    street = h.street
    if code in ("ATL", "ORL"):
        street = street.replace("Road", "Rd").replace("Street", "St").replace("Boulevard", "Bd").replace("Avenue", "Av")
    if code == "BLU" and rng.random() < 0.35:
        return h.area
    if code == "SAH":
        return f"{street}, {h.area}, P.O. Box {rng.randint(10000, 99999)}"
    no = "" if rng.random() < 0.15 else f"{h.street_no} "
    return f"{no}{street}, {h.area}"


def _phone(code: str, h: Hotel, rng: random.Random) -> str | None:
    digits = "".join(ch for ch in h.phone if ch.isdigit())
    cc_len = {"DXB": 3, "BKK": 2, "PAR": 2}[h.city]
    local = digits[cc_len:]
    if code == "BLU" and rng.random() < 0.45:
        return None
    if code == "ATL":
        return "+" + digits
    if code == "MER":
        return "0" + local[:1] + " " + local[1:4] + " " + local[4:]
    if code == "SAH":
        return f"({digits[:cc_len]}) {local[:1]}-{local[1:4]}-{local[4:]}"
    if code == "ORL":
        return None if rng.random() < 0.25 else "0" + local
    return h.phone


def _coords(code: str, h: Hotel, rng: random.Random) -> tuple[float, float]:
    jitter = {"ATL": 25, "MER": 180, "BLU": 90, "SAH": 40, "ORL": 120}[code]
    lat, lon = offset(h.lat, h.lon, abs(rng.gauss(0, jitter)), rng.uniform(0, 360))
    if code == "MER" and rng.random() < 0.012:
        lat, lon = lon, lat  # a real-world bug class: swapped coordinates
    if code == "BLU" and rng.random() < 0.02:
        lat, lon = offset(h.lat, h.lon, rng.uniform(1500, 4000), rng.uniform(0, 360))  # geocoded to area centroid
    dec = 4 if code == "ATL" else 6
    return round(lat, dec), round(lon, dec)


# --------------------------------------------------------------- room names
def room_name(code: str, r: Room, rng: random.Random) -> str:
    cls, bed, view = r.room_class, r.bed, r.view
    v = view or ""
    leak = ""
    if code == "ATL":
        cmap = {"Standard": "STD", "Superior": "SUP", "Deluxe": "DLX", "Premier": "PRM", "Executive": "EXEC",
                "Junior Suite": "JR STE", "Suite": "STE", "Family Room": "FAM", "Studio": "STU"}
        bmap = {"King": "KING", "Queen": "QN", "Double": "DBL", "Twin": "TWN"}
        vmap = {"Sea": "SEA VW", "City": "CITY VW", "Creek": "CRK VW", "Pool": "POOL VW", "Marina": "MAR VW", "River": "RIV VW",
                "Garden": "GDN VW", "Courtyard": "CRTYD", "Street": "STREET", "Eiffel Tower": "EIFFEL VW"}
        parts = [cmap[cls], bmap[bed]] + ([vmap[view]] if view else []) + (["BALC"] if r.balcony else [])
        if rng.random() < 0.25:
            parts.append(rng.choice(["RO", "BB", "NRF"]))
        return " ".join(parts)
    if code == "MER":
        bed_txt = {"King": "1 King Bed", "Queen": "1 Queen Bed", "Double": "1 Double Bed", "Twin": "2 Twin Beds"}[bed]
        base = cls if cls.endswith(("Room", "Suite", "Studio")) else f"{cls} Room"
        tail = f", {v} View" if view else ""
        tail += ", Balcony" if r.balcony else ""
        return f"{base}, {bed_txt}{tail}"
    if code == "BLU":
        bed_txt = {"King": "King", "Queen": "Queen", "Double": "Double", "Twin": "Twin"}[bed]
        if rng.random() < 0.3:
            leak = rng.choice([" - Breakfast Included", " - Non Refundable", " - Room Only", " (Promo)"])
        vtxt = f" with {v} View" if view else ""
        return f"{bed_txt} {cls}{vtxt}{' & Balcony' if r.balcony else ''}{leak}"
    if code == "SAH":
        bed_txt = {"King": "King", "Queen": "Queen", "Double": "Double", "Twin": "Twin"}[bed]
        vtxt = f" {v} View" if view else ""
        return f"{cls}{vtxt} Room ({bed_txt}){' with Balcony' if r.balcony else ''}".replace("Room Room", "Room").replace("Suite Room", "Suite")
    if code == "ORL":
        # OrientLink calls every one-big-bed room "Double": genuine information loss
        bed_txt = "Twin" if bed == "Twin" else "Double"
        vtxt = f" {v.replace(' ', '')}view" if view else ""
        return f"{cls} {bed_txt} Room{vtxt}".replace("Room Room", "Room").strip()
    return cls


# ---------------------------------------------------------------- generator
def generate_supplier_feeds(hotels: list[Hotel], seed: int = 11):
    rng = random.Random(seed)
    from ..config import CITIES
    hotel_recs: list[SupplierHotel] = []
    room_recs: list[SupplierRoom] = []
    for code, sp in SUPPLIERS.items():
        for h in hotels:
            cover = sp["cover"].get(h.city, 0.0)
            # Platinum / 5-star properties are carried by more suppliers
            cover = min(0.97, cover + (0.1 if h.stars == 5 else 0))
            if rng.random() > cover:
                continue
            copies = 2 if rng.random() < 0.004 else 1  # rare true duplicate inside one supplier
            for c in range(copies):
                rid = f"{code}-{h.city}-{len([x for x in hotel_recs if x.supplier == code]) + 1:05d}"
                lat, lon = _coords(code, h, rng)
                stars = float(h.stars)
                if rng.random() < 0.08:
                    stars = max(1.0, min(5.0, stars + rng.choice([-1, 1, 0.5, -0.5])))
                if code == "BLU" and rng.random() < 0.15:
                    stars = None
                hotel_recs.append(SupplierHotel(
                    rec_id=rid, supplier=code, supplier_hotel_code=f"{code[:2]}{rng.randint(100000, 999999)}", city=h.city,
                    name=_hotel_name(code, h, CITIES[h.city]["name"], rng), stars=stars, lat=lat, lon=lon,
                    address=_address(code, h, rng), postcode=(h.postcode or None) if code not in ("BLU",) else None,
                    phone=_phone(code, h, rng), chain=h.chain if code in ("ATL", "SAH") else None, true_hotel_id=h.hotel_id,
                ))
                if c == 1:
                    continue
                for r in h.rooms:
                    if rng.random() < 0.85:
                        room_recs.append(SupplierRoom(
                            rec_id=f"{rid}-{len(room_recs) + 1}", supplier=code, hotel_rec_id=rid,
                            raw_name=room_name(code, r, rng), true_room_id=r.room_id))
    return hotel_recs, room_recs


# ---------------------------------------------------------------- rates
def generate_offers(hotels: list[Hotel], hotel_recs, room_recs, city: str, nights: int, seed: int = 23):
    """Live availability response for one search (city, 2 adults, N nights)."""
    rng = random.Random(seed)
    by_id = {h.hotel_id: h for h in hotels}
    room_by_id = {r.room_id: r for h in hotels for r in h.rooms}
    def g(x, k):
        return x[k] if isinstance(x, dict) else getattr(x, k)
    hrec = {g(r, "rec_id"): r for r in hotel_recs}
    offers = []
    for rr in room_recs:
        hr = hrec[g(rr, "hotel_rec_id")]
        if g(hr, "city") != city:
            continue
        if rng.random() < 0.18:  # not available for these dates
            continue
        sup = g(rr, "supplier")
        sp = SUPPLIERS[sup]
        room = room_by_id[g(rr, "true_room_id")]
        h = by_id[g(hr, "true_hotel_id")]
        n_plans = rng.choices([1, 2, 3], weights=[4, 4, 2])[0]
        seen = set()
        for _ in range(n_plans):
            board = rng.choices(["RO", "BB", "HB"], weights=[5, 4, 1])[0]
            cancel_days = rng.choices([None, 3, 7, 14], weights=[3, 3, 3, 2])[0]  # None = non-refundable
            pay_later = sp["pay_later"] and cancel_days is not None and rng.random() < 0.6
            key = (board, cancel_days, pay_later)
            if key in seen:
                continue
            seen.add(key)
            board_up = {"RO": 0.0, "BB": 0.11 + 0.01 * h.stars, "HB": 0.27 + 0.02 * h.stars}[board]
            nr_disc = 0.89 if cancel_days is None else (0.97 if cancel_days >= 7 else 1.0)
            net = room.base_price_inr * nights * sp["bias"] * (1 + board_up) * nr_disc * rng.uniform(0.93, 1.07)
            sell = net * (1 + sp["markup"])
            offers.append({
                "offer_id": f"{city}-O{len(offers) + 1:05d}", "supplier": sup, "hotel_rec_id": g(rr, "hotel_rec_id"),
                "room_rec_id": g(rr, "rec_id"), "raw_room_name": g(rr, "raw_name"), "board": board, "cancel_free_until_days": cancel_days,
                "pay_later": pay_later, "net_inr": round(net), "sell_inr": round(sell / 10) * 10,
                "true_hotel_id": h.hotel_id, "true_room_id": room.room_id,
            })
    return offers


def generate_booking_log(seed: int = 31):
    """Historical booking outcomes per supplier x city (what TBO already has in its order DB)."""
    rng = random.Random(seed)
    rows = []
    for (sup, city), (pj, cf, pc, n) in TRUE_RELIABILITY.items():
        for i in range(n):
            u = rng.random()
            outcome = "ok"
            if u < pj:
                outcome = "price_jump"
            elif u < pj + cf:
                outcome = "confirm_fail"
            elif u < pj + cf + pc:
                outcome = "supplier_cancel"
            rows.append({"supplier": sup, "city": city, "outcome": outcome})
    return rows


def to_dicts(items):
    return [asdict(x) for x in items]

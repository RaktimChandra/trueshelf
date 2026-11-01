"""Synthetic multi-supplier hotel world with ground truth.

TBO's real supplier feeds are not available to hackathon teams, so we generate
a world that reproduces the failure modes seen in multi-supplier hotel data:

* each supplier names the same hotel differently (case, abbreviations,
  transliteration, chain prefixes dropped, star ratings glued into names,
  city suffixes, typos, accents removed);
* coordinates drift (and one supplier occasionally swaps lat/lon);
* phone numbers and addresses are formatted differently or missing;
* "sister" properties of the same brand sit 80-250 m apart with nearly the
  same name (the classic false-merge trap);
* each supplier names rooms with its own grammar and leaks rate-plan words
  ("Breakfast Included", "Non Refundable") into room names;
* suppliers differ in price level, rate plans, payment terms and reliability.

Ground truth (true hotel id, true room id) is stored on every record but the
matching engine never reads it; it is used only for evaluation.
"""
from __future__ import annotations

import math
import random
import unicodedata
from dataclasses import dataclass, field

from ..config import CITIES

# ---------------------------------------------------------------- vocabulary
CITY_VOCAB = {
    "DXB": {
        "first": ["Al Noor", "Saffron", "Pearl", "Amber", "Coral", "Oud", "Falcon", "Dhow", "Majlis",
                  "Zaafaran", "Silk", "Azure", "Desert Rose", "Lantern", "Palm", "Qasr Al", "Mirage",
                  "Sand Dune", "Wind Tower", "Golden Sail", "Al Seef", "Jasmine", "Bayt", "Noor Al"],
        "second": ["Creek", "Dunes", "Gate", "Garden", "Harbour", "Tower", "Sands", "Ridge", "Court",
                   "View", "Bay", "Oasis", "Pavilion", "Residence", "Crest", "Waters", "Heights", "Square"],
        "areas": {"Deira": (25.2711, 55.3075), "Bur Dubai": (25.2532, 55.2972), "Downtown": (25.1972, 55.2744),
                  "Dubai Marina": (25.0805, 55.1403), "Al Barsha": (25.1124, 55.1980), "JBR": (25.0779, 55.1335),
                  "Business Bay": (25.1850, 55.2650), "Al Karama": (25.2400, 55.3030)},
        "streets": ["Al Rigga Road", "Sheikh Zayed Road", "Al Mankhool Street", "Baniyas Road", "Al Sufouh Road",
                    "The Walk", "Marasi Drive", "Kuwait Street", "Al Wasl Road", "Khalid Bin Al Waleed Road"],
        "phone": ("971", "4"),
        "views": ["Sea", "City", "Creek", "Pool", "Marina"],
    },
    "BKK": {
        "first": ["Lotus", "Chao Phraya", "Silom", "Baan Saeng", "Golden Naga", "Teak", "Orchid", "Sukhumvit",
                  "Jasmine", "Siam", "Ratchada", "Bamboo", "Lumphini", "Sathorn", "Riva", "Krung", "Wang Lang",
                  "Thonglor", "Mango", "Saffron", "Benjarong", "Sala"],
        "second": ["Riverside", "Garden", "House", "Court", "Pavilion", "Lane", "Residence", "Place", "Terrace",
                   "Sky", "Park", "Grove", "Palace", "Quarter", "Haven", "Point"],
        "areas": {"Silom": (13.7286, 100.5340), "Sukhumvit": (13.7380, 100.5600), "Riverside": (13.7230, 100.5130),
                  "Siam": (13.7460, 100.5340), "Khao San": (13.7590, 100.4970), "Sathorn": (13.7210, 100.5290),
                  "Ratchada": (13.7660, 100.5700), "Thonglor": (13.7320, 100.5810)},
        "streets": ["Silom Road", "Sukhumvit Soi 11", "Charoen Krung Road", "Rama IV Road", "Phetchaburi Road",
                    "Sathorn Tai Road", "Ratchadaphisek Road", "Thong Lo Soi 10", "Khao San Road", "Rama I Road"],
        "phone": ("66", "2"),
        "views": ["River", "City", "Pool", "Garden"],
    },
    "PAR": {
        "first": ["Hôtel des Lilas", "Maison Saint-Roch", "Hôtel du Canal", "Villa Opéra", "Le Petit", "Hôtel Lumière",
                  "Les Jardins", "Hôtel de la Seine", "Maison Marais", "Hôtel Saint-Germain", "Le Grand Rivoli",
                  "Hôtel des Arts", "Hôtel Élysée", "Maison Montmartre", "Hôtel Bastille", "Le Clos", "Hôtel Vendôme Rive"],
        "second": ["Étoile", "Parc", "Palais", "Montparnasse", "Pigalle", "Trocadéro", "Saint-Michel", "République",
                   "Concorde", "Louvre", "Nation", "Odéon", "Batignolles", "Madeleine"],
        "areas": {"Le Marais": (48.8590, 2.3620), "Saint-Germain": (48.8530, 2.3330), "Montmartre": (48.8867, 2.3431),
                  "Opéra": (48.8710, 2.3320), "Latin Quarter": (48.8490, 2.3470), "Bastille": (48.8530, 2.3690),
                  "Champs-Élysées": (48.8700, 2.3070), "Montparnasse": (48.8420, 2.3210)},
        "streets": ["Rue de Rivoli", "Boulevard Saint-Germain", "Rue des Martyrs", "Rue Saint-Antoine", "Avenue de l'Opéra",
                    "Rue de la Roquette", "Rue du Bac", "Boulevard Haussmann", "Rue Oberkampf", "Rue Cler"],
        "phone": ("33", "1"),
        "views": ["City", "Courtyard", "Street", "Eiffel Tower"],
    },
}

HOTEL_TYPES = ["Hotel", "Suites", "Resort & Spa", "Hotel Apartments", "Boutique Hotel", "Inn", "Grand Hotel"]
CHAINS = {"Zenora": 0.07, "Halcyon": 0.06, "Kestrel Inn": 0.06, "Brightwater": 0.05, "Amaltas": 0.04}

ROOM_CLASSES = ["Standard", "Superior", "Deluxe", "Premier", "Executive", "Junior Suite", "Suite", "Family Room", "Studio"]
CLASS_TIER = {c: i for i, c in enumerate(ROOM_CLASSES)}
BEDS = ["King", "Queen", "Double", "Twin"]


@dataclass
class Room:
    room_id: str
    room_class: str
    bed: str
    view: str | None
    balcony: bool
    max_occ: int
    base_price_inr: float


@dataclass
class Hotel:
    hotel_id: str
    city: str
    name: str
    chain: str | None
    stars: int
    lat: float
    lon: float
    area: str
    street_no: int
    street: str
    postcode: str
    phone: str
    rooms: list[Room] = field(default_factory=list)
    sister_of: str | None = None
    platinum: bool = False
    content_score: float = 0.5   # how rich the merged content is (images, amenities)
    review_score: float = 8.0


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def offset(lat: float, lon: float, dist_m: float, bearing_deg: float) -> tuple[float, float]:
    br = math.radians(bearing_deg)
    dlat = dist_m * math.cos(br) / 111_320
    dlon = dist_m * math.sin(br) / (111_320 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def _postcode(city: str, rng: random.Random) -> str:
    if city == "PAR":
        return f"750{rng.randint(1, 20):02d}"
    if city == "BKK":
        return f"10{rng.choice(['110', '120', '330', '400', '500', '200'])}"
    return ""  # Dubai: no postcodes, which is realistic and removes a signal


def _room_catalogue(hotel_id: str, city: str, stars: int, rng: random.Random) -> list[Room]:
    views = CITY_VOCAB[city]["views"]
    n = rng.randint(3, 7) if stars >= 4 else rng.randint(2, 5)
    allowed = ROOM_CLASSES[: 3 + stars] if stars < 5 else ROOM_CLASSES
    seen = set()
    rooms: list[Room] = []
    star_base = {2: 3200, 3: 5200, 4: 8800, 5: 16500}[stars]
    city_mult = {"DXB": 1.0, "BKK": 0.62, "PAR": 1.55}[city]
    tries = 0
    while len(rooms) < n and tries < 60:
        tries += 1
        rc = rng.choice(allowed)
        bed = rng.choice(["King", "King", "Twin", "Queen", "Double"]) if rc not in ("Family Room",) else "Twin"
        view = rng.choice(views + [None, None])
        # one big-bed type per (class, view): avoids King and Queen variants of the same room
        bucket = "TWO" if bed == "Twin" else "ONE"
        key = (rc, bucket, view)
        if key in seen:
            continue
        seen.add(key)
        price = star_base * city_mult * (1 + 0.16 * CLASS_TIER[rc]) * (1.12 if view in ("Sea", "River", "Eiffel Tower", "Marina") else 1.0)
        price *= rng.uniform(0.9, 1.12)
        rooms.append(Room(
            room_id=f"{hotel_id}-R{len(rooms) + 1}",
            room_class=rc, bed=bed, view=view,
            balcony=rng.random() < (0.35 if city != "PAR" else 0.15),
            max_occ=4 if rc in ("Family Room", "Suite") else (3 if rc in ("Junior Suite", "Executive") else 2),
            base_price_inr=round(price, -1),
        ))
    return rooms


def generate_hotels(seed: int = 7, per_city: dict | None = None) -> list[Hotel]:
    per_city = per_city or {"DXB": 210, "BKK": 200, "PAR": 170}
    rng = random.Random(seed)
    hotels: list[Hotel] = []
    for city, n in per_city.items():
        voc = CITY_VOCAB[city]
        area_names = list(voc["areas"].keys())
        used_names: set[str] = set()
        cores = [f"{a} {b}" for a in voc["first"] for b in voc["second"]]
        rng.shuffle(cores)
        i = 0
        while len([h for h in hotels if h.city == city]) < n:
            core = cores[i % len(cores)]
            i += 1
            area = rng.choice(area_names)
            chain = None
            r = rng.random()
            acc = 0.0
            for c, p in CHAINS.items():
                acc += p
                if r < acc:
                    chain = c
                    break
            htype = rng.choice(HOTEL_TYPES)
            if chain:
                name = f"{chain} {area}" if rng.random() < 0.5 else f"{chain} {core}"
            else:
                name = core if core.startswith(("Hôtel", "Maison", "Villa", "Le ", "Les ")) else f"{core} {htype}"
            if name in used_names:
                continue
            used_names.add(name)
            hid = f"{city}-{len([h for h in hotels if h.city == city]) + 1:04d}"
            alat, alon = voc["areas"][area]
            lat, lon = offset(alat, alon, abs(rng.gauss(0, 650)), rng.uniform(0, 360))
            stars = rng.choices([2, 3, 4, 5], weights=[1, 3, 4, 2])[0]
            cc, ac = voc["phone"]
            h = Hotel(
                hotel_id=hid, city=city, name=name, chain=chain, stars=stars, lat=lat, lon=lon, area=area,
                street_no=rng.randint(1, 240), street=rng.choice(voc["streets"]), postcode=_postcode(city, rng),
                phone=f"+{cc} {ac} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
                platinum=rng.random() < 0.06, content_score=round(rng.uniform(0.25, 0.95), 2),
                review_score=round(min(9.7, max(6.1, rng.gauss(6.4 + 0.55 * stars, 0.45))), 1),
            )
            h.rooms = _room_catalogue(hid, city, stars, rng)
            hotels.append(h)
            # ~9% get a sister property: same brand core, different type, very close by
            if rng.random() < 0.09 and len([x for x in hotels if x.city == city]) < n:
                sis_type = rng.choice([t for t in HOTEL_TYPES if t != htype])
                base = core if not chain else name
                sis_name = (f"{base} {sis_type}" if chain or not base.startswith(("Hôtel", "Maison", "Villa", "Le ", "Les "))
                            else f"{base} {rng.choice(['Annexe', 'Suites', 'Rive Gauche', 'Résidence'])}")
                if city != "PAR" and not chain:
                    sis_name = f"{core} {sis_type}"
                if sis_name in used_names:
                    continue
                used_names.add(sis_name)
                sid = f"{city}-{len([x for x in hotels if x.city == city]) + 1:04d}"
                slat, slon = offset(lat, lon, rng.uniform(80, 250), rng.uniform(0, 360))
                s = Hotel(
                    hotel_id=sid, city=city, name=sis_name, chain=chain, stars=max(2, min(5, stars + rng.choice([-1, 0, 0, 1]))),
                    lat=slat, lon=slon, area=area, street_no=h.street_no + rng.randint(1, 12), street=h.street,
                    postcode=h.postcode, phone=f"+{cc} {ac} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
                    sister_of=hid, platinum=False, content_score=round(rng.uniform(0.25, 0.95), 2),
                    review_score=round(min(9.7, max(6.1, rng.gauss(6.4 + 0.55 * stars, 0.45))), 1),
                )
                s.rooms = _room_catalogue(sid, city, s.stars, rng)
                hotels.append(s)
    return hotels

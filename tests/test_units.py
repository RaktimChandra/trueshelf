"""Fast unit tests for the deterministic layers."""
from trueshelf.config import DEFAULT
from trueshelf.l4l import l4l
from trueshelf.normalize import clean_name, phone_key, repair_coords
from trueshelf.reliability import ledger
from trueshelf.room_map import parse_room
from trueshelf.sightseeing import atoms, resolve_attraction

P = DEFAULT.l4l
REL_BAD = {"price_jump": {"mean": 0.09}, "confirm_fail": {"mean": 0.03}, "supplier_cancel": {"mean": 0.01}}


def offer(**kw):
    o = {"sell_inr": 20000, "board": "RO", "cancel_free_until_days": 7, "pay_later": False}
    o.update(kw)
    return o


# ------------------------------------------------------------- like-for-like
def test_reference_product_has_no_adjustment():
    c = l4l(offer(), 4, None, P)
    assert c["l4l"] == 20000 and c["meals"] == 0 and c["cancellation"] == 0 and c["pay_later"] == 0


def test_breakfast_lowers_l4l_by_its_value():
    c = l4l(offer(board="BB"), 4, None, P)
    assert c["meals"] == -P.breakfast_pp_by_star[4] * 2 * 2
    assert c["l4l"] < 20000


def test_non_refundable_costs_more_than_flexible():
    nr = l4l(offer(cancel_free_until_days=None), 4, None, P)["l4l"]
    flex = l4l(offer(cancel_free_until_days=3), 4, None, P)["l4l"]
    assert nr > 20000 > flex


def test_pay_later_is_worth_money():
    assert l4l(offer(pay_later=True), 4, None, P)["pay_later"] < 0


def test_unreliable_supplier_adds_expected_failure_cost():
    # 9% x 7% x 20k + 4% x (18% x 20k + 2.5k) = 126 + 244
    assert l4l(offer(), 4, REL_BAD, P)["supplier_risk"] == 370


def test_components_sum_to_l4l():
    c = l4l(offer(board="HB", cancel_free_until_days=14, pay_later=True), 5, REL_BAD, P)
    assert abs(c["price"] + c["meals"] + c["cancellation"] + c["pay_later"] + c["supplier_risk"] - c["l4l"]) <= 3


# ------------------------------------------------------------- normalisation
def test_transliteration_and_abbreviation_collapse():
    a = clean_name("QASR AL TWR INN", "DXB")
    b = clean_name("Kasr El Tower Inn", "DXB")
    assert a["core_sorted"] == b["core_sorted"] and a["types"] == b["types"]


def test_city_suffix_and_stars_removed():
    assert clean_name("Pearl Bay Hotel 4* - Dubai", "DXB")["core"] == ["pearl", "bay"]


def test_type_words_are_kept_apart_from_core():
    assert clean_name("Saffron Creek Suites", "DXB")["types"] == ["suites"]


def test_typo_inside_type_word_is_repaired():
    assert clean_name("Lotus Court Hoel", "BKK")["types"] == ["hotel"]


def test_swapped_coordinates_are_repaired():
    lat, lon, fixed = repair_coords(55.27, 25.20, "DXB")
    assert fixed and abs(lat - 25.20) < 1e-9


def test_phone_key_ignores_formatting():
    assert phone_key("(971) 4-772-9110") == phone_key("+97147729110") == phone_key("04 772 9110")


# ------------------------------------------------------------- rooms
def test_room_grammar_across_supplier_styles():
    names = ["DLX KING SEA VW BALC", "Deluxe Room, 1 King Bed, Sea View, Balcony", "King Deluxe with Sea View & Balcony - Breakfast Included",
             "Deluxe Sea View Room (King) with Balcony"]
    keys = {(p["room_class"], p["bed_bucket"], p["view"]) for p in map(parse_room, names)}
    assert keys == {("Deluxe", "ONE", "Sea")}


def test_rate_words_in_room_name_are_detected_and_stripped():
    p = parse_room("Twin Superior with City View - Non Refundable")
    assert "non_refundable" in p["rate_leaks"] and p["room_class"] == "Superior" and p["bed"] == "Twin"


def test_junior_suite_is_not_a_suite():
    assert parse_room("JR STE KING")["room_class"] == "Junior Suite"
    assert parse_room("STE KING")["room_class"] == "Suite"


# ------------------------------------------------------------- reliability
def test_thin_evidence_is_shrunk_towards_city_average():
    rows = [{"supplier": "BIG", "city": "X", "outcome": "confirm_fail" if i < 50 else "ok"} for i in range(1000)]
    rows += [{"supplier": "TINY", "city": "X", "outcome": "ok"} for _ in range(10)]
    led = ledger(rows)
    tiny = led["TINY|X"]["confirm_fail"]
    assert tiny["raw"] == 0.0 and tiny["mean"] > 0.03 and led["TINY|X"]["thin_evidence"]


# ------------------------------------------------------------- sightseeing
def test_attraction_alias_resolution():
    assert resolve_attraction("At The Top – Priority Entry / Live Guide", "DXB")[0] == "dxb-burj"


def test_experience_atoms():
    a = atoms({"title": "Evening Desert Safari (incl. Sharing Transfer, BBQ Dinner) [Non-Refundable]", "cancellation": "NR"})
    assert a["transfer"] == "shared" and a["meal"] == "dinner" and not a["cancel_24h"]


def test_unreadable_room_names_are_never_grouped():
    from trueshelf.room_map import map_rooms
    recs = [{"rec_id": f"r{i}", "supplier": "NOVA", "hotel_rec_id": "h", "raw_name": n} for i, n in
            enumerate(["Room Type A", "Room Type B", "Junior Suite Lit King", "Junior Suite Lit King Côté Cour"])]
    keys, dq, _ = map_rooms(recs, {"h": "H1"})
    assert len(set(keys.values())) == 4 and dq["NOVA"]["unmapped"] == 4

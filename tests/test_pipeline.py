"""End-to-end checks on the held-out evaluation and the browser/engine parity."""
import json
import pathlib
import subprocess

import pytest

from trueshelf.pipeline import run

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def out():
    return run()


@pytest.mark.parametrize("city", ["DXB", "BKK", "PAR"])
def test_held_out_matching_beats_rule_baseline(out, city):
    e = out["evidence"][city]
    assert e["blocking_recall"] >= 0.995
    assert e["auto"]["f1"] >= 0.98
    assert e["auto"]["precision"] >= 0.995  # wrong merges are the expensive error
    assert e["auto"]["f1"] - e["baseline"]["f1"] >= 0.15


def test_review_load_is_small(out):
    cands = sum(out["evidence"][c]["candidate_pairs"] for c in ("DXB", "BKK", "PAR"))
    assert len(out["review"]) / cands < 0.005


def test_review_queue_is_ordered_by_value_at_risk(out):
    v = [r["gtv_at_risk"] for r in out["review"]]
    assert v == sorted(v, reverse=True)


def test_room_mapping_quality(out):
    assert out["evidence"]["rooms"]["f1"] >= 0.98 and out["evidence"]["rooms"]["precision"] >= 0.999


def test_every_offer_has_consistent_l4l(out):
    for c in ("DXB", "BKK", "PAR"):
        for s in out["search"][c]["shelves"]:
            for r in s["rooms"]:
                ls = [o["l4l"]["l4l"] for o in r["offers"]]
                assert ls == sorted(ls)


def test_platinum_lift_is_bounded(out):
    cap = out["config"]["rank"]["platinum_max_lift"]
    for c in ("DXB", "BKK", "PAR"):
        assert all(s["platinum_lift"] <= cap for s in out["search"][c]["shelves"])


def test_pipeline_is_deterministic():
    a, b = run(), run()
    for c in ("DXB", "BKK", "PAR"):
        assert [s["id"] for s in a["search"][c]["shelves"]] == [s["id"] for s in b["search"][c]["shelves"]]


def test_browser_engine_matches_python(out, tmp_path):
    """web/app.js re-prices and re-ranks in the browser; it must agree with Python to the rupee."""
    data = tmp_path / "data.js"
    data.write_text("window.TS_DATA = " + json.dumps(out, default=float) + ";")
    script = f"""
      global.window = global; require({json.dumps(str(data))}); require({json.dumps(str(ROOT / 'web' / 'app.js'))});
      const res = {{}};
      for (const c of ['DXB','BKK','PAR']) {{
        const r = window.TS_ENGINE.recompute(c);
        res[c] = {{ order: r.map(s => s.id), l4l: r.map(s => s.rooms.map(x => x.offers.map(o => o.l4l.l4l))) }};
      }}
      console.log(JSON.stringify(res));
    """
    js = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(js.stdout)
    for c in ("DXB", "BKK", "PAR"):
        py = out["search"][c]["shelves"]
        assert res[c]["order"] == [s["id"] for s in py], c
        assert res[c]["l4l"] == [[[o["l4l"]["l4l"] for o in r["offers"]] for r in s["rooms"]] for s in py], c

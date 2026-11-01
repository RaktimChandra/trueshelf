"""Run the full pipeline and write web/data.js + data/evidence.json."""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trueshelf.pipeline import run

def main():
    out = run()
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "evidence.json").write_text(json.dumps(out["evidence"], indent=2, default=float))
    js = "window.TS_DATA = " + json.dumps(out, separators=(",", ":"), default=float) + ";\n"
    (ROOT / "web" / "data.js").write_text(js)
    print(f"wrote web/data.js ({len(js)/1e6:.2f} MB)")
    ev = out["evidence"]
    for c in ("DXB", "BKK", "PAR"):
        e = ev[c]
        print(c, "auto F1 %.4f (P %.4f R %.4f) | +review F1 %.4f | baseline F1 %.4f | review pairs %d | listings %s | headline!=best %d/%d" % (
            e["auto"]["f1"], e["auto"]["precision"], e["auto"]["recall"], e["with_review"]["f1"], e["baseline"]["f1"],
            e["review_pairs"], e["listings"], out["search"][c]["headline_not_best"], len(out["search"][c]["shelves"])))
    for c in ("DXB", "BKK", "PAR"):
        rc = out["search"][c]["room_compare"]
        print(c, "rooms with >=2 offers", rc["rooms_multi_offer"], "cheapest-not-best", rc["cheapest_not_best"],
              "%.1f%%" % (100 * rc["cheapest_not_best"] / rc["rooms_multi_offer"]), "avg gap INR %.0f" % (rc["l4l_gap_sum"] / max(1, rc["cheapest_not_best"])))
    print("rooms", {k: round(v, 4) if isinstance(v, float) else v for k, v in ev["rooms"].items()})
    print("sightseeing", ev["sightseeing"])
    print("runtime", ev["runtime_s"])

if __name__ == "__main__":
    main()

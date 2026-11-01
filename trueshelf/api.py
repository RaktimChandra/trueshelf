"""HTTP API around the TrueShelf engine (FastAPI).

Run:  uvicorn trueshelf.api:app --port 8000   then open http://localhost:8000/
"""
from __future__ import annotations

import json
import pathlib
import time
from functools import lru_cache

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import CITIES, DEFAULT, L4LParams
from .hotel_match import HotelMatcher, build_candidates, pair_features, prepare_all, _idf
from .l4l import l4l as l4l_calc
from .normalize import prepare

ROOT = pathlib.Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "data" / "review_decisions.jsonl"

app = FastAPI(title="TrueShelf", version=DEFAULT.version,
              description="Multi-supplier hotel & sightseeing consolidation, like-for-like pricing and ranking.")

# Security headers on every response (found missing by the OWASP ZAP scan in CI).
# The UI loads only its own files (fonts are self-hosted), so the policy can be strict.
_CSP_UI = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
           "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
# FastAPI's interactive /docs page loads Swagger UI from a CDN, so it gets its own, looser policy.
_CSP_DOCS = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
             "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
             "object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
}


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    docs = request.url.path in ("/docs", "/redoc", "/docs/oauth2-redirect")
    for k, v in SECURITY_HEADERS.items():
        if docs and k == "Cross-Origin-Embedder-Policy":
            continue  # the CDN-hosted Swagger UI assets do not send CORP headers
        response.headers.setdefault(k, v)
    response.headers.setdefault("Content-Security-Policy", _CSP_DOCS if docs else _CSP_UI)
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@lru_cache(maxsize=1)
def state() -> dict:
    from .pipeline import run
    from .synth.suppliers import generate_supplier_feeds, to_dicts
    from .synth.world import generate_hotels
    out = run()
    # production matcher: trained on all labelled cities
    hrecs, _ = generate_supplier_feeds(generate_hotels(seed=7), seed=11)
    recs = to_dicts(hrecs)
    X, y = [], []
    idfs = {}
    for c in CITIES:
        R = prepare_all([r for r in recs if r["city"] == c])
        cands, idf = build_candidates(R)
        idfs[c] = idf
        X += [cd.feats for cd in cands]
        y += [int(R[cd.a]["true_hotel_id"] == R[cd.b]["true_hotel_id"]) for cd in cands]
    model = HotelMatcher().fit(np.array(X), np.array(y))
    return {"out": out, "model": model, "idf": idfs}


class SupplierHotelIn(BaseModel):
    supplier: str = Field(..., max_length=8)
    city: str = Field(..., pattern="^(DXB|BKK|PAR)$")
    name: str = Field(..., min_length=2, max_length=200)
    lat: float = Field(..., ge=-90, le=180)
    lon: float = Field(..., ge=-180, le=180)
    stars: float | None = Field(None, ge=0, le=5)
    address: str | None = Field(None, max_length=300)
    phone: str | None = Field(None, max_length=40)
    chain: str | None = Field(None, max_length=80)


class MatchIn(BaseModel):
    a: SupplierHotelIn
    b: SupplierHotelIn


class OfferIn(BaseModel):
    sell_inr: float = Field(..., gt=0, lt=1e8)
    board: str = Field(..., pattern="^(RO|BB|HB)$")
    cancel_free_until_days: int | None = Field(None, ge=0, le=365)
    pay_later: bool = False
    supplier: str | None = None
    city: str = Field("DXB", pattern="^(DXB|BKK|PAR)$")
    stars: int = Field(4, ge=1, le=5)


class DecisionIn(BaseModel):
    same: bool
    reviewer: str = Field(..., min_length=1, max_length=60)


@app.get("/api/health")
def health():
    return {"ok": True, "config_version": DEFAULT.version}


@app.get("/api/search")
def search(city: str = "DXB", limit: int = 20):
    if city not in CITIES:
        raise HTTPException(404, "unknown city")
    s = state()["out"]["search"][city]
    limit = max(1, min(limit, 200))
    slim = [{k: sh[k] for k in ("rank", "id", "name", "stars", "area", "suppliers", "n_offers", "best", "cheapest", "score", "score_parts", "platinum_lift")}
            for sh in s["shelves"][:limit]]
    return {"city": city, "hotels": len(s["shelves"]), "supplier_records": len(s["raw"]), "offers": s["n_offers"], "results": slim}


@app.get("/api/shelf/{shelf_id}")
def shelf(shelf_id: str):
    city = shelf_id[:3]
    if city not in CITIES:
        raise HTTPException(404, "unknown shelf")
    for sh in state()["out"]["search"][city]["shelves"]:
        if sh["id"] == shelf_id:
            return {k: v for k, v in sh.items() if k != "true_ids"}
    raise HTTPException(404, "unknown shelf")


@app.post("/api/match")
def match(body: MatchIn):
    """Score two supplier hotel records: probability, decision and the signals behind it."""
    if body.a.city != body.b.city:
        return {"p_same": 0.0, "decision": "keep_apart", "why": [{"label": "Different cities"}]}
    st = state()
    r1 = prepare({**body.a.model_dump(), "rec_id": "a"})
    r2 = prepare({**body.b.model_dump(), "rec_id": "b"})
    x = pair_features(r1, r2, st["idf"][body.a.city])
    p = float(st["model"].predict_proba(np.array([x]))[0])
    th = DEFAULT.match
    decision = "merge" if p >= th.auto_merge else "review" if p >= th.review_floor else "keep_apart"
    return {"p_same": round(p, 4), "decision": decision, "thresholds": {"auto_merge": th.auto_merge, "review_floor": th.review_floor},
            "why": st["model"].explain(x, top=6), "model_version": DEFAULT.version}


@app.post("/api/l4l")
def like_for_like(body: OfferIn):
    rel = state()["out"]["reliability"].get(f"{body.supplier}|{body.city}") if body.supplier else None
    o = {"sell_inr": body.sell_inr, "board": body.board, "cancel_free_until_days": body.cancel_free_until_days, "pay_later": body.pay_later}
    return {"components": l4l_calc(o, body.stars, rel, DEFAULT.l4l, DEFAULT.occupancy_adults, DEFAULT.nights, DEFAULT.lead_days),
            "assumptions_version": DEFAULT.version}


@app.get("/api/review")
def review_queue(limit: int = 50):
    q = state()["out"]["review"][: max(1, min(limit, 500))]
    return [{k: v for k, v in r.items() if k != "truth_same"} for r in q]


@app.post("/api/review/{pair}")
def review_decide(pair: str, body: DecisionIn):
    if not any(r["pair"] == pair for r in state()["out"]["review"]):
        raise HTTPException(404, "unknown pair")
    DECISIONS.parent.mkdir(exist_ok=True)
    rec = {"pair": pair, "same": body.same, "reviewer": body.reviewer, "ts": time.time(), "model_version": DEFAULT.version}
    with DECISIONS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return {"logged": True, **rec}


@app.get("/api/reliability")
def reliability(city: str | None = None):
    rel = state()["out"]["reliability"]
    return [v for v in rel.values() if city is None or v["city"] == city]


@app.get("/api/evidence")
def evidence():
    return state()["out"]["evidence"]


@app.get("/api/config")
def config():
    return DEFAULT.to_dict()


@app.get("/data.js")
def data_js():
    p = ROOT / "web" / "data.js"
    if not p.exists():
        raise HTTPException(404, "run scripts/build_data.py first")
    return FileResponse(p, media_type="application/javascript")


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")

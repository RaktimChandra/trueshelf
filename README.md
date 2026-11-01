# TrueShelf

[![tests](https://github.com/RaktimChandra/trueshelf/actions/workflows/ci.yml/badge.svg)](https://github.com/RaktimChandra/trueshelf/actions/workflows/ci.yml)

**Every supplier's version of the same product, on one shelf, at its true price.**
Team **vortexxx** (Raktim Chandra, Nipun Dewangan, Pronov Mazumdar) · TBO VoyageHack 4.0 · Track: *Multi-Supplier Optimization*

**Proof page** (live prototype, walkthrough, all tests, and our evaluation re-run in your browser): https://raktimchandra.github.io/trueshelf/
· Round 1 deck: [`submission/`](submission/) · What is *not* built yet: [**ROADMAP.md**](ROADMAP.md)

> **Status, in one line:** the engine, held-out evaluation, 36 tests, prototype and API are built and working on **synthetic data**.
> Content/image enrichment, sightseeing ranking, learned ranking and a real-data pilot are **coming soon**; see the roadmap.

TBO buys the same hotel, the same room and the same Burj Khalifa ticket from several suppliers. Each supplier names, prices and
packages it differently. Agents today scroll duplicate hotel cards and compare headline prices that hide breakfast, cancellation terms,
pay-later terms and supplier risk. TrueShelf fixes this in four layers:

| Layer | Question | How |
|---|---|---|
| 1. Hotel identity | Same place? | Deterministic cleaning → geo + rare-word blocking → 23 pairwise signals → calibrated gradient boosting → clustering constrained by "one supplier never lists a building twice" |
| 2. Product identity | Same room? Same experience? | Room grammar (class, bed, view) with rate-plan leak stripping; sightseeing "experience atoms" (access, transfer, meal, guide, group, cancellation) |
| 3. Like-for-Like Price | Which deal is really cheaper? | Converts meals, cancellation terms, pay-later and supplier failure risk into rupees against one reference product. Every term is shown |
| 4. ShelfRank | What should the agent see first? | Value + quality + expected TBO gross profit + supplier trust, a diversity pass, and a capped, visible Platinum lift |

Around these sit a **Mapping Review Desk** (only uncertain pairs reach a person, ordered by booking value at risk) and a
**Supplier Reliability Ledger** (Bayesian failure rates per supplier × city, with credible intervals).

## Results (synthetic data, held-out)

The hotel matcher for each city is trained only on the other two cities (leave-one-city-out).

| City (held out) | Records → hotels | TrueShelf F1 | Precision | Rule baseline F1 | Sent to review |
|---|---|---|---|---|---|
| Dubai | 651 → 209 | 0.9987 | 1.0000 | 0.8058 | 23 pairs |
| Bangkok | 605 → 198 | 0.9928 | 0.9956 | 0.7553 | 13 pairs |
| Paris | 401 → 167 | 0.9955 | 1.0000 | 0.8239 | 3 pairs |

* Room mapping F1 **0.996** (precision 0.9997) vs **0.21** for fuzzy room-name matching.
* Sightseeing product matching F1 **0.996**; attraction resolved correctly for 100% of products.
* Only **39 of 102,100** candidate pairs (0.04%) needed a person.
* In **25–65%** of rooms sold by two or more offers, the cheapest headline was not the best like-for-like deal (average gap ₹1.1k–1.4k per booking). This depends on the stated assumptions.
* An unseen room-naming style keeps **zero wrong merges**; recall drops to 49% and the rest is flagged for mapping. See `docs/EVALUATION_STRESS.md`.

**Honest limits:** all hotels, suppliers and bookings are generated (`trueshelf/synth/`) because no TBO data is available to teams.
The generator reproduces real failure modes: transliteration, abbreviations, city suffixes, typos, swapped coordinates, sister
properties 80–250 m apart, and rate-plan words in room names. Real feeds will still be messier. Rupee values in like-for-like
pricing are editable assumptions, meant to be replaced by values measured from TBO's own data.

## Run it

```bash
pip install -r requirements.txt
python scripts/build_data.py           # runs the engine, writes web/data.js (~15 s)
open web/index.html                    # the full UI works as a static page
# or serve UI + API:
uvicorn trueshelf.api:app --port 8000  # http://localhost:8000  ·  API docs at /docs
python -m pytest -q                    # 36 tests, ~1 min
python scripts/stress_test.py          # unseen room style + throughput
docker build -t trueshelf . && docker run -p 8000:8000 trueshelf   # same, containerised
```

CI runs the full test suite and the stress test on every push.

### API

| Endpoint | Purpose |
|---|---|
| `GET /api/search?city=DXB` | Ranked hotel shelves with best like-for-like offer and score breakdown |
| `GET /api/shelf/{id}` | One hotel: merged supplier records, canonical rooms, all offers with L4L components |
| `POST /api/match` | Score two supplier hotel records: probability, merge/review/keep-apart decision, signals |
| `POST /api/l4l` | Like-for-like breakdown for an offer |
| `GET /api/review` · `POST /api/review/{pair}` | Review queue; decisions are appended to `data/review_decisions.jsonl` with reviewer and model version |
| `GET /api/reliability` · `GET /api/evidence` · `GET /api/config` | Ledger, evaluation, configuration in force |

## Repository map

```
trueshelf/
  config.py          every threshold, weight and rupee assumption (versioned)
  normalize.py       deterministic cleaning: transliteration, abbreviations, type words, phones, coordinate repair
  hotel_match.py     blocking, pairwise features, calibrated model, constrained clustering, rule baseline
  room_map.py        room grammar, rate-plan leak detection, fail-safe grouping
  l4l.py             like-for-like price
  reliability.py     supplier reliability ledger (empirical-Bayes Beta-Binomial)
  shelfrank.py       ranking, diversity, bounded Platinum lift
  sightseeing.py     attraction resolution + experience atoms
  pipeline.py        end-to-end run with leave-one-city-out evaluation
  api.py             FastAPI service
  synth/             synthetic world, supplier feeds, offers, booking log, sightseeing feeds
web/                 single-page UI (no build step); L4L + ShelfRank re-implemented for live what-if
tests/               unit, pipeline, API and browser/engine parity tests
docs/                architecture, stress tests, honest status
proof/               proof page source (in-browser verification driver, test report)
submission/          Round 1 deck (PPTX + PDF) and video script
```

## Coming soon

Short version of [ROADMAP.md](ROADMAP.md):

- Shadow-mode pilot on one real TBO supplier feed (everything so far is synthetic)
- Content and image enrichment (asked for in the brief; not built yet)
- Sightseeing listing-page ranking (asked for in the brief; products are grouped but not ranked yet)
- Learning-to-rank from click/booking logs, with an A/B test on conversion
- Learned room matcher for unseen naming styles; non-Latin scripts
- Postgres storage, incremental re-mapping, auth on the Review Desk, live TBO API adapters

## Licences

Repository: all rights reserved pending the competition's IP terms (see `LICENSE`).
All dependencies allow commercial use: NumPy, SciPy and scikit-learn (BSD-3), RapidFuzz (MIT), FastAPI (MIT),
Uvicorn (BSD-3) and Pydantic (MIT). UI fonts are IBM Plex (OFL) and Fraunces (OFL).
AI coding assistant: Claude, used for implementation support and test writing. Design decisions and evaluation protocol are the team's.

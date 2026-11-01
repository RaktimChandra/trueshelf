# Roadmap: what is built, what is not, what is next

The step-by-step execution plan with acceptance checks is in [PLAN.md](PLAN.md).

This page is deliberately blunt. Everything marked **Built** runs and is tested.
Everything marked **Coming soon** is not built yet, however it is described elsewhere.

## Against the problem statement

| Asked for in the TBO brief | Status |
|---|---|
| Hotels: identify and consolidate duplicate listings across suppliers | **Built**: held-out F1 0.993–0.999 across three cities |
| Hotels: map equivalent room types | **Built**: F1 0.996 on known supplier styles; fail-safe (zero wrong merges) on an unseen style |
| Hotels: **enrich property content and images** | **Coming soon**: today we only choose a consensus display name. No image de-duplication, quality scoring, description or amenity merging yet |
| Hotels: compare bookable options on price, cancellation, payment terms, supplier reliability | **Built**: like-for-like price with an itemised breakdown; Bayesian supplier reliability ledger |
| Hotels: compare on **availability** | **Partial**: only offers that are available are shown. No availability-quality signal (e.g. allotment depth, sold-out frequency) yet |
| Hotels: optimise listing-page ranking | **Built** with fixed, configurable weights. **Not yet learned from real click/booking data** |
| Sightseeing: identify equivalent products while keeping meaningful differences | **Built**: experience atoms; F1 0.996 |
| Sightseeing: **optimise listing-page ranking** | **Coming soon**: products are grouped and sorted by price minus inclusions. No ranking model yet |
| Increase price competitiveness and booking conversion | **Not measured**: needs real traffic and an A/B test |

## Coming soon (Round 2 and beyond)

### Data and evaluation
- [ ] **Shadow-mode pilot on one real TBO supplier feed.** Everything so far is synthetic, because no TBO data is available to teams. This is the single most important next step.
- [ ] **Learned room matcher for unseen naming styles.** Recall on an unseen style is 49% (by design, unreadable names are isolated, not guessed). A small learned model plus the Review Desk should lift this without giving up precision.
- [ ] **Non-Latin scripts** (Arabic, Thai, Japanese hotel names). Not handled today.
- [ ] **Scale test at catalogue size.** Measured on 1,657 supplier records; matching is per city and shards by destination, but a run at 100k+ records has not been done.

### Product
- [ ] **Content and image enrichment**: perceptual-hash image de-duplication, image quality scoring, amenity and description merging with per-field provenance.
- [ ] **Sightseeing ranking**: the same value / quality / margin / trust approach as ShelfRank, applied to experiences.
- [ ] **Learning-to-rank** from TBO click and booking logs to replace fixed ShelfRank weights; measure conversion with an A/B test.
- [ ] **Like-for-like assumptions fitted from data**: cancellation curves, breakfast value and failure costs measured from TBO's own bookings instead of stated defaults.
- [ ] **Availability-quality signal** (sold-out frequency, allotment depth) in the comparison and ranking.

### Engineering
- [ ] **Persistent storage**: mapping table and review decisions in Postgres (review decisions are a JSONL file today).
- [ ] **Incremental re-mapping** when one supplier's feed changes (designed in `docs/ARCHITECTURE.md`, not built).
- [ ] **Authentication and roles** on the Review Desk and API.
- [x] Free OWASP ZAP security scan in CI; security headers and self-hosted fonts (12 findings → 2, none High).
- [ ] **Security to zero**: remove inline styles from the UI (CSP), JSON on every API error, plus CodeQL, Bandit, pip-audit.
- [ ] **Prototype on phones**: the proof page is fixed; the prototype still overflows on small screens.
- [ ] **Live supplier adapters** for TBO's real hotel and sightseeing APIs.

### Submission
- [ ] **Human voice-over** for the walkthrough (the current narration is a synthetic voice).
- [ ] **Confirm the in-browser verification** runs on judges' typical laptops and browsers (built and simulated, not yet run end-to-end in a browser).

## Built (for reference)
Engine, held-out evaluation, 36 tests (unit, pipeline, API, browser ↔ engine parity, determinism), 6-screen prototype, REST API, Round 1 deck and video, and a proof page that re-runs the Paris evaluation in the viewer's browser. Details: [README](README.md) · [docs/STATUS.md](docs/STATUS.md).

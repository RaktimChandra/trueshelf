# TrueShelf master plan: from today to the finale, free tools only

**Bar:** award-winning, no compromise. Everything must be real, tested, measured and honestly labelled.
**Constraint:** free tools and services only (no StackHawk or any paid service).
**How to use this file:** start the next working session with *"Execute PLAN.md, starting at Phase 0 checks, then Phase 1 in order"*.
Every task has an acceptance check, so "done" is objective. Tick boxes as you go.

Last updated: 2 Nov 2026 · Repo: https://github.com/RaktimChandra/trueshelf · Proof page: https://raktimchandra.github.io/trueshelf/

---

## 1. Honest position today

| Area | Done | Evidence / gap |
|---|---|---|
| Round 1 deliverables (deck, video, proof page, QR) | **90%** | Synthetic voice; in-browser verification not yet run in a real browser; prototype not phone-friendly |
| Core engine (hotel identity, rooms, like-for-like, ShelfRank, ledger, sightseeing atoms) | **85%** | Room recall on unseen naming styles is 49% (fails safe) |
| Coverage of the TBO brief | **75%** | **Content and image enrichment: 0%. Sightseeing ranking: 0%.** Availability quality: partial |
| Evaluation and tests | **80%** | 38 tests, held-out by city, stress test, determinism, parity. No ranking-quality evaluation; no scale test |
| Security | **60%** | ZAP in CI: 12 → 2 findings (0 High). Left: inline styles in the UI (Medium), unexpected content-type (Low). No SAST/dependency scanning yet |
| Mobile and accessibility | **40%** | Proof page fixed and checked on 3 devices; **prototype overflows on phones**; no accessibility audit |
| Engineering for production | **35%** | CI, Docker done. No database, auth, incremental re-mapping, live API adapter, observability, scale |
| Real-world validation | **0%** | Needs TBO data; plan below asks for it |
| Team readiness for the finale | **5%** | Teammates have no commits; no rehearsal or Q&A bank |
| Round 2 package (10-slide deck, demo video) | **0%** | Due 24 Dec |

**Overall: about 55% done, 45% left** against the award-winning bar. Round 1 alone: about 90% done.

---

## 2. Phase 0: your checks before the next session (about 30 minutes, you)

- [ ] Open https://raktimchandra.github.io/trueshelf/ on a laptop. Press **Run everything**. Note the time taken and whether the comparison table says "match". If anything fails, copy the console text.
- [ ] Scan the QR on the deck cover from your phone (iPhone: Camera app; Android: Camera or Google Lens). It must open the proof page. Try once in an incognito tab.
- [ ] Decide the voice: (a) record your own over `TrueShelf_demo_walkthrough.mp4`, or (b) allow `huggingface.co` in claude.ai Settings → Capabilities and record a 30–60 s clean sample for a voice clone (free, open model).
- [ ] Nipun and Pronov: create GitHub accounts if needed; you add them as collaborators (repo → Settings → Collaborators).
- [ ] Optional but valuable: email TBO (voyagehacks@tbo.com) asking whether a small anonymised supplier-content sample or API sandbox access is possible for Round 2. Even "no" is useful for the Q&A.

---

## 3. Phase 1: Round 1 polish (one session; finish well before 20 Nov)

Order matters: the items a judge sees first come first.

### 1.1 Prototype on phones (judges arrive by QR)
- Filters move into a slide-up sheet; shelf cards stack (image, name, price, then chips); header becomes one compact row with a scrollable tab bar; review desk and ledger tables become cards below 600 px.
- Also self-host fonts in the standalone `app.html` and `index.html` used on GitHub Pages.
- **Accept:** zero horizontal overflow at 320, 375, 412 and 768 px on every view, enforced by a Playwright test in CI; screenshots checked by eye.

### 1.2 Hotel content and image enrichment (missing from the brief)
- Synthetic supplier content: amenities (with conflicts), descriptions (different lengths and quality), and procedurally generated images per supplier with exact duplicates, near-duplicates (resized, re-compressed, cropped), low-resolution and off-topic shots.
- Engine: amenity merge by weighted supplier vote with per-field provenance; description choice by completeness and specificity, never invented text; image de-duplication with perceptual hashing (difference hash, pure NumPy); quality score from resolution, sharpness (Laplacian variance) and exposure; gallery ordering that covers room, bathroom, pool, lobby and exterior.
- UI: a "Content" tab per hotel showing the merged gallery, which supplier each field came from, and the conflicts we resolved.
- **Accept:** image de-dup precision ≥ 0.99 and recall ≥ 0.95 on held-out cities; amenity merge accuracy vs ground truth reported; tests added; numbers on the Evidence page.

### 1.3 Sightseeing listing ranking (missing from the brief)
- "SightRank": value after inclusions, quality (synthetic ratings and review counts), TBO margin, supplier reliability, plus diversity so the first screen is not eight Burj Khalifa variants.
- UI: a ranked sightseeing listing per city with "why this rank" bars, as for hotels.
- **Accept:** ranking parity test (browser vs engine), diversity check on the top 10, documented weights, tests.

### 1.4 Availability-quality signal
- Synthetic sold-out frequency and last-room flags per supplier and hotel; shown as a chip and used as a small ranking factor.
- **Accept:** tests; documented as synthetic.

### 1.5 Security to zero findings (free tools)
- Remove `style-src 'unsafe-inline'`: move inline `style=` attributes in `web/app.js` into CSS classes, or set styles through the DOM (allowed by CSP).
- Investigate the 4 "Unexpected Content-Type" responses from the ZAP report artifact; make every API error return JSON.
- Turn the ZAP job into a gate: fail CI on any Medium or High.
- Add free scanners: **CodeQL** (free for public repos), **Bandit** (Python SAST), **pip-audit** (dependency CVEs), **Dependabot** alerts and updates, GitHub **secret scanning** (free for public repos).
- Update Actions to Node 24-compatible versions (CI currently warns that Node 20 is deprecated).
- **Accept:** ZAP 0 Medium/High (Low only if justified in `SECURITY.md`); CodeQL, Bandit and pip-audit clean or each exception justified.

### 1.6 Quality bars a judge can feel
- Lighthouse CI (free) on the proof page and prototype: **Performance, Accessibility, Best Practices ≥ 90**.
- axe-core accessibility scan via Playwright: **0 serious/critical** issues (keyboard navigation, contrast, labels, focus rings).
- Prototype data is 3.8 MB of JavaScript: split per city and load lazily; first paint < 2 s on a mid-range phone.

### 1.7 Refresh the submission
- Update both content slides with enrichment and sightseeing ranking; keep the 2-slide rule.
- Regenerate the walkthrough: new scenes, final voice (from Phase 0), QR end card; re-check frames and audio.
- Extend the in-browser verification to the new modules if the run stays under 3 minutes.
- Re-run everything; tag `v1.0-round1` on GitHub with release notes; submit PDF and video on Unstop.
- **Accept:** all tests green, proof-page numbers match the engine output exactly, QR scans from deck and video.

---

## 4. Phase 2: Round 2 prototype (26 Nov – 24 Dec)

### 2.1 Matching that generalises
- Learned room matcher (character n-grams + parsed attributes) behind the same fail-safe: anything uncertain goes to review.
- Non-Latin names (Arabic, Thai, Japanese) via free transliteration (Unidecode / ICU) plus script-aware rules.
- **Accept:** unseen-style room recall ≥ 85% with **zero** wrong merges; non-Latin held-out F1 reported.

### 2.2 Ranking that learns, evaluated honestly
- Simulated agent behaviour with position bias; learning-to-rank (free, e.g. XGBoost `rank:pairwise`); counterfactual offline evaluation (inverse propensity scoring) against fixed ShelfRank and cheapest-first.
- An A/B-test simulator showing how a real TBO test would be read (sample size, duration, guardrails).
- **Accept:** clearly labelled as simulation; NDCG and expected-margin gains with confidence intervals.

### 2.3 Scale
- 100k and 1M synthetic supplier records; per-city sharding with multiprocessing; memory profile.
- **Accept:** benchmark table in `docs/`; search-time path (join + like-for-like + rank) under 50 ms p95 per search.

### 2.4 Production shape
- Postgres (free, Docker) via SQLAlchemy: listings, supplier mappings, canonical rooms, review decisions with full audit trail, versioned config.
- Incremental re-mapping when one supplier's feed changes (diff, re-block that city, re-score, audit).
- Auth and roles (agent, mapping reviewer, admin) with JWT; rate limiting; review decisions feed scheduled retraining (active learning).
- Observability: structured logs, `/metrics` (Prometheus format), request IDs.
- **Accept:** `docker compose up` brings up API, DB and UI; migration and integration tests in CI.

### 2.5 Live supply
- Adapter interface for TBO hotel and sightseeing APIs, with a mock server and contract tests; plug in real credentials if TBO provides sandbox access.
- **Accept:** the adapter passes contract tests against the mock; no change to booking codes (display layer only).

### 2.6 Free hosting for a live demo
- Static: GitHub Pages (done). API: a free tier such as Hugging Face Spaces (Docker) or Render free web service; document the cold-start delay honestly.

### 2.7 Round 2 deliverables
- 10-slide deck (Slides/PPTX), explainer video with human or cloned voice, README and developer docs, a 3-minute demo script, GitHub release `v2.0-round2`.

---

## 5. Phase 3: Grand Finale (8 Jan)

- [ ] Each member owns and has committed to their module: **Raktim** (ShelfRank, like-for-like, demo, product story), **Nipun** (hotel matching, enrichment), **Pronov** (rooms, sightseeing, evaluation, tests). Each rebuilds their part locally once.
- [ ] Q&A bank: the 25 hardest likely questions with crisp, honest answers (synthetic data, "isn't mapping solved", conversion uplift, assumptions, scale, security, cost to run).
- [ ] Two full rehearsals with a timer; a recorded offline demo as fallback if Wi-Fi fails.
- [ ] One-page pilot proposal for TBO leadership: one city, shadow mode, success metrics, 4-week timeline.
- [ ] Printed QR card linking to the proof page.

---

## 6. Definition of "award-winning done"

- [ ] Every item the TBO brief asks for is built, tested and visible in the prototype.
- [ ] Every number in the deck, video and proof page is produced by code in the repo and re-runnable.
- [ ] CI is green: tests, ZAP (0 Medium/High), CodeQL, Bandit, pip-audit, Lighthouse ≥ 90, axe 0 serious, mobile overflow test.
- [ ] Works on a phone from the QR in under 3 seconds.
- [ ] `ROADMAP.md` lists only genuinely future work; nothing claimed that isn't built.
- [ ] Every team member can explain and demo their part alone.

---

## 7. Free tool list

| Need | Free choice |
|---|---|
| Dynamic security scan | OWASP ZAP (Apache 2.0) in GitHub Actions |
| Code and dependency security | CodeQL, Bandit, pip-audit, Dependabot, GitHub secret scanning |
| CI and hosting | GitHub Actions, GitHub Pages; Hugging Face Spaces or Render free tier for the API |
| Performance and accessibility | Lighthouse CI, axe-core with Playwright |
| Voice | Kokoro (Apache-2.0, used now) or an open voice-clone model (needs huggingface.co allowed) |
| Fonts | IBM Plex, Fraunces (SIL OFL), self-hosted |
| Database | PostgreSQL in Docker |

## 8. Risks and how we handle them

| Risk | Mitigation |
|---|---|
| Judges dismiss synthetic data | Say it first; show held-out protocol, stress test and open code; ask TBO for a sample; pilot plan |
| In-browser verification fails on some browsers | Graceful error with the local command; recorded run in the video; test on Chrome, Edge, Firefox, Safari |
| Scope creep before 20 Nov | Phase 1 order is fixed; Phase 2 items never block Round 1 submission |
| Teammates can't answer individually | Module ownership, own commits, two rehearsals |
| Other teams copy the idea (repo is public) | Public, timestamped commit history is our prior-art record; execution depth is the moat |

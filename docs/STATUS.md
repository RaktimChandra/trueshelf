# TrueShelf: honest status (VoyageHack 4.0, team vortexxx)

## Done
| Item | State | Evidence |
|---|---|---|
| Track choice + research | Done | Multi-Supplier Optimization; TBO hotels ≈ 87% of gross profit; most public VoyageHack repos are chatbot copilots |
| Engine (matching, rooms, like-for-like price, ShelfRank, sightseeing, reliability) | Done, works | `trueshelf/` |
| Held-out evaluation | Done | Hotel matching F1 0.996 vs 0.795 rule baseline; rooms 0.996; sightseeing 0.996 |
| Tests | 36/36 pass | Includes determinism and browser ↔ engine parity |
| Prototype UI (6 screens) + REST API | Done | `web/`, `trueshelf/api.py` |
| Round 1 deck (cover + 2 content + close), PPTX + PDF | Done, with QR on cover and close | `TrueShelf_vortexxx_VoyageHack4.pptx` |
| Narrated video (5:36) with QR end card | Done, synthetic voice | `TrueShelf_narrated_video.mp4` |
| Proof page: re-runs our Paris evaluation in the viewer's browser | Published, **private until you share it** | https://claude.ai/artifact/MFWWqm5Hn7ZVQPgyFcq2k9 |

## Left, in priority order
1. **Make the proof page public (5 min, you).** Open the link above on claude.ai → Share → set to anyone with the link. Then scan the QR from your phone in a private/incognito window. If it asks you to log in, it is not public yet. Until this is done, every QR in the deck and video leads to a page judges can't open.
2. **Run "Run everything" once yourself (5 min, you).** In-browser Python could not be tested from my workspace, which has no internet. The Python side was simulated exactly, the page handles failure gracefully, and the command-line fallback is printed. But open the page on a laptop, press the button, and confirm the "Your browser vs our report" table shows "match". If it fails, tell me the console text.
3. **Decide on the voice (you).** The narration is synthetic. Either keep it (and say so if asked), record your own voice over `TrueShelf_demo_walkthrough.mp4` using `VIDEO_SCRIPT.md`, or allow huggingface.co and send a 30–60 s sample for a clone.
4. **Push the code to GitHub (10 min, you).** My GitHub token here is invalid. Unzip `trueshelf_code.zip`, then `git init`, commit, and push to `RaktimChandra/trueshelf`. Round 2 requires a repo, and the finale asks members about their own commits.
5. **Optional short link.** Approve Vercel team access when I ask, and I'll put `trueshelf-vortexxx.vercel.app` in front of the proof page.
6. **Submit on Unstop before 20 Nov, 11:59 PM:** the PDF/PPT plus the video.

## Weak spots a judge may hit (prepare answers)
- **"It's synthetic data."** Yes. No TBO feeds are given to teams. The generator reproduces documented failure modes, the evaluation is held-out by city, and Round 2 starts with a shadow pilot on one real feed.
- **"Isn't hotel mapping solved by GIATA/Vervotech?"** Hotel *identity* is. Offer-level like-for-like comparison and ranking from TBO's own booking outcomes is not. That's our layer, and it can sit on top of a bought mapping table.
- **"Where's the conversion uplift?"** Not measured. It needs real traffic and an A/B test. We don't claim it.
- **"Are the like-for-like rupee values right?"** They're stated, editable assumptions, to be replaced by values measured from TBO's data.

## Team ownership (so each person can answer alone in the finale)
| Person | Owns | Must be able to explain |
|---|---|---|
| Raktim | Overall, ShelfRank, like-for-like, demo | Why like-for-like is a comparison price; the score formula; the Platinum cap |
| Nipun | Hotel matching (`normalize.py`, `hotel_match.py`) | Blocking, the 23 signals, calibration, why there are two thresholds, the one-supplier-one-building rule |
| Pronov | Rooms, sightseeing, evaluation, tests | Room grammar and fail-safe isolation, experience atoms, leave-one-city-out, the 3 bugs the tests caught |

Suggested split for this is only a starting point; swap as you prefer, but each person should rebuild their part locally once.

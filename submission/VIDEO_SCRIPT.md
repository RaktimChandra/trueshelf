# TrueShelf: Round 1 video script (about 4½ minutes; a 3-minute cut is noted at the end)

**Format:** screen recording with voice-over. Raktim narrates. Nipun or Pronov can take the middle section if you want more than one voice.
**What to show:** the deck (slides 1–3), then the live prototype. `TrueShelf_demo_walkthrough.mp4` already has the exact click path with captions. Record your voice over it, or re-record the screen while you speak.
**Pace:** about 140 words a minute. Times are cumulative.

---

### 0:00–0:30 · Hook (slide 1, cover)

> Hi, we're team vortexxx from SRM. Our idea is TrueShelf.
> TBO buys the same hotel, the same room and the same Burj Khalifa ticket from many suppliers. Each supplier names it, prices it and packages it differently. So an agent ends up comparing the same product against itself, using a price that doesn't tell the whole story.
> TrueShelf puts every supplier's version of a product on one shelf, at its true price.

### 0:30–1:05 · The problem (switch to prototype, "Supplier feed (today)" view)

> This is a Dubai search: two adults, two nights. In our test world the feed returns 643 cards for 209 real hotels. The coloured stripes mark cards that are really the same hotel, up to five times.
> And the price on each card is a headline. It hides whether breakfast is included, whether the booking is refundable, whether the agent can pay later, and how often that supplier fails to confirm.
> Hotels and ancillaries are about 87% of TBO's gross profit, so this screen is where the money is made.

### 1:05–2:15 · The solution (toggle to "TrueShelf", open the #1 hotel)

> TrueShelf works in four layers.
> First, *same place?* We clean names: transliterations like Qasr and Kasr, abbreviations like HTL, star ratings and city names glued onto the name. Then we score twenty-three signals with a calibrated model. A sister property 150 metres away, "Creek Hotel" next to "Creek Suites", stays separate.
> Second, *same product?* A room grammar reads class, bed and view from every supplier's naming style. It strips "Breakfast Included" when a supplier writes it into the room name, so breakfast isn't counted twice.
> Third, the *like-for-like price*. Click an offer and you see it: the price the agent pays, minus the value of meals, plus the expected cost of stricter cancellation, minus the cash benefit of paying later, plus the expected cost of the supplier failing. Here, Meridian's ₹31,710 headline is actually ₹2,231 dearer than the best offer.
> Fourth, *ShelfRank*. Hotels are ordered by deal value, quality, TBO's expected margin and supplier trust. The bar on each card shows why it is ranked where it is. Platinum hotels can be lifted, but only by up to three places, and the card says so.

### 2:15–2:45 · Sightseeing (Sightseeing tab)

> The same idea applies to sightseeing. Fifteen Burj Khalifa products from three suppliers become eight genuinely different experiences. Skip-the-line, prime-time, transfers, dinner and cancellation are read as separate parts, so a cheap ticket and a ticket with a transfer can be compared fairly.

### 2:45–3:30 · Safe to run (Review desk, then Supplier ledger)

> The expensive mistake is a wrong merge, because then you sell the wrong room. So TrueShelf merges automatically only when it is at least 90% sure. Uncertain pairs go to this review desk: 39 out of 102,100 candidate pairs, ordered by how much booking value depends on the answer. The model shows why it is unsure, and every decision is logged with who made it.
> The supplier ledger turns TBO's own booking outcomes into failure rates per supplier and city. A supplier with only fourteen bookings gets pulled towards the city average instead of a perfect score.

### 3:30–4:10 · Evidence (Evidence tab, then slide 3)

> We measured all of this honestly. Each city is scored by a model that never saw that city. Hotel matching F1 is 0.996, against 0.795 for the usual "similar name within 300 metres" rule, with 99.86% precision. Room mapping F1 is 0.996, against 0.21 for fuzzy matching.
> We also stress-tested a supplier whose naming style we had never seen. Recall dropped, but wrong merges stayed at zero, because anything the system can't read stays separate and goes to a person.
> One honest limit: the data is synthetic, since teams don't get TBO feeds. That's why our Round 2 plan starts with a shadow-mode pilot on one city's real feed.

### 4:10–4:45 · Adoption and close (Assumptions tab, move a slider, then slide 4)

> Every rupee assumption and every ranking weight is configuration. Move a slider and prices and rankings update live. TBO's commercial team stays in control, and agents still pay the real price; like-for-like only reorders and explains.
> TrueShelf is one hotel, one card, the true price, with the evidence attached. Thank you.

---

**Recording tips**
- Record at 1440×900 or 1920×1080, with the browser zoom at 100%.
- Keep the cursor still while you talk about a number, so viewers can read it.
- **3-minute cut:** drop the sightseeing section, the ledger paragraph and the stress-test sentence. That leaves about 450 words.

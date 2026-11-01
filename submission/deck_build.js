const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/b42d1b54-7457-410c-9dbe-73023ffe5d2c_9f9727a8-2561-43f9-aafc-54eb688abae1/pptx/scripts/apply_theme.js");

const THEME = {
  name: "TrueShelf",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: { dk1: "13202A", lt1: "FFFFFF", dk2: "3B4954", lt2: "F5F2EC", accent1: "D9481C", accent2: "0F7A63", accent3: "1D4E89",
    accent4: "A86A10", accent5: "6B7680", accent6: "B3261E", hlink: "1D4E89", folHlink: "6B7680" },
};
const HEX = { ink: "13202A", ink2: "3B4954", ink3: "6B7680", paper: "F5F2EC", line: "E2DCCF", accent: "D9481C", accentSoft: "FBE6DC",
  good: "0F7A63", goodSoft: "DCF0E9", warnSoft: "F8ECD2", blue: "1D4E89", blueSoft: "E1EBF6", white: "FFFFFF" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "Team vortexxx";
pres.title = "TrueShelf: VoyageHack 4.0 idea submission";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

pres.defineSlideMaster({ title: "DARK", background: { color: C.text1 }, objects: [] });
pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.background1 },
  objects: [
    { text: { text: "TrueShelf · team vortexxx · VoyageHack 4.0 · Multi-Supplier Optimization", options: { x: 0.5, y: 7.08, w: 8, h: 0.28, fontSize: 9, color: C.accent5, margin: 0 } } },
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.32, w: 12.3, h: 0.62, fontFace: "Cambria", fontSize: 28, bold: true, color: C.text1, margin: 0, valign: "top" }, text: "" } },
  ],
  slideNumber: { x: 12.4, y: 7.08, w: 0.45, h: 0.28, fontSize: 9, color: C.accent5, align: "right" },
});

const T = (slide, text, o) => slide.addText(text, { isTextBox: true, margin: 0, fontFace: "Calibri", color: C.text1, valign: "top", ...o });
const card = (slide, x, y, w, h, fill, name) => slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: HEX.line, width: 0.75 }, objectName: name });
const label = (slide, text, x, y, w, col = C.accent1) => T(slide, text.toUpperCase(), { x, y, w, h: 0.26, fontSize: 10.5, bold: true, color: col, charSpacing: 2 });
const img = (slide, path, x, y, w, pxW, pxH, name) => slide.addImage({ path, x, y, w, h: w * pxH / pxW, objectName: name, altText: name,
  shadow: { type: "outer", color: "13202A", blur: 6, offset: 2, angle: 90, opacity: 0.18 } });

// ======================================================= 1. COVER
pres.addSection({ title: "Cover" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Cover" });
  s.addImage({ path: "logo.png", x: 0.6, y: 0.62, w: 0.62, h: 0.525, objectName: "logo" });
  T(s, "TBO VOYAGEHACK 4.0  ·  IDEA SUBMISSION", { x: 1.38, y: 0.72, w: 5.5, h: 0.32, fontSize: 11, bold: true, color: "A9B3BA", charSpacing: 2 });
  T(s, "TrueShelf", { x: 0.6, y: 1.55, w: 6.2, h: 1.05, fontFace: "Cambria", fontSize: 60, bold: true, color: C.background1 });
  T(s, "Every supplier's version of the same hotel, room or experience: on one shelf, at its true price.",
    { x: 0.6, y: 2.72, w: 5.6, h: 1.0, fontSize: 20, color: "E6E1D6" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 3.95, w: 4.55, h: 0.44, rectRadius: 0.22, fill: { color: "24394A" }, line: { color: "2E4252", width: 0.75 }, objectName: "track pill" });
  T(s, "Track: Multi-Supplier Optimization (Hotels + Sightseeing)", { x: 0.78, y: 4.03, w: 4.3, h: 0.3, fontSize: 12.5, color: C.background1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.05, w: 1.42, h: 1.42, rectRadius: 0.08, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" }, objectName: "qr card" });
  s.addImage({ path: "qr.png", x: 0.66, y: 5.11, w: 1.3, h: 1.3, objectName: "QR code", altText: "QR code to the TrueShelf proof page" });
  T(s, [
    { text: "Team vortexxx", options: { bold: true, color: C.background1, breakLine: true } },
    { text: "Raktim Chandra (lead) · Nipun Dewangan · Pronov Mazumdar", options: { color: "C9D1D6", breakLine: true } },
    { text: "SRM Institute of Science and Technology, Chennai", options: { color: "A9B3BA" } },
  ], { x: 2.25, y: 5.05, w: 4.3, h: 1.45, fontSize: 13, paraSpaceAfter: 3 });
  T(s, "Scan: live prototype, 5-min walkthrough, all 36 tests, and our evaluation re-run in your own browser.", { x: 0.6, y: 6.65, w: 6.2, h: 0.5, fontSize: 11.5, italic: true, color: "E8633A" });
  // product shot
  s.addImage({ path: "full.png", x: 6.95, y: 0.72, w: 5.9, h: 4.097, sizing: { type: "crop", w: 5.9, h: 4.097 }, objectName: "product screenshot",
    altText: "TrueShelf hotel results for Dubai", shadow: { type: "outer", color: "000000", blur: 14, offset: 4, angle: 90, opacity: 0.45 } });
  img(s, "card.png", 6.6, 4.55, 6.25, 2088, 448, "shelf card");
  T(s, "One card per real hotel. Every supplier's offers inside. Like-for-like price up front.", { x: 6.6, y: 6.05, w: 6.25, h: 0.3, fontSize: 11, color: "A9B3BA", align: "right" });
}

// ======================================================= 2. PROBLEM / SOLUTION / INNOVATION
pres.addSection({ title: "Idea" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Idea" });
  s.addText("The cheapest headline is often not the cheapest deal", { placeholder: "title" });
  T(s, "TBO buys the same hotel, room and ticket from many suppliers. Each names, prices and packages it differently, and agents pay for the confusion.",
    { x: 0.5, y: 0.95, w: 12.3, h: 0.32, fontSize: 13, color: C.text2 });

  // --- column 1: problem
  const c1 = 0.5, w1 = 3.95, top = 1.5;
  label(s, "1 · Problem today", c1, top, w1);
  img(s, "raw.png", c1, top + 0.32, w1, 2088, 570, "raw supplier feed");
  T(s, "Today's feed: the same hotel up to 5×, sorted by a price that hides breakfast, cancellation terms and supplier risk.",
    { x: c1, y: top + 1.47, w: w1, h: 0.55, fontSize: 11, color: C.accent5, italic: true });
  const stat = (y, big, small, col) => {
    T(s, big, { x: c1, y, w: 1.6, h: 0.55, fontFace: "Cambria", fontSize: 26, bold: true, color: col });
    T(s, small, { x: c1 + 1.62, y: y + 0.02, w: w1 - 1.62, h: 0.62, fontSize: 11, color: C.text2, valign: "middle" });
  };
  stat(top + 2.15, "87%", "of TBO gross profit comes from hotels + ancillaries (Q2 FY26). Listing quality is a profit lever.", C.accent1);
  stat(top + 2.85, "2.9×", "supplier records per real hotel in our test world: 1,657 records collapse into 574 hotels.", C.accent1);
  stat(top + 3.55, "25–65%", "of rooms sold by 2+ offers, where the cheapest headline loses like-for-like (avg ₹1.1–1.4k).", C.accent1);
  T(s, "Synthetic data, held-out evaluation; see slide 3.", { x: c1, y: top + 4.28, w: w1, h: 0.25, fontSize: 9.5, color: C.accent5 });

  // --- column 2: solution layers
  const c2 = 4.8, w2 = 3.9;
  label(s, "2 · TrueShelf: four layers", c2, top, w2);
  const layers = [
    ["Same place?", "Cleans names (Qasr/Kasr, HTL/Hotel), blocks by geo + rare words, scores 23 signals with a calibrated model. Sister properties 150 m apart stay separate."],
    ["Same product?", "Room grammar reads class, bed, view; strips “Breakfast Included” leaked into names. Sightseeing split into atoms: access, transfer, meal, guide, cancellation."],
    ["Like-for-Like Price", "Turns meals, cancellation terms, pay-later and supplier failure risk into rupees. Every rupee shown, every assumption editable."],
    ["ShelfRank", "Orders hotels by deal value, quality, expected TBO margin and supplier trust. No clone-stacking; Platinum lift capped and visible."],
  ];
  layers.forEach(([h, d], i) => {
    const y = top + 0.36 + i * 0.99;
    card(s, c2, y, w2, 0.9, i === 2 ? HEX.accentSoft : HEX.paper, "layer " + (i + 1));
    s.addShape(pres.shapes.OVAL, { x: c2 + 0.14, y: y + 0.14, w: 0.36, h: 0.36, fill: { color: i === 2 ? HEX.accent : HEX.ink }, line: { color: i === 2 ? HEX.accent : HEX.ink }, objectName: "num " + (i + 1) });
    T(s, String(i + 1), { x: c2 + 0.14, y: y + 0.14, w: 0.36, h: 0.36, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle" });
    T(s, h, { x: c2 + 0.62, y: y + 0.09, w: w2 - 0.75, h: 0.26, fontSize: 13, bold: true });
    T(s, d, { x: c2 + 0.62, y: y + 0.34, w: w2 - 0.72, h: 0.52, fontSize: 9.8, color: C.text2 });
  });
  T(s, [{ text: "Plus: ", options: { bold: true } }, { text: "a Review Desk (people see only the 0.04% of uncertain pairs, ordered by booking value at risk) and a Supplier Reliability Ledger (Bayesian failure rates per supplier × city)." }],
    { x: c2, y: top + 4.4, w: w2, h: 0.6, fontSize: 10.5, color: C.text2 });

  // --- column 3: innovation
  const c3 = 9.05, w3 = 3.78;
  label(s, "3 · Innovation", c3, top, w3);
  img(s, "card.png", c3, top + 0.34, w3, 2088, 448, "shelf card");
  img(s, "wf.png", c3, top + 1.31, w3, 2024, 376, "like-for-like breakdown");
  const inn = [
    ["Offer-level, not just hotel-level.", " Hotel mapping can be bought. Comparing offers like-for-like, from TBO's own booking outcomes, cannot."],
    ["A price with receipts.", " Agents still pay the real price; L4L only reorders choices and explains why, in rupees."],
    ["Fails safe.", " Unreadable room names are never merged; a wrong merge sells the wrong bed."],
    ["No chatbot.", " Rules where rules work, small calibrated models where they don't. Cheap to run, easy to audit."],
  ];
  T(s, inn.flatMap(([b, t], i) => [{ text: b, options: { bold: true, color: C.text1 } }, { text: t, options: { color: C.text2, breakLine: i < inn.length - 1 } }]),
    { x: c3, y: top + 2.12, w: w3, h: 2.55, fontSize: 10.8, paraSpaceAfter: 5 });
  s.addNotes("Problem, solution and innovation. Numbers are from the working prototype on synthetic data with leave-one-city-out evaluation.");
}

// ======================================================= 3. IMPACT / FEASIBILITY / ADOPTION
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Idea" });
  s.addText("Measured, explainable, and safe to switch on", { placeholder: "title" });
  T(s, "Every number below comes from the running prototype. Hotel matching is held-out: each city is scored by a model trained only on the other two.",
    { x: 0.5, y: 0.95, w: 12.3, h: 0.32, fontSize: 13, color: C.text2 });
  const top = 1.5;

  // --- column 1: impact
  const c1 = 0.5, w1 = 3.95;
  label(s, "Potential impact", c1, top, w1);
  const big = (y, v, l, col) => {
    T(s, v, { x: c1, y, w: w1, h: 0.55, fontFace: "Cambria", fontSize: 30, bold: true, color: col });
    T(s, l, { x: c1, y: y + 0.55, w: w1, h: 0.42, fontSize: 11, color: C.text2 });
  };
  big(top + 0.3, "0.996  vs  0.795", "Hotel matching F1, held-out, no human, vs the usual “similar name + within 300 m” rule (precision 99.86%).", C.accent2);
  big(top + 1.35, "0.996  vs  0.21", "Room mapping F1 vs fuzzy room-name matching; sightseeing product matching F1 0.996.", C.accent2);
  T(s, [
    { text: "Agents: ", options: { bold: true } }, { text: "one card per hotel instead of up to five; the real best deal is visible in seconds.", options: { breakLine: true } },
    { text: "TBO margin: ", options: { bold: true } }, { text: "ranking weighs expected gross profit and booking success, not headline price alone.", options: { breakLine: true } },
    { text: "Fewer failed bookings: ", options: { bold: true } }, { text: "supplier risk is priced in before the agent books.", options: { breakLine: true } },
    { text: "Supply team: ", options: { bold: true } }, { text: "per-supplier data-quality report (e.g. 30% of one feed's room names carry rate-plan words)." },
  ], { x: c1, y: top + 2.48, w: w1, h: 2.3, fontSize: 11, color: C.text2, paraSpaceAfter: 5 });

  // --- column 2: feasibility
  const c2 = 4.8, w2 = 3.9;
  label(s, "Implementation & technical feasibility", c2, top, w2);
  const steps = ["Supplier feeds", "Clean", "Block", "Score", "Cluster", "Rooms", "L4L", "Rank"];
  steps.forEach((t, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = c2 + col * 0.99, y = top + 0.36 + row * 0.62;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.86, h: 0.44, rectRadius: 0.06, fill: { color: i >= 6 ? HEX.accentSoft : HEX.blueSoft }, line: { color: i >= 6 ? "F0C2AE" : "C5D7EC", width: 0.75 }, objectName: "step " + t });
    T(s, t, { x, y, w: 0.86, h: 0.44, fontSize: 10, bold: true, align: "center", valign: "middle", color: i >= 6 ? "7D2A0F" : "163D6B" });
    if (col < 3) T(s, "→", { x: x + 0.855, y, w: 0.14, h: 0.44, fontSize: 10, color: C.accent5, align: "center", valign: "middle" });
  });
  const rows = [["", "Records", "F1", "Rule F1"], ["Dubai", "651", "0.999", "0.806"], ["Bangkok", "605", "0.993", "0.755"], ["Paris", "401", "0.996", "0.824"]];
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: i === 0 || (j === 2 && i > 0), color: i === 0 ? HEX.ink3 : j === 2 ? HEX.good : HEX.ink, align: j === 0 ? "left" : "right", fontSize: 10.5, fill: { color: i === 0 ? HEX.paper : HEX.white } } }))),
    { x: c2, y: top + 1.72, w: w2, colW: [1.3, 0.85, 0.85, 0.9], rowH: 0.27, border: { type: "solid", pt: 0.5, color: HEX.line }, fontFace: "Calibri", margin: [0.03, 0.08, 0.03, 0.08], objectName: "held-out table" });
  T(s, [
    { text: "Offline: ", options: { bold: true } }, { text: "mapping re-runs per city when a feed changes (blocking never crosses cities, so it shards by destination).", options: { breakLine: true } },
    { text: "Online: ", options: { bold: true } }, { text: "at search time it is a table join plus arithmetic. Booking still uses the supplier's own codes.", options: { breakLine: true } },
    { text: "Built: ", options: { bold: true } }, { text: "Python, scikit-learn, RapidFuzz, FastAPI, plain-JS UI; 36 tests, including a check that browser and engine agree to the rupee. Full pipeline in 15 s on one CPU." },
  ], { x: c2, y: top + 2.95, w: w2, h: 1.8, fontSize: 10.5, color: C.text2, paraSpaceAfter: 5 });

  // --- column 3: adoption risk
  const c3 = 9.05, w3 = 3.78;
  label(s, "Adoption risk & how we de-risk it", c3, top, w3);
  const risks = [
    ["A wrong merge sells the wrong room", "Merge only at p ≥ 0.90; 0.30–0.90 goes to a person. Unreadable names never merge."],
    ["Agents distrust a “made-up” price", "They still see and pay the real price. L4L is a labelled comparison with every rupee itemised."],
    ["Commercial deals bend ranking", "Platinum lift is a setting, capped at 3 places and shown on the card."],
    ["Assumptions may be wrong", "All are versioned config with live what-if sliders, then replaced by values from TBO's booking data."],
    ["Synthetic data ≠ real feeds", "Round 2: shadow-mode pilot on one city's real feed, then A/B on conversion."],
  ];
  risks.forEach(([r, m], i) => {
    const y = top + 0.36 + i * 0.89;
    card(s, c3, y, w3, 0.8, i % 2 ? HEX.white : HEX.paper, "risk " + (i + 1));
    T(s, r, { x: c3 + 0.14, y: y + 0.07, w: w3 - 0.28, h: 0.25, fontSize: 11, bold: true, color: C.accent6 });
    T(s, m, { x: c3 + 0.14, y: y + 0.32, w: w3 - 0.28, h: 0.46, fontSize: 10, color: C.text2 });
  });
  s.addNotes("Impact, feasibility and adoption risk. Rollout path: shadow mode, then an A/B test in one city, then expand.");
}

// ======================================================= 4. THANK YOU
pres.addSection({ title: "Close" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
  s.addImage({ path: "logo.png", x: 0.6, y: 0.62, w: 0.62, h: 0.525, objectName: "logo" });
  T(s, "Thank you", { x: 0.6, y: 1.5, w: 6, h: 1.0, fontFace: "Cambria", fontSize: 54, bold: true, color: C.background1 });
  T(s, "One hotel, one card, the true price, with the evidence attached.", { x: 0.6, y: 2.55, w: 6, h: 0.8, fontSize: 20, color: "E6E1D6" });
  T(s, [
    { text: "Already built for Round 2", options: { bold: true, color: "E8633A", breakLine: true } },
    { text: "Six-screen working prototype: hotel shelves, sightseeing, review desk, supplier ledger, evidence, live assumptions", options: { bullet: true, breakLine: true } },
    { text: "REST API: search, match, like-for-like, review decisions", options: { bullet: true, breakLine: true } },
    { text: "Held-out evaluation, an unseen-supplier stress test and 36 automated tests", options: { bullet: true, breakLine: true } },
    { text: "A proof page that re-runs our evaluation in the judge's own browser", options: { bullet: true } },
  ], { x: 0.6, y: 3.75, w: 6.2, h: 1.9, fontSize: 14, color: "D6DCE0", paraSpaceAfter: 6 });
  T(s, "Team vortexxx · Raktim Chandra · raktimchandra26@gmail.com · +91 98322 88101", { x: 0.6, y: 6.55, w: 8, h: 0.35, fontSize: 12, color: "A9B3BA" });
  img(s, "review.png", 7.3, 0.9, 5.5, 1936, 1122, "review desk");
  T(s, "Review desk: a person sees only the pairs the model is unsure about, with the reasons.", { x: 7.3, y: 4.2, w: 5.5, h: 0.5, fontSize: 11, color: "A9B3BA" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.3, y: 4.95, w: 1.62, h: 1.62, rectRadius: 0.08, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" }, objectName: "qr card" });
  s.addImage({ path: "qr.png", x: 7.36, y: 5.01, w: 1.5, h: 1.5, objectName: "QR code", altText: "QR code to the TrueShelf proof page" });
  T(s, [
    { text: "Don't trust the slides. Run them.", options: { bold: true, color: "E8633A", breakLine: true } },
    { text: "Scan to open the proof page. It re-runs our Paris held-out evaluation inside your browser: no server, nothing precomputed. Plus the live prototype, the video and all 36 tests.", options: { color: "D6DCE0" } },
  ], { x: 9.15, y: 4.98, w: 3.65, h: 1.6, fontSize: 12, paraSpaceAfter: 4 });
}

(async () => {
  await pres.writeFile({ fileName: "TrueShelf_vortexxx_VoyageHack4.pptx" });
  await applyTheme("TrueShelf_vortexxx_VoyageHack4.pptx", THEME);
  console.log("done");
})();

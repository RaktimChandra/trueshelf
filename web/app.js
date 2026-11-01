/* TrueShelf front-end. Vanilla JS, no build step.
   L4L and ShelfRank are re-implemented here so that the Assumptions page can
   re-price and re-rank live; tests/test_js_parity.py checks this file gives the
   same answers as the Python engine for the default configuration. */
(function () {
  "use strict";
  const D = window.TS_DATA;
  const $ = (s, el = document) => el.querySelector(s);
  const h = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const inr = (v) => "₹" + Math.round(v).toLocaleString("en-IN");
  const pct = (v, d = 1) => (100 * v).toFixed(d) + "%";
  // Python's round(): banker's rounding, so browser and engine agree to the rupee.
  const pyRound = (x) => { const f = Math.floor(x), d = x - f; if (Math.abs(d - 0.5) < 1e-9) return f % 2 === 0 ? f : f + 1; return Math.round(x); };
  const SUPCOL = { ATL: "#1d4e89", MER: "#b5651d", BLU: "#2a7f8f", SAH: "#8a6d1d", ORL: "#7a3e8f" };
  const supName = (c) => (D.suppliers[c] || {}).name || c;

  // ------------------------------------------------------------ params (editable)
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const DEFAULTS = { l4l: clone(D.config.l4l), rank: clone(D.config.rank) };
  const P = clone(DEFAULTS);
  const NIGHTS = D.config.nights, ADULTS = D.config.occupancy_adults, LEAD = D.config.lead_days;

  // ------------------------------------------------------------ L4L (mirror of trueshelf/l4l.py)
  function lateShare(days, p) {
    if (days === null || days === undefined) return 1.0;
    let best = 0.0;
    Object.keys(p.late_cancel_share).map(Number).sort((a, b) => a - b).forEach((k) => { if (k <= days) best = p.late_cancel_share[String(k)]; });
    return best;
  }
  function l4l(o, stars, rel, p) {
    const price = o.sell;
    let s = Math.min(5, Math.max(2, pyRound(stars || 3)));
    let meals = 0;
    if (o.board === "BB" || o.board === "HB") meals += p.breakfast_pp_by_star[String(s)] * ADULTS * NIGHTS;
    if (o.board === "HB") meals += p.dinner_pp_by_star[String(s)] * ADULTS * NIGHTS;
    let exposure, share;
    if (o.cancel === null || o.cancel === undefined) { exposure = p.nr_loss_fraction; share = 1.0; } else { exposure = 1.0; share = lateShare(o.cancel, p); }
    const ref = lateShare(7, p);
    const cancel = p.p_cancel * price * (exposure * share - ref);
    let paylater = 0;
    if (o.paylater && o.cancel !== null && o.cancel !== undefined) paylater = price * p.annual_cost_of_capital * Math.max(0, LEAD - o.cancel) / 365;
    let fail = 0;
    if (rel) {
      const pj = rel.price_jump.mean, cf = rel.confirm_fail.mean + rel.supplier_cancel.mean;
      fail = pj * p.avg_price_jump * price + cf * (p.reaccommodation_premium * price + p.failure_handling_cost);
    }
    const total = price - meals + cancel - paylater + fail;
    return { price: pyRound(price), meals: pyRound(-meals), cancellation: pyRound(cancel), pay_later: pyRound(-paylater), supplier_risk: pyRound(fail), l4l: pyRound(total) };
  }

  // ------------------------------------------------------------ ShelfRank (mirror of trueshelf/shelfrank.py)
  function pctRank(vals) {
    const order = vals.map((v, i) => i).sort((a, b) => vals[a] - vals[b]);
    const out = new Array(vals.length).fill(0);
    order.forEach((i, r) => (out[i] = r / Math.max(1, vals.length - 1)));
    return out;
  }
  function scoreShelves(shelves, rp) {
    const byStar = {};
    shelves.forEach((s, i) => (byStar[s.stars] = byStar[s.stars] || []).push(i));
    const value = new Array(shelves.length).fill(0);
    Object.values(byStar).forEach((idx) => {
      const r = pctRank(idx.map((i) => shelves[i].best.l4l_per_night));
      idx.forEach((i, j) => (value[i] = 1 - r[j]));
    });
    const gmax = Math.max(...shelves.map((s) => s.best.exp_gp)) || 1;
    shelves.forEach((s, i) => {
      const quality = 0.45 * (s.stars - 2) / 3 + 0.35 * (s.review_score - 6) / 4 + 0.20 * s.content_score;
      const trust = 1 - Math.min(1, s.best.p_fail / 0.12);
      const parts = { value: rp.w_value * value[i], quality: rp.w_quality * quality, margin: rp.w_margin * s.best.exp_gp / gmax, trust: rp.w_trust * trust };
      s.score_parts = parts;
      s.score = Object.values(parts).reduce((a, b) => a + b, 0);
      s.score = Math.round(s.score * 1e4) / 1e4;
    });
    return shelves;
  }
  const sim = (a, b) => {
    const p1 = a.best.l4l_per_night, p2 = b.best.l4l_per_night;
    return 0.5 * (a.area === b.area) + 0.3 * (Math.abs(p1 - p2) / Math.max(p1, p2) < 0.12) + 0.2 * (a.stars === b.stars);
  };
  function rankShelves(shelves, rp) {
    const pool = shelves.slice().sort((a, b) => b.score - a.score);
    const chosen = [];
    while (pool.length && chosen.length < 60) {
      let bi = 0, bv = -1e9;
      const lim = Math.min(40, pool.length);
      for (let i = 0; i < lim; i++) {
        const s = pool[i];
        const recent = chosen.slice(-8);
        const div = recent.length ? Math.max(...recent.map((c) => sim(s, c))) : 0;
        const v = s.score - rp.diversity_lambda * div * 0.1;
        if (v > bv) { bi = i; bv = v; }
      }
      chosen.push(pool.splice(bi, 1)[0]);
    }
    chosen.push(...pool);
    chosen.forEach((s) => (s._lifted = undefined));
    for (let pos = 0; pos < chosen.length; pos++) {
      const s = chosen[pos];
      if (s.platinum && s._lifted === undefined) {
        const nw = Math.max(0, pos - rp.platinum_max_lift);
        s._lifted = pos - nw;
        chosen.splice(nw, 0, chosen.splice(pos, 1)[0]);
      }
    }
    chosen.forEach((s, i) => { s.rank = i + 1; s.platinum_lift = s._lifted || 0; delete s._lifted; });
    return chosen;
  }

  // ------------------------------------------------------------ recompute a city's shelves under params + filters
  const state = { city: "DXB", view: "hotels", mode: "shelf", sort: "rank", open: null, dtab: "rooms", selOffer: null, f: { stars: new Set(), areas: new Set(), freeCancel: false, breakfast: false, hideC: false }, rv: 0, rvDone: {}, ssAttr: null };
  const cache = {};
  function relOf(sup, city) { return D.reliability[sup + "|" + city]; }
  function offerAllowed(o, city) {
    if (state.f.freeCancel && (o.cancel === null || o.cancel === undefined)) return false;
    if (state.f.breakfast && o.board === "RO") return false;
    if (state.f.hideC) { const r = relOf(o.sup, city); if (r && r.grade === "C") return false; }
    return true;
  }
  function recompute(city) {
    const src = D.search[city].shelves.slice().sort((a, b) => a.ord - b.ord);
    const out = [];
    src.forEach((s0) => {
      if (state.f.stars.size && !state.f.stars.has(s0.stars)) return;
      if (state.f.areas.size && !state.f.areas.has(s0.area)) return;
      const rooms = [];
      s0.rooms.forEach((r0) => {
        const offs = r0.offers.filter((o) => offerAllowed(o, city)).map((o) => ({ ...o, l4l: l4l(o, s0.stars, relOf(o.sup, city), P.l4l) }));
        if (!offs.length) return;
        offs.sort((a, b) => a.l4l.l4l - b.l4l.l4l);
        rooms.push({ ...r0, offers: offs, best_l4l: offs[0].l4l.l4l, min_sell: Math.min(...offs.map((o) => o.sell)) });
      });
      if (!rooms.length) return;
      rooms.sort((a, b) => a.best_l4l - b.best_l4l);
      const all = rooms.flatMap((r) => r.offers);
      let best = all[0], cheapest = all[0];
      all.forEach((o) => { if (o.l4l.l4l < best.l4l.l4l) best = o; if (o.sell < cheapest.sell) cheapest = o; });
      const bestRoom = rooms.find((r) => r.offers.some((o) => o.id === best.id));
      out.push({ ...s0, rooms, n_offers: all.length,
        cheapest: { id: cheapest.id, sell: cheapest.sell, l4l: cheapest.l4l.l4l, sup: cheapest.sup },
        best: { id: best.id, sup: best.sup, sell: best.sell, l4l: best.l4l.l4l, l4l_per_night: best.l4l.l4l / NIGHTS, room: bestRoom.label, p_fail: best.p_fail, exp_gp: pyRound((best.sell - best.net) * (1 - best.p_fail)) } });
    });
    const ranked = out.length ? rankShelves(scoreShelves(out, P.rank), P.rank) : [];
    cache[city] = ranked;
    return ranked;
  }
  window.TS_ENGINE = { l4l, recompute, P, DEFAULTS, pyRound }; // exposed for the parity test

  // ------------------------------------------------------------ procedural facade art (no stock photos)
  function hash(s) { let x = 2166136261; for (const c of s) { x ^= c.charCodeAt(0); x = Math.imul(x, 16777619); } return x >>> 0; }
  function facade(id, stars, city) {
    let r = hash(id);
    const rnd = () => ((r = Math.imul(r ^ (r >>> 15), 2246822507) >>> 0) % 1000) / 1000;
    const pal = { DXB: ["#f1d3a6", "#e9b980", "#c98a52", "#5a3b2a"], BKK: ["#cfe3da", "#9cc7b6", "#4f8f7c", "#22463d"], PAR: ["#dfe2ea", "#b9c0d1", "#7a86a3", "#2e3550"] }[city];
    let svg = `<svg viewBox="0 0 132 104" width="132" height="104" xmlns="http://www.w3.org/2000/svg"><rect width="132" height="104" fill="${pal[0]}"/>`;
    svg += `<circle cx="${20 + rnd() * 90}" cy="${18 + rnd() * 10}" r="${7 + rnd() * 6}" fill="#fff" opacity=".55"/>`;
    const n = 2 + Math.floor(rnd() * 3);
    let x = 4 + rnd() * 8;
    for (let i = 0; i < n && x < 124; i++) {
      const w = 18 + rnd() * 26, hh = 26 + rnd() * (18 + stars * 11), y = 92 - hh, col = pal[1 + Math.floor(rnd() * 2)];
      svg += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${hh.toFixed(1)}" fill="${col}"/>`;
      if (city === "PAR") svg += `<path d="M${x - 1} ${y} L${x + w / 2} ${y - 7} L${x + w + 1} ${y} Z" fill="${pal[3]}" opacity=".55"/>`;
      if (city === "DXB" && rnd() > 0.6) svg += `<path d="M${x + w / 2} ${y - 14} L${x + w / 2 + 3} ${y} L${x + w / 2 - 3} ${y} Z" fill="${col}"/>`;
      for (let wy = y + 5; wy < 88; wy += 7) for (let wx = x + 3; wx < x + w - 4; wx += 6) svg += `<rect x="${wx.toFixed(1)}" y="${wy.toFixed(1)}" width="3" height="3.5" fill="${pal[3]}" opacity="${(0.25 + rnd() * 0.5).toFixed(2)}"/>`;
      x += w + 2 + rnd() * 6;
    }
    if (city === "DXB" || city === "BKK") { const px = 10 + rnd() * 110; svg += `<path d="M${px} 92 q2 -14 0 -22" stroke="${pal[3]}" stroke-width="2" fill="none"/><path d="M${px} 70 q-9 -2 -12 4 M${px} 70 q9 -2 12 4 M${px} 70 q-4 -7 -9 -7 M${px} 70 q4 -7 9 -7" stroke="${pal[3]}" stroke-width="1.6" fill="none"/>`; }
    svg += `<rect y="92" width="132" height="12" fill="${pal[3]}" opacity=".85"/></svg>`;
    return svg;
  }

  // ------------------------------------------------------------ small UI helpers
  const starStr = (n) => "★".repeat(n) + "☆".repeat(Math.max(0, 5 - n));
  const boardLbl = { RO: "Room only", BB: "Breakfast", HB: "Half board" };
  const cancelLbl = (c) => (c === null || c === undefined ? "Non-refundable" : `Free cancel until ${c}d before`);
  function diffChips(o, ref) {
    const c = [];
    if (o.board !== ref.board) c.push(`<span class="chip ${o.board === "RO" ? "warn" : "good"}">${boardLbl[o.board]}</span>`);
    if ((o.cancel ?? -1) !== (ref.cancel ?? -1)) c.push(`<span class="chip ${o.cancel === null ? "bad" : "good"}">${o.cancel === null ? "Non-refundable" : "Free cancel " + o.cancel + "d"}</span>`);
    if (o.paylater !== ref.paylater) c.push(`<span class="chip ${o.paylater ? "good" : "warn"}">${o.paylater ? "Pay later" : "Pay now"}</span>`);
    if (o.sup !== ref.sup) { const g = (relOf(o.sup, state.city) || {}).grade; if (g && g !== "A") c.push(`<span class="chip ${g === "C" ? "bad" : "warn"}">Supplier grade ${g}</span>`); }
    if (o.leaks && o.leaks.length) c.push(`<span class="chip blue" title="Supplier wrote rate-plan words into the room name; stripped before matching">name had “${o.leaks.join(", ")}”</span>`);
    return c.join("");
  }
  function searchChip() { $("#searchChip").textContent = `${D.cities[state.city]} · ${ADULTS} adults · ${NIGHTS} nights · check-in in ${LEAD} days`; }

  // ------------------------------------------------------------ tabs
  const TABS = [["hotels", "Hotels"], ["ss", "Sightseeing"], ["review", "Review desk"], ["ledger", "Supplier ledger"], ["evidence", "Evidence"], ["assume", "Assumptions"]];
  function renderTabs() {
    const t = $("#tabs");
    t.innerHTML = TABS.map(([k, l]) => `<button class="tab ${state.view === k ? "on" : ""}" data-v="${k}">${l}${k === "review" ? ` <span class="mono" style="opacity:.7">${D.review.filter((r) => !state.rvDone[r.pair]).length}</span>` : ""}</button>`).join("");
    t.querySelectorAll("button").forEach((b) => (b.onclick = () => { state.view = b.dataset.v; render(); window.scrollTo(0, 0); }));
  }

  // ------------------------------------------------------------ HOTELS
  function renderHotels(app) {
    const S = D.search[state.city];
    const shelves = recompute(state.city);
    const areas = [...new Set(S.shelves.map((s) => s.area))].sort();
    const nRooms = S.shelves.reduce((a, s) => a + s.rooms.length, 0);
    const rc = S.room_compare;
    app.innerHTML = "";
    const g = h(`<div class="grid-hotels"></div>`);
    const rail = h(`<aside class="panel rail">
      <div class="sec funnel"><h4>What TrueShelf did</h4>
        <div class="row"><span>Supplier hotel records</span><span class="big">${S.raw.length}</span></div>
        <div class="arrow">↓ matched across ${Object.keys(D.suppliers).length} suppliers</div>
        <div class="row"><span>Hotel listings</span><span class="big">${S.shelves.length}</span></div>
        <div class="row" style="margin-top:6px"><span>Live offers</span><span class="big">${S.n_offers.toLocaleString("en-IN")}</span></div>
        <div class="arrow">↓ grouped into canonical rooms</div>
        <div class="row"><span>Room options</span><span class="big">${nRooms.toLocaleString("en-IN")}</span></div>
        <div class="note" style="margin-top:8px">In <b>${pct(rc.cheapest_not_best / rc.rooms_multi_offer, 0)}</b> of rooms sold by 2+ offers, the cheapest headline was <i>not</i> the best like-for-like deal (avg gap ${inr(rc.l4l_gap_sum / Math.max(1, rc.cheapest_not_best))}).</div>
      </div>
      <div class="sec"><h4>Stars</h4>${[5, 4, 3, 2].map((s) => `<label class="check"><input type="checkbox" data-star="${s}" ${state.f.stars.has(s) ? "checked" : ""}> <span class="stars">${starStr(s)}</span></label>`).join("")}</div>
      <div class="sec"><h4>Area</h4>${areas.map((a) => `<label class="check"><input type="checkbox" data-area="${esc(a)}" ${state.f.areas.has(a) ? "checked" : ""}> ${esc(a)}</label>`).join("")}</div>
      <div class="sec"><h4>Offer rules</h4>
        <label class="check"><input type="checkbox" id="fFree" ${state.f.freeCancel ? "checked" : ""}> Free cancellation only</label>
        <label class="check"><input type="checkbox" id="fBB" ${state.f.breakfast ? "checked" : ""}> Meals included</label>
        <label class="check"><input type="checkbox" id="fC" ${state.f.hideC ? "checked" : ""}> Hide grade C suppliers</label>
      </div></aside>`);
    g.appendChild(rail);
    const main = h(`<section></section>`);
    const nDup = S.raw.length - new Set(S.raw.map((r) => r.listing)).size;
    main.appendChild(h(`<div class="headrow"><div><h1>Hotels in ${esc(D.cities[state.city])}</h1>
      <p>${state.mode === "shelf" ? `${shelves.length} hotels · one card per real property, every supplier's offers inside` : `${S.raw.length} cards from the supplier feed · ${nDup} are repeats of a hotel already listed`}</p></div>
      <div style="display:flex;gap:10px;align-items:center">
        ${state.mode === "shelf" ? `<select class="select" style="background:#fff;color:var(--ink);border-color:var(--line)" id="sortSel"><option value="rank">Sort: TrueShelf rank</option><option value="l4l">Sort: like-for-like price</option><option value="head">Sort: cheapest headline</option></select>` : ""}
        <div class="seg"><button data-m="raw" class="${state.mode === "raw" ? "on" : ""}">Supplier feed (today)</button><button data-m="shelf" class="${state.mode === "shelf" ? "on" : ""}">TrueShelf</button></div></div></div>`));
    if (state.mode === "raw") renderRaw(main, S);
    else renderShelfList(main, shelves);
    g.appendChild(main);
    app.appendChild(g);
    rail.querySelectorAll("[data-star]").forEach((c) => (c.onchange = () => { const v = +c.dataset.star; c.checked ? state.f.stars.add(v) : state.f.stars.delete(v); render(); }));
    rail.querySelectorAll("[data-area]").forEach((c) => (c.onchange = () => { const v = c.dataset.area; c.checked ? state.f.areas.add(v) : state.f.areas.delete(v); render(); }));
    $("#fFree").onchange = (e) => { state.f.freeCancel = e.target.checked; render(); };
    $("#fBB").onchange = (e) => { state.f.breakfast = e.target.checked; render(); };
    $("#fC").onchange = (e) => { state.f.hideC = e.target.checked; render(); };
    main.querySelectorAll(".seg button").forEach((b) => (b.onclick = () => { state.mode = b.dataset.m; render(); }));
    const ss = $("#sortSel"); if (ss) { ss.value = state.sort; ss.onchange = () => { state.sort = ss.value; render(); }; }
  }

  function renderRaw(main, S) {
    const counts = {};
    S.raw.forEach((r) => (counts[r.listing] = (counts[r.listing] || 0) + 1));
    main.appendChild(h(`<div class="banner warn"><b>Today’s view.</b> Each supplier record is its own card, sorted by cheapest headline price. The coloured stripe shows cards that are really the same hotel; the price shown hides breakfast, cancellation and supplier risk.</div>`));
    const list = h(`<div></div>`);
    S.raw.slice(0, 80).forEach((r) => {
      const col = `hsl(${hash(r.listing) % 360} 55% 58%)`;
      const dup = counts[r.listing] > 1 ? `<span class="dupbadge">same hotel ×${counts[r.listing]}</span>` : "";
      list.appendChild(h(`<div class="rawcard"><div class="stripe" style="background:${counts[r.listing] > 1 ? col : "transparent"}"></div>
        <div><div class="n">${esc(r.name)} ${dup}</div><div class="s"><span class="chip sup" style="border-color:${SUPCOL[r.sup]};color:${SUPCOL[r.sup]}">${r.sup}</span> ${r.stars ?? "?"}★ · <span class="raw">${esc(r.room)}</span> · ${boardLbl[r.board]} · ${cancelLbl(r.cancel)}</div></div>
        <div class="r"><div class="mono" style="font-size:17px;font-weight:600">${inr(r.sell)}</div><div class="s">${NIGHTS} nights, headline</div></div></div>`));
    });
    main.appendChild(list);
    main.appendChild(h(`<div class="note" style="padding:8px 2px">Showing the first 80 of ${S.raw.length} cards.</div>`));
  }

  function renderShelfList(main, shelves) {
    let list = shelves.slice();
    if (state.sort === "l4l") list.sort((a, b) => a.best.l4l - b.best.l4l);
    if (state.sort === "head") list.sort((a, b) => a.cheapest.sell - b.cheapest.sell);
    if (!list.length) { main.appendChild(h(`<div class="panel empty">No hotel has an offer that passes these filters. Loosen a filter on the left.</div>`)); return; }
    main.appendChild(h(`<div class="legend" style="margin:0 0 10px 2px"><span><i style="background:#2c6e9b"></i>value</span><span><i style="background:#8a6db0"></i>quality</span><span><i style="background:#c7892b"></i>TBO margin</span><span><i style="background:#2f8f6f"></i>supplier trust</span><span>— bar shows why a hotel is ranked where it is</span></div>`));
    list.slice(0, 40).forEach((s) => main.appendChild(shelfCard(s)));
    if (list.length > 40) main.appendChild(h(`<div class="note" style="padding:8px 2px">Showing 40 of ${list.length} hotels.</div>`));
  }

  function shelfCard(s) {
    const tot = Object.values(s.score_parts).reduce((a, b) => a + b, 0) || 1;
    const col = { value: "#2c6e9b", quality: "#8a6db0", margin: "#c7892b", trust: "#2f8f6f" };
    const trap = s.cheapest.id !== s.best.id && s.cheapest.l4l > s.best.l4l
      ? `<div class="trap">Cheapest headline ${inr(s.cheapest.sell)} (${s.cheapest.sup}) is really <b>${inr(s.cheapest.l4l - s.best.l4l)}</b> dearer like-for-like</div>` : "";
    const g = (relOf(s.best.sup, state.city) || {}).grade || "B";
    const open = state.open === s.id;
    const el = h(`<article class="card ${open ? "open" : ""}" id="c-${s.id}">
      <div class="facade">${facade(s.id, s.stars, state.city)}</div>
      <div>
        <div class="meta"><span class="mono" style="color:var(--ink)">#${s.rank}</span>${s.platinum_lift ? `<span class="chip plat" title="Commercial lift, capped at ${P.rank.platinum_max_lift} places">Platinum · lifted ${s.platinum_lift}</span>` : s.platinum ? `<span class="chip plat">Platinum</span>` : ""}</div>
        <h3>${esc(s.name)}</h3>
        <div class="meta"><span class="stars">${starStr(s.stars)}</span><span>${esc(s.area)}</span><span>Guest score ${s.review_score}</span>${s.chain ? `<span>${esc(s.chain)}</span>` : ""}</div>
        <div class="chips">${s.suppliers.map((c) => `<span class="chip sup" style="border-color:${SUPCOL[c]}55;color:${SUPCOL[c]}" title="${esc(supName(c))}">${c}</span>`).join("")}
          <span class="chip">${s.records.length} supplier records → 1 hotel</span><span class="chip">${s.rooms.length} rooms · ${s.n_offers} offers</span></div>
        <div class="rankwhy"><span class="stack">${Object.entries(s.score_parts).map(([k, v]) => `<i style="width:${(100 * v / tot).toFixed(1)}%;background:${col[k]}"></i>`).join("")}</span> score ${s.score.toFixed(3)}</div>
      </div>
      <div class="pricebox">
        <div><div class="lbl">Like-for-like from</div><div class="l4l">${inr(s.best.l4l / NIGHTS)}<span class="per"> /night</span></div>
          <div class="head">${esc(s.best.room)} · ${s.best.sup} <span class="grade ${g}" style="width:18px;height:18px;line-height:18px;font-size:10.5px">${g}</span></div>
          <div class="head">Pays ${inr(s.best.sell)} for ${NIGHTS} nights</div>${trap}</div>
        <div style="margin-top:10px"><button class="btn ${open ? "" : "ghost"}" data-open>${open ? "Close" : "Compare offers"}</button></div>
      </div></article>`);
    el.querySelector("[data-open]").onclick = () => { state.open = open ? null : s.id; state.selOffer = null; state.dtab = "rooms"; render(); setTimeout(() => { const c = $("#c-" + s.id); if (c && !open) c.scrollIntoView({ behavior: "smooth", block: "start" }); }, 30); };
    if (open) el.appendChild(detail(s));
    return el;
  }

  function detail(s) {
    const d = h(`<div class="detail"><div class="dtabs"><button data-t="rooms">Rooms & offers</button><button data-t="same">Why this is one hotel</button><button data-t="rank">Why rank #${s.rank}</button></div><div class="dbody"></div></div>`);
    d.querySelectorAll(".dtabs button").forEach((b) => { if (b.dataset.t === state.dtab) b.classList.add("on"); b.onclick = () => { state.dtab = b.dataset.t; render(); }; });
    const body = d.querySelector(".dbody");
    if (state.dtab === "rooms") body.appendChild(roomsView(s));
    if (state.dtab === "same") body.appendChild(sameView(s));
    if (state.dtab === "rank") body.appendChild(rankView(s));
    return d;
  }

  function roomsView(s) {
    const w = h(`<div></div>`);
    s.rooms.forEach((r) => {
      const ref = r.offers[0];
      const box = h(`<div class="room"><div class="room-h"><span>${esc(r.label)}<span class="sub">${r.suppliers.length} supplier${r.suppliers.length > 1 ? "s" : ""} named this room ${new Set(r.offers.map((o) => o.raw)).size} different ways</span></span><span class="mono">from ${inr(r.best_l4l / NIGHTS)}/night like-for-like</span></div>
        <table class="t"><thead><tr><th>Supplier</th><th>Supplier's room name</th><th>Terms</th><th class="r">Pays</th><th class="r">Like-for-like</th><th>Differences vs best</th></tr></thead><tbody></tbody></table></div>`);
      const tb = box.querySelector("tbody");
      r.offers.slice(0, 8).forEach((o, i) => {
        const tr = h(`<tr class="clickable ${state.selOffer === o.id ? "sel" : ""}"><td><span class="chip sup" style="border-color:${SUPCOL[o.sup]}55;color:${SUPCOL[o.sup]}">${o.sup}</span></td>
          <td class="raw">${esc(o.raw)}</td><td>${boardLbl[o.board]} · ${o.cancel === null ? "Non-ref" : "Free " + o.cancel + "d"}${o.paylater ? " · Pay later" : ""}</td>
          <td class="r mono">${inr(o.sell)}</td><td class="r mono"><b>${inr(o.l4l.l4l)}</b>${i === 0 ? '<div class="best-tag">best deal</div>' : ""}</td>
          <td><div class="chips" style="margin:0">${i === 0 ? '<span class="note">reference</span>' : diffChips(o, ref)}</div></td></tr>`);
        tr.onclick = () => { state.selOffer = state.selOffer === o.id ? null : o.id; render(); };
        tb.appendChild(tr);
      });
      const sel = r.offers.find((o) => o.id === state.selOffer);
      if (sel) box.appendChild(waterfall(sel, s));
      w.appendChild(box);
    });
    w.appendChild(h(`<div class="note">Click any offer to see how its like-for-like price is built. All assumptions are editable on the Assumptions tab.</div>`));
    return w;
  }

  function waterfall(o, s) {
    const c = o.l4l;
    const steps = [["Price the agent pays", c.price, "#13202a"], ["Meals included", c.meals, "#0f7a63"], ["Cancellation terms", c.cancellation, c.cancellation > 0 ? "#b3261e" : "#0f7a63"], ["Pay-later cash benefit", c.pay_later, "#0f7a63"], ["Supplier failure risk", c.supplier_risk, "#b3261e"]];
    const max = Math.max(c.price, c.l4l) * 1.05;
    let run = 0;
    const rows = steps.map(([lbl, v, col], i) => {
      const a = i === 0 ? 0 : run, b = i === 0 ? v : run + v;
      run = i === 0 ? v : run + v;
      const lo = Math.min(a, b), hi = Math.max(a, b);
      return `<div class="wf-row"><span>${lbl}</span><div class="wf-bar"><span style="left:${(100 * lo / max).toFixed(2)}%;width:${Math.max(0.4, 100 * (hi - lo) / max).toFixed(2)}%;background:${col}"></span></div><span class="mono r">${i === 0 ? inr(v) : (v >= 0 ? "+" : "−") + inr(Math.abs(v)).slice(1)}</span></div>`;
    }).join("");
    const rel = relOf(o.sup, state.city);
    return h(`<div class="waterfall"><div>${rows}<div class="wf-row" style="border-top:1px solid var(--line);margin-top:4px;padding-top:6px;font-weight:600"><span>Like-for-like price</span><div class="wf-bar"><span style="left:0;width:${(100 * c.l4l / max).toFixed(2)}%;background:#d9481c"></span></div><span class="mono r">${inr(c.l4l)}</span></div></div>
      <div class="wf-note"><b>Reference product:</b> room only, free cancellation to 7 days, pay now, perfectly reliable supplier.<br><br>
      ${supName(o.sup)} in ${D.cities[state.city]}: ${rel ? `${pct(rel.price_jump.mean)} price jumps at booking, ${pct(rel.confirm_fail.mean)} confirmation failures, ${pct(rel.supplier_cancel.mean)} supplier cancellations over ${rel.bookings.toLocaleString("en-IN")} bookings (grade ${rel.grade}).` : "no booking history."}<br><br>
      Like-for-like is a comparison price, not what is charged. The agent still pays ${inr(c.price)}.</div></div>`);
  }

  function sameView(s) {
    const lat0 = s.lat, lon0 = s.lon;
    const pts = s.records.map((r) => {
      let la = r.lat, lo = r.lon;
      if (r.fixed) [la, lo] = [lo, la];
      const dy = (la - lat0) * 111320, dx = (lo - lon0) * 111320 * Math.cos(lat0 * Math.PI / 180);
      return { ...r, dx, dy };
    });
    const R = Math.max(120, ...pts.map((p) => Math.hypot(p.dx, p.dy))) * 1.25;
    const map = `<svg viewBox="-110 -110 220 220" width="220" height="220" style="background:#f3efe6;border-radius:8px;border:1px solid var(--line)">
      <circle r="${(100 * 50 / R).toFixed(1)}" fill="none" stroke="#d6cfc0" stroke-dasharray="3 3"/><circle r="${(100 * 100 / R).toFixed(1)}" fill="none" stroke="#e1dbcf"/>
      ${pts.map((p) => `<circle cx="${(100 * p.dx / R).toFixed(1)}" cy="${(-100 * p.dy / R).toFixed(1)}" r="5" fill="${SUPCOL[p.sup]}" opacity=".85"><title>${p.sup}</title></circle>`).join("")}
      <text x="-104" y="104" font-size="9" fill="#6b7680">dashed ring = 50 m · solid = 100 m</text></svg>`;
    return h(`<div style="display:grid;grid-template-columns:1fr 240px;gap:16px"><table class="t"><thead><tr><th>Supplier</th><th>Name as sent</th><th>Stars</th><th>Address as sent</th><th>Phone as sent</th></tr></thead>
      <tbody>${s.records.map((r) => `<tr><td><span class="chip sup" style="border-color:${SUPCOL[r.sup]}55;color:${SUPCOL[r.sup]}">${r.sup}</span></td><td class="raw">${esc(r.name)}</td><td>${r.stars ?? "—"}</td><td class="raw">${esc(r.addr)}</td><td class="raw">${esc(r.phone ?? "—")}${r.fixed ? ' <span class="chip warn">lat/lon swapped, repaired</span>' : ""}</td></tr>`).join("")}</tbody></table>
      <div>${map}<div class="note" style="margin-top:6px">Each dot is where a supplier says the hotel is. Merged automatically because the calibrated match probability for every pair cleared 0.90.</div></div></div>`);
  }

  function rankView(s) {
    const lbl = { value: "Value of best like-for-like deal vs same-star hotels", quality: "Stars, guest score, content richness", margin: "Expected TBO gross profit (margin × success chance)", trust: "Reliability of the winning supplier" };
    const w = P.rank;
    return h(`<div class="two"><div>${Object.entries(s.score_parts).map(([k, v]) => `<div class="wf-row" style="grid-template-columns:300px 1fr 70px"><span>${lbl[k]}</span><div class="wf-bar"><span style="left:0;width:${(100 * v / 0.45).toFixed(1)}%;background:${{ value: "#2c6e9b", quality: "#8a6db0", margin: "#c7892b", trust: "#2f8f6f" }[k]}"></span></div><span class="mono r">${v.toFixed(3)}</span></div>`).join("")}</div>
      <div class="wf-note">Weights: value ${w.w_value}, quality ${w.w_quality}, margin ${w.w_margin}, trust ${w.w_trust}. A diversity pass then stops the first screen filling with near-identical hotels (same area, same price band). ${s.platinum ? `This is a Platinum hotel: lifted ${s.platinum_lift} place(s), capped at ${w.platinum_max_lift}.` : "No commercial lift applied."}</div></div>`);
  }

  // ------------------------------------------------------------ SIGHTSEEING
  function renderSS(app) {
    const A = D.sightseeing.attractions;
    const ids = Object.keys(A).filter((k) => A[k].city === state.city);
    if (!state.ssAttr || !ids.includes(state.ssAttr)) state.ssAttr = ids[0];
    const a = A[state.ssAttr];
    const L = D.sightseeing.labels;
    app.innerHTML = "";
    app.appendChild(h(`<div class="headrow"><div><h1>Sightseeing in ${esc(D.cities[state.city])}</h1><p>Same attraction ≠ same product. Offers with identical inclusions are merged; real differences stay visible.</p></div></div>`));
    const g = h(`<div class="grid-hotels"></div>`);
    g.appendChild(h(`<aside class="panel rail"><div class="sec"><h4>Attractions</h4>${ids.map((k) => `<button class="tab" style="display:block;width:100%;text-align:left;color:var(--ink);${k === state.ssAttr ? "background:#efe9de" : ""}" data-a="${k}">${esc(A[k].name)}<div class="note">${A[k].n_products} supplier products → ${A[k].variants.length} distinct</div></button>`).join("")}</div></aside>`));
    const m = h(`<section class="panel" style="padding:14px"></section>`);
    m.appendChild(h(`<div style="margin-bottom:10px"><b style="font-family:var(--serif);font-size:20px">${esc(a.name)}</b> <span class="note">· ${a.n_products} products from ${new Set(a.variants.flatMap((v) => v.offers.map((o) => o.supplier))).size} suppliers collapse into ${a.variants.length} genuinely different experiences</span></div>`));
    const yes = (v, lab) => (v && v !== "none" && v !== "general" ? `<td class="yes">${esc(lab)}</td>` : `<td class="no">—</td>`);
    const t = h(`<table class="t matrix"><thead><tr><th>Access</th><th>Transfer</th><th>Meal</th><th>Guide</th><th>Group</th><th>Cancel</th><th>Supplier titles (merged)</th><th class="r">Best price</th><th class="r">Price minus inclusions</th></tr></thead><tbody></tbody></table>`);
    a.variants.forEach((v, i) => {
      const at = v.atoms;
      t.querySelector("tbody").appendChild(h(`<tr><td>${at.access === "general" ? "General" : `<b>${esc(L[at.access])}</b>`}</td>${yes(at.transfer, L[at.transfer])}${yes(at.meal, L[at.meal])}${yes(at.guide, L[at.guide])}<td>${at.private ? "<b>Private</b>" : "Shared"}</td><td>${at.cancel_24h ? '<span class="chip good">24h free</span>' : '<span class="chip bad">Non-ref</span>'}</td>
        <td>${v.offers.map((o) => `<div class="raw" style="margin:2px 0"><span class="chip sup">${o.supplier}</span> ${esc(o.title)} · <b>${inr(o.price_inr)}</b></div>`).join("")}</td>
        <td class="r mono">${inr(v.best_price)}</td><td class="r mono"><b>${inr(v.core_price)}</b>${i === 0 ? '<div class="best-tag">lowest core</div>' : ""}</td></tr>`));
    });
    m.appendChild(t);
    m.appendChild(h(`<div class="note" style="margin-top:10px">“Price minus inclusions” subtracts what transfers, meals and guides are worth (editable assumption), so a cheap ticket and a ticket-plus-transfer can be compared honestly. Product atoms are read from free-text titles by deterministic rules; durations come from structured fields when a supplier sends them.</div>`));
    g.appendChild(m);
    app.appendChild(g);
    g.querySelectorAll("[data-a]").forEach((b) => (b.onclick = () => { state.ssAttr = b.dataset.a; render(); }));
  }

  // ------------------------------------------------------------ REVIEW DESK
  function renderReview(app) {
    const Q = D.review;
    app.innerHTML = "";
    const done = Object.values(state.rvDone);
    const agree = done.filter((d) => d.correct).length;
    const total = Object.values(D.evidence).filter((e) => e && e.candidate_pairs).reduce((a, e) => a + e.candidate_pairs, 0);
    app.appendChild(h(`<div class="headrow"><div><h1>Mapping review desk</h1><p>Only pairs the model is unsure about reach a person: <b>${Q.length}</b> of ${total.toLocaleString("en-IN")} candidate pairs (${pct(Q.length / total, 2)}). The queue is ordered by booking value at risk, not by arrival time.</p></div>
      <div class="kpi" style="padding:10px 14px"><div class="mono" style="font-size:18px;font-weight:600">${done.length} reviewed · ${done.length ? pct(agree / done.length, 0) : "—"} correct</div><div class="l">decisions feed the next model retrain</div></div></div>`));
    if (!Q.length) { app.appendChild(h(`<div class="panel empty">Nothing to review.</div>`)); return; }
    state.rv = Math.min(state.rv, Q.length - 1);
    const g = h(`<div class="rv-grid"></div>`);
    const q = h(`<aside class="panel queue" style="max-height:72vh;overflow:auto"></aside>`);
    Q.forEach((r, i) => {
      const d = state.rvDone[r.pair];
      q.appendChild(h(`<button class="qi ${i === state.rv ? "on" : ""}" data-i="${i}"><div class="nm">${esc(r.a.name)}<br><span style="font-weight:400;color:var(--ink-3)">vs</span> ${esc(r.b.name)}</div>
        <div class="sb"><span>${r.city} · ${inr(r.gtv_at_risk)} at risk</span><span>${d ? (d.correct ? "✓ decided" : "✗ decided") : "p=" + r.p.toFixed(2)}</span></div><div class="pbar"><i style="width:${(100 * r.p).toFixed(0)}%"></i></div></button>`));
    });
    g.appendChild(q);
    const r = Q[state.rv];
    const rows = [["Supplier", r.a.supplier + " · " + supName(r.a.supplier), r.b.supplier + " · " + supName(r.b.supplier)], ["Name", r.a.name, r.b.name], ["Stars", r.a.stars ?? "—", r.b.stars ?? "—"], ["Address", r.a.address, r.b.address], ["Phone", r.a.phone ?? "—", r.b.phone ?? "—"]];
    const m = h(`<section class="panel" style="padding:16px"></section>`);
    m.appendChild(h(`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><div><b style="font-family:var(--serif);font-size:20px">Same hotel?</b> <span class="note">model probability ${r.p.toFixed(2)} · ${r.distance_m.toLocaleString("en-IN")} m apart · ${inr(r.gtv_at_risk)} of current offers depend on this answer</span></div></div>`));
    m.appendChild(h(`<div class="cmp">${rows.map(([k, a, b]) => `<div class="k">${k}</div><div class="${String(a).toLowerCase() !== String(b).toLowerCase() && k !== "Supplier" ? "diff" : ""} raw">${esc(a)}</div><div class="${String(a).toLowerCase() !== String(b).toLowerCase() && k !== "Supplier" ? "diff" : ""} raw">${esc(b)}</div>`).join("")}</div>`));
    const mx = Math.max(...r.why.map((w) => Math.abs(w.push)), 1);
    m.appendChild(h(`<div class="why" style="margin-top:14px"><div class="note" style="margin-bottom:6px"><b>Why the model is unsure</b>: signals pushing towards <span style="color:var(--good)">same</span> or <span style="color:var(--bad)">different</span></div>
      ${r.why.map((w) => `<div class="w"><span>${esc(w.label)}${typeof w.value === "number" ? ` <span class="mono note">(${w.value})</span>` : String(w.value).endsWith(" m") ? ` <span class="mono note">(${w.value})</span>` : ""}</span><div class="axis"><i style="${w.push >= 0 ? `left:50%;width:${(50 * w.push / mx).toFixed(1)}%;background:var(--good)` : `right:50%;width:${(50 * -w.push / mx).toFixed(1)}%;background:var(--bad)`}"></i></div><span class="mono r">${w.push > 0 ? "+" : ""}${w.push}</span></div>`).join("")}</div>`));
    const d = state.rvDone[r.pair];
    const act = h(`<div style="display:flex;gap:10px;margin-top:16px"><button class="btn good" data-d="1">Same hotel: merge</button><button class="btn bad" data-d="0">Different hotels: keep apart</button><button class="btn ghost" data-d="s">Skip</button></div>`);
    m.appendChild(act);
    if (d) m.appendChild(h(`<div class="verdict ${d.correct ? "banner good" : "banner warn"}">You said <b>${d.same ? "same hotel" : "different hotels"}</b>. Ground truth in the synthetic world: <b>${r.truth_same ? "same hotel" : "different hotels"}</b>. ${d.correct ? "Correct." : "This pair is genuinely hard; that is why it was routed to a person."}</div>`));
    m.appendChild(h(`<div class="note" style="margin-top:14px">Auto-merge at p ≥ ${D.config.match.auto_merge}; keep apart below ${D.config.match.review_floor}. Both thresholds are configuration. Merges are reversible and every decision is logged with who made it and which model version proposed it.</div>`));
    g.appendChild(m);
    app.appendChild(g);
    q.querySelectorAll(".qi").forEach((b) => (b.onclick = () => { state.rv = +b.dataset.i; render(); }));
    act.querySelectorAll("button").forEach((b) => (b.onclick = () => {
      if (b.dataset.d !== "s") { const same = b.dataset.d === "1"; state.rvDone[r.pair] = { same, correct: same === r.truth_same }; render(); return; }
      state.rv = Math.min(Q.length - 1, state.rv + 1); render();
    }));
  }

  // ------------------------------------------------------------ SUPPLIER LEDGER
  function renderLedger(app) {
    app.innerHTML = "";
    app.appendChild(h(`<div class="headrow"><div><h1>Supplier reliability ledger</h1><p>From TBO's own booking outcomes, per supplier and destination. Small samples are pulled towards the city average, so a supplier never gets a perfect score from fourteen lucky bookings.</p></div></div>`));
    const rows = Object.values(D.reliability).sort((a, b) => a.city.localeCompare(b.city) || a.p_any_failure - b.p_any_failure);
    const ci = (e) => { const M = 0.12; return `<div class="ci"><i style="left:${(100 * e.lo90 / M).toFixed(1)}%;width:${(100 * (e.hi90 - e.lo90) / M).toFixed(1)}%"></i><b style="left:${(100 * e.mean / M).toFixed(1)}%"></b></div>`; };
    const t = h(`<div class="panel" style="overflow:auto"><table class="t"><thead><tr><th>City</th><th>Supplier</th><th class="r">Bookings</th><th>Price jump at booking</th><th>Confirmation fail</th><th>Supplier cancels</th><th class="r">Any failure</th><th>Grade</th></tr></thead><tbody>
      ${rows.map((e) => `<tr style="${e.city === state.city ? "" : "opacity:.55"}"><td>${e.city}</td><td><span class="chip sup" style="border-color:${SUPCOL[e.supplier]}55;color:${SUPCOL[e.supplier]}">${e.supplier}</span> ${esc(supName(e.supplier))}${e.thin_evidence ? ' <span class="chip warn">thin evidence</span>' : ""}</td><td class="r mono">${e.bookings.toLocaleString("en-IN")}</td>
      ${["price_jump", "confirm_fail", "supplier_cancel"].map((k) => `<td><div style="display:flex;gap:8px;align-items:center">${ci(e[k])}<span class="mono" style="font-size:12px">${pct(e[k].mean)}</span><span class="note" style="font-size:11px">raw ${pct(e[k].raw)}</span></div></td>`).join("")}
      <td class="r mono">${pct(e.p_any_failure)}</td><td><span class="grade ${e.grade}">${e.grade}</span></td></tr>`).join("")}</tbody></table></div>`);
    app.appendChild(t);
    app.appendChild(h(`<div class="note" style="margin:8px 2px 0">Bar = 90% credible interval; tick = estimate. Scale 0–12%. Rows for other cities are dimmed.</div>`));
    app.appendChild(h(`<div class="h2">Supplier data quality (found while mapping)</div>`));
    const dq = D.data_quality;
    app.appendChild(h(`<div class="panel"><table class="t"><thead><tr><th>Supplier</th><th class="r">Room records</th><th class="r">Rate-plan words inside room names</th><th class="r">Ambiguous bed (“Double”)</th><th>What to raise with the supplier</th></tr></thead><tbody>
      ${Object.entries(dq).map(([k, v]) => `<tr><td><span class="chip sup" style="border-color:${SUPCOL[k]}55;color:${SUPCOL[k]}">${k}</span> ${esc(supName(k))}</td><td class="r mono">${v.rooms.toLocaleString("en-IN")}</td><td class="r mono">${pct(v.rate_words_in_room_name / v.rooms)}</td><td class="r mono">${pct(v.ambiguous_bed / v.rooms)}</td>
      <td class="note">${v.rate_words_in_room_name / v.rooms > 0.1 ? "Send board and refundability as fields, not in the room name. " : ""}${v.ambiguous_bed / v.rooms > 0.4 ? "Send bed type (King/Queen) explicitly." : ""}${v.rate_words_in_room_name / v.rooms <= 0.1 && v.ambiguous_bed / v.rooms <= 0.4 ? "Clean." : ""}</td></tr>`).join("")}</tbody></table></div>`));
  }

  // ------------------------------------------------------------ EVIDENCE
  function renderEvidence(app) {
    const E = D.evidence;
    const C = ["DXB", "BKK", "PAR"];
    const avg = (f) => C.reduce((a, c) => a + f(E[c]), 0) / C.length;
    app.innerHTML = "";
    app.appendChild(h(`<div class="headrow"><div><h1>Evidence</h1><p>Every hotel-matching number is held-out: the model scoring a city was trained only on the other two cities. Ground truth comes from the synthetic world and is never shown to the engine.</p></div></div>`));
    app.appendChild(h(`<div class="kpis">
      <div class="kpi"><div class="v">${avg((e) => e.auto.f1).toFixed(3)}</div><div class="l">Hotel matching F1, held-out, no human</div><div class="d" style="color:var(--good)">vs ${avg((e) => e.baseline.f1).toFixed(3)} for name + distance rule</div></div>
      <div class="kpi"><div class="v">${pct(avg((e) => e.auto.precision), 2)}</div><div class="l">Precision of automatic merges</div><div class="d">wrong merges are the expensive error</div></div>
      <div class="kpi"><div class="v">${E.rooms.f1.toFixed(3)}</div><div class="l">Room mapping F1 (${E.rooms.true_pairs.toLocaleString("en-IN")} true pairs)</div><div class="d">vs 0.21 for fuzzy room-name match</div></div>
      <div class="kpi"><div class="v">${E.sightseeing.variant_pairs.f1.toFixed(3)}</div><div class="l">Sightseeing product matching F1</div><div class="d">attraction resolved correctly for ${pct(E.sightseeing.attraction_accuracy, 0)}</div></div></div>`));
    app.appendChild(h(`<div class="panel" style="overflow:auto"><table class="t"><thead><tr><th>City (held out)</th><th class="r">Supplier records</th><th class="r">Hotels (truth)</th><th class="r">Listings produced</th><th class="r">Blocking recall</th><th class="r">Auto F1</th><th class="r">Auto precision</th><th class="r">Auto recall</th><th class="r">Exact hotels</th><th class="r">Sent to review</th><th class="r">F1 after review</th><th class="r">Rule baseline F1</th></tr></thead><tbody>
      ${C.map((c) => { const e = E[c]; return `<tr><td>${D.cities[c]}</td><td class="r mono">${e.listings.raw_records}</td><td class="r mono">${e.listings.true_hotels}</td><td class="r mono">${e.listings.predicted_listings}</td><td class="r mono">${pct(e.blocking_recall, 1)}</td><td class="r mono"><b>${e.auto.f1.toFixed(4)}</b></td><td class="r mono">${e.auto.precision.toFixed(4)}</td><td class="r mono">${e.auto.recall.toFixed(4)}</td><td class="r mono">${pct(e.auto_exact, 1)}</td><td class="r mono">${e.review_pairs}</td><td class="r mono">${e.with_review.f1.toFixed(4)}</td><td class="r mono">${e.baseline.f1.toFixed(4)}</td></tr>`; }).join("")}</tbody></table></div>`));
    app.appendChild(h(`<div class="two" style="margin-top:16px"><div class="panel" style="padding:16px"><b>What the baseline gets wrong</b><div class="note" style="margin-top:6px">${C.map((c) => `${D.cities[c]}: ${E[c].baseline.false_merges} wrong merges, ${E[c].baseline.missed_merges} missed`).join(" · ")}.<br>TrueShelf: ${C.map((c) => `${D.cities[c]}: ${E[c].auto.false_merges} wrong, ${E[c].auto.missed_merges} missed`).join(" · ")}.<br><br>The rule fails on transliteration (Qasr/Kasr, Baan/Ban), abbreviations (HTL, STES), city suffixes, and sister properties 80–250 m apart (“Saffron Creek Hotel” vs “Saffron Creek Suites”).</div></div>
      <div class="panel" style="padding:16px"><b>Honest limits</b><div class="note" style="margin-top:6px">• The data is synthetic. Its failure modes are realistic, but real feeds will be messier; Round 2 targets a pilot on a real TBO supplier sample.<br>• The room grammar was written for these suppliers' styles. Against an unseen style (French, marketing names, “Room Type C”), recall fell to 49% but wrong merges stayed at zero: unreadable rooms stay separate and are flagged for mapping. That stress test found, and we fixed, a bug that grouped partly-read names.<br>• Like-for-like rupee values are stated assumptions (see Assumptions), meant to be replaced by values measured from TBO's booking data.<br>• Pipeline runtime for all three cities: ${E.runtime_s.matching_all_cities}s matching, ${E.runtime_s.total}s end to end on one CPU.</div></div></div>`));
  }

  // ------------------------------------------------------------ ASSUMPTIONS
  function renderAssume(app) {
    app.innerHTML = "";
    const before = (cache[state.city] || recompute(state.city)).slice(0, 10).map((s) => s.id);
    app.appendChild(h(`<div class="headrow"><div><h1>Assumptions</h1><p>Every rupee in a like-for-like price and every ranking weight is configuration, not code. Move a slider: prices and ranks update everywhere, live.</p></div><button class="btn ghost" id="reset">Reset to defaults</button></div>`));
    const S = [
      ["l4l", "p_cancel", "Chance the traveller cancels", 0, 0.4, 0.01, (v) => pct(v, 0)],
      ["l4l", "annual_cost_of_capital", "Agent cost of capital (annual)", 0, 0.3, 0.01, (v) => pct(v, 0)],
      ["l4l", "failure_handling_cost", "Ops cost of a failed booking", 0, 8000, 100, inr],
      ["l4l", "reaccommodation_premium", "Re-accommodation premium (share of price)", 0, 0.5, 0.01, (v) => pct(v, 0)],
      ["l4l", "avg_price_jump", "Average price jump at booking", 0, 0.25, 0.01, (v) => pct(v, 0)],
      ["bf", "scale", "Breakfast value (× default)", 0, 2.5, 0.05, (v) => v.toFixed(2) + "×"],
      ["rank", "w_value", "Weight: value", 0, 1, 0.01, (v) => v.toFixed(2)],
      ["rank", "w_quality", "Weight: quality", 0, 1, 0.01, (v) => v.toFixed(2)],
      ["rank", "w_margin", "Weight: TBO margin", 0, 1, 0.01, (v) => v.toFixed(2)],
      ["rank", "w_trust", "Weight: supplier trust", 0, 1, 0.01, (v) => v.toFixed(2)],
      ["rank", "platinum_max_lift", "Max Platinum lift (places)", 0, 10, 1, (v) => v],
    ];
    const bfScale = P._bf || 1;
    const panel = h(`<div class="two"><div class="panel" style="padding:16px"><b>Like-for-like price</b><div id="sl1"></div></div><div class="panel" style="padding:16px"><b>ShelfRank</b><div id="sl2"></div></div></div>`);
    S.forEach(([grp, key, label, mn, mx, st, fmt]) => {
      const cur = grp === "bf" ? bfScale : P[grp][key];
      const row = h(`<div class="slider"><div><label>${label}</label><input type="range" min="${mn}" max="${mx}" step="${st}" value="${cur}"></div><div class="val">${fmt(cur)}</div></div>`);
      const inp = row.querySelector("input");
      inp.oninput = () => {
        const v = +inp.value;
        row.querySelector(".val").textContent = fmt(v);
        if (grp === "bf") { P._bf = v; ["breakfast_pp_by_star", "dinner_pp_by_star"].forEach((k) => Object.keys(DEFAULTS.l4l[k]).forEach((s) => (P.l4l[k][s] = DEFAULTS.l4l[k][s] * v))); }
        else P[grp][key] = v;
        showDelta();
      };
      (grp === "rank" ? panel.querySelector("#sl2") : panel.querySelector("#sl1")).appendChild(row);
    });
    app.appendChild(panel);
    const delta = h(`<div class="panel" style="padding:16px;margin-top:16px"></div>`);
    app.appendChild(delta);
    function showDelta() {
      const now = recompute(state.city).slice(0, 10);
      const moved = now.filter((s, i) => before[i] !== s.id).length;
      delta.innerHTML = `<b>Top 10 in ${esc(D.cities[state.city])} under these assumptions</b> <span class="note">· ${moved} of 10 positions changed vs when you opened this page</span>
        <table class="t" style="margin-top:8px"><thead><tr><th>#</th><th>Hotel</th><th>Best offer</th><th class="r">Like-for-like / night</th><th class="r">Was</th></tr></thead><tbody>${now.map((s, i) => `<tr><td class="mono">${i + 1}</td><td>${esc(s.name)} <span class="stars">${starStr(s.stars)}</span></td><td>${s.best.sup} · ${esc(s.best.room)}</td><td class="r mono">${inr(s.best.l4l / NIGHTS)}</td><td class="r mono">${before.indexOf(s.id) >= 0 ? "#" + (before.indexOf(s.id) + 1) : "new"}</td></tr>`).join("")}</tbody></table>`;
    }
    showDelta();
    $("#reset").onclick = () => { Object.assign(P.l4l, clone(DEFAULTS.l4l)); Object.assign(P.rank, clone(DEFAULTS.rank)); P._bf = 1; render(); };
  }

  // ------------------------------------------------------------ root
  function render() {
    renderTabs();
    searchChip();
    const app = $("#app");
    ({ hotels: renderHotels, ss: renderSS, review: renderReview, ledger: renderLedger, evidence: renderEvidence, assume: renderAssume }[state.view])(app);
  }
  function init() {
    const sel = $("#citySel");
    sel.innerHTML = Object.entries(D.cities).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
    sel.value = state.city;
    sel.onchange = () => { state.city = sel.value; state.open = null; state.f.areas.clear(); render(); };
    $("#cfgv").textContent = D.config.version;
    const q = new URLSearchParams(location.search);
    if (q.get("view")) state.view = q.get("view");
    if (q.get("city")) { state.city = q.get("city"); sel.value = state.city; }
    if (q.get("mode")) state.mode = q.get("mode");
    if (q.get("open") === "1") { const s = recompute(state.city)[0]; state.open = s.id; }
    if (q.get("dtab")) state.dtab = q.get("dtab");
    if (q.get("sel") && state.open) { const s = recompute(state.city)[0]; const r = s.rooms[0]; const o = r.offers[Math.min(r.offers.length - 1, +q.get("sel"))]; state.selOffer = o.id; }
    if (q.get("rv")) state.rv = +q.get("rv");
    render();
  }
  if (typeof document !== "undefined" && document.getElementById("app")) init();
})();

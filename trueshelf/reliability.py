"""Supplier Reliability Ledger.

From TBO's own booking outcomes, estimate per supplier x destination how often
a booking goes wrong: price jumps at booking, confirmation failures, and
supplier-side cancellations after confirmation.

Small samples are shrunk towards the destination average (empirical Bayes,
Beta-Binomial), so one lucky or unlucky week never decides ranking, and every
estimate carries a 90% credible interval.
"""
from __future__ import annotations

from collections import defaultdict

from scipy.stats import beta

OUTCOMES = ("price_jump", "confirm_fail", "supplier_cancel")
PRIOR_STRENGTH = 150  # pseudo-bookings: how much evidence it takes to move away from the city average


def ledger(rows: list[dict]) -> dict:
    counts = defaultdict(lambda: defaultdict(int))
    city_tot = defaultdict(lambda: defaultdict(int))
    for r in rows:
        k = (r["supplier"], r["city"])
        counts[k]["n"] += 1
        counts[k][r["outcome"]] += 1
        city_tot[r["city"]]["n"] += 1
        city_tot[r["city"]][r["outcome"]] += 1
    out = {}
    for (sup, city), c in counts.items():
        n = c["n"]
        entry = {"supplier": sup, "city": city, "bookings": n}
        for o in OUTCOMES:
            prior_mean = max(1e-4, city_tot[city][o] / city_tot[city]["n"])
            a0, b0 = prior_mean * PRIOR_STRENGTH, (1 - prior_mean) * PRIOR_STRENGTH
            a, b = a0 + c[o], b0 + n - c[o]
            entry[o] = {"raw": c[o] / n, "mean": a / (a + b), "lo90": float(beta.ppf(0.05, a, b)),
                        "hi90": float(beta.ppf(0.95, a, b))}
        p_ok = 1.0
        for o in OUTCOMES:
            p_ok *= 1 - entry[o]["mean"]
        entry["p_any_failure"] = 1 - p_ok
        entry["grade"] = "A" if entry["p_any_failure"] < 0.025 else "B" if entry["p_any_failure"] < 0.06 else "C"
        entry["thin_evidence"] = n < 100
        out[f"{sup}|{city}"] = entry
    return out

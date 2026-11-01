"""Layer 2b of TrueShelf: Like-for-Like Price.

Two offers for the same room are rarely the same *product*: one includes
breakfast, one is non-refundable, one lets the agent pay later, one comes from
a supplier that fails 1 booking in 12. The cheapest headline price is
therefore often not the cheapest deal.

L4L converts every difference into rupees against a common reference product:
  room only + free cancellation (to 7 days) + pay now + perfectly reliable supplier

    L4L = selling price
          - value of included meals            (they are worth money to the traveller)
          + expected loss from tighter cancellation
          - cash-flow benefit of paying later
          + expected cost of supplier failure

Every term is returned separately so the UI can show *why*, and the same
formula is implemented in the browser (web/app.js) and checked against this
file by a test.
"""
from __future__ import annotations

from .config import L4LParams

REF_CANCEL_DAYS = 7


def _late_share(days: int | None, params: L4LParams) -> float:
    """Share of cancellations happening inside `days` of check-in (step interpolation)."""
    curve = {int(k): v for k, v in params.late_cancel_share.items()}
    if days is None:
        return 1.0
    ks = sorted(curve)
    best = 0.0
    for k in ks:
        if k <= days:
            best = curve[k]
    return best


def l4l(offer: dict, stars: int, rel: dict | None, params: L4LParams, adults: int = 2, nights: int = 2,
        lead_days: int = 21) -> dict:
    price = float(offer["sell_inr"])
    s = int(round(stars or 3))
    s = min(5, max(2, s))
    meals = 0.0
    if offer["board"] in ("BB", "HB"):
        meals += params.breakfast_pp_by_star[s] * adults * nights
    if offer["board"] == "HB":
        meals += params.dinner_pp_by_star[s] * adults * nights
    # expected loss from cancellation terms, relative to the reference product
    cd = offer.get("cancel_free_until_days")
    if cd is None:
        exposure = params.nr_loss_fraction
        share = 1.0
    else:
        exposure = 1.0
        share = _late_share(cd, params)
    ref_share = _late_share(REF_CANCEL_DAYS, params)
    cancel_cost = params.p_cancel * price * (exposure * share - ref_share)
    # paying later frees cash until the free-cancel deadline
    paylater = 0.0
    if offer.get("pay_later") and cd is not None:
        days_deferred = max(0, lead_days - cd)
        paylater = price * params.annual_cost_of_capital * days_deferred / 365
    # supplier failure expected cost
    fail = 0.0
    if rel:
        pj = rel["price_jump"]["mean"]
        cf = rel["confirm_fail"]["mean"] + rel["supplier_cancel"]["mean"]
        fail = pj * params.avg_price_jump * price + cf * (params.reaccommodation_premium * price + params.failure_handling_cost)
    total = price - meals + cancel_cost - paylater + fail
    return {"price": round(price), "meals": round(-meals), "cancellation": round(cancel_cost), "pay_later": round(-paylater),
            "supplier_risk": round(fail), "l4l": round(total)}

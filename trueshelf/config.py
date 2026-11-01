"""Central, versioned configuration for TrueShelf.

Every number that changes what an agent sees (like-for-like price, ranking,
review thresholds) lives here, not inside model code. Ops/commercial teams can
change these values without touching the engine, and each export records the
config version it was produced with.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

CONFIG_VERSION = "2026.11-r1"

CITIES = {
    "DXB": {"name": "Dubai", "country": "AE", "lat": 25.2048, "lon": 55.2708, "ccy_per_inr": 1 / 22.7},
    "BKK": {"name": "Bangkok", "country": "TH", "lat": 13.7563, "lon": 100.5018, "ccy_per_inr": 1 / 2.4},
    "PAR": {"name": "Paris", "country": "FR", "lat": 48.8566, "lon": 2.3522, "ccy_per_inr": 1 / 95.0},
}


@dataclass
class MatchThresholds:
    # Calibrated probability that two supplier records are the same property.
    auto_merge: float = 0.90   # at or above: merged without a human
    review_floor: float = 0.30  # between floor and auto_merge: Mapping Review Desk
    # below review_floor: kept apart automatically


@dataclass
class L4LParams:
    """Assumptions that turn product differences into rupees.

    All values are deliberately simple, explicit and editable. They are
    defaults for the demo, meant to be replaced by TBO's own measured values
    (e.g. breakfast value from ancillary sales, cancel curve from booking logs).
    """
    # What breakfast is worth to the traveller per person per night, by star rating (INR).
    # Deliberately conservative (below hotel menu prices): not every guest eats it.
    breakfast_pp_by_star: dict = field(default_factory=lambda: {2: 300, 3: 450, 4: 700, 5: 1100})
    # Dinner (half board adds this on top of breakfast), per person per night.
    dinner_pp_by_star: dict = field(default_factory=lambda: {2: 550, 3: 800, 4: 1200, 5: 1900})
    # Probability the end traveller cancels before travel (B2B leisure, demo default).
    p_cancel: float = 0.16
    # Share of cancellations that happen inside N days of check-in (cumulative curve).
    # Used to price "free cancellation until D days before".
    late_cancel_share: dict = field(default_factory=lambda: {0: 0.0, 1: 0.22, 3: 0.38, 7: 0.55, 14: 0.74, 30: 0.92})
    # Fraction of the booking value lost if a non-refundable booking is cancelled.
    nr_loss_fraction: float = 1.0
    # Agent's cost of capital for paying earlier than necessary (annual).
    annual_cost_of_capital: float = 0.12
    # Ops cost of a failed booking (re-accommodation effort, support time), INR.
    failure_handling_cost: float = 2500.0
    # Average extra paid to re-accommodate after a confirmation failure (share of price).
    reaccommodation_premium: float = 0.18
    # Average size of a price jump at booking time (share of price).
    avg_price_jump: float = 0.07


@dataclass
class RankParams:
    w_value: float = 0.42        # how good the like-for-like price is vs. comparable hotels
    w_quality: float = 0.22      # stars + content richness
    w_margin: float = 0.18       # expected gross profit for TBO
    w_trust: float = 0.18        # supplier reliability of the winning offer
    diversity_lambda: float = 0.25  # MMR: penalty for near-identical neighbours
    platinum_max_lift: int = 3   # a Platinum hotel can move up at most this many slots
    platinum_bonus: float = 0.04


@dataclass
class Config:
    version: str = CONFIG_VERSION
    match: MatchThresholds = field(default_factory=MatchThresholds)
    l4l: L4LParams = field(default_factory=L4LParams)
    rank: RankParams = field(default_factory=RankParams)
    occupancy_adults: int = 2
    nights: int = 2
    lead_days: int = 21

    def to_dict(self) -> dict:
        d = asdict(self)
        # JSON keys must be strings
        for k in ("breakfast_pp_by_star", "dinner_pp_by_star", "late_cancel_share"):
            d["l4l"][k] = {str(kk): vv for kk, vv in d["l4l"][k].items()}
        return d


DEFAULT = Config()

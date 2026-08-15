"""Turn a watch's own price history into a buy-now-or-wait recommendation."""

from dataclasses import asdict, dataclass
from datetime import date
from statistics import fmean

MIN_POINTS = 3
RECENT_POINTS = 5
CHEAP_MARGIN = 0.05  # within 5% of the lowest seen counts as "at the low"
TREND_MARGIN = 0.02  # ignore trends smaller than 2%
LAST_CALL_DAYS = 21  # fares rarely improve inside three weeks of departure


@dataclass
class Recommendation:
    verdict: str  # "buy", "wait", or "watch"
    reason: str
    latest_price: float | None = None
    lowest_price: float | None = None
    average_price: float | None = None
    percent_vs_average: float | None = None
    trend: str = "flat"  # "rising", "falling", or "flat"
    days_to_departure: int | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _trend(prices: list[float]) -> str:
    """Direction of the most recent window compared with everything before it."""
    recent = prices[-RECENT_POINTS:]
    earlier = prices[:-RECENT_POINTS] or prices[:-1]
    if not earlier:
        return "flat"
    change = (fmean(recent) - fmean(earlier)) / fmean(earlier)
    if change > TREND_MARGIN:
        return "rising"
    if change < -TREND_MARGIN:
        return "falling"
    return "flat"


def recommend(
    prices: list[float],
    depart_date: date | None = None,
    today: date | None = None,
    target_price: float | None = None,
) -> Recommendation:
    """Advise on buying now, given the prices seen so far (oldest first)."""
    if not prices:
        return Recommendation(verdict="watch", reason="No price checks yet.")

    latest = prices[-1]
    lowest = min(prices)
    average = fmean(prices)
    days_left = (depart_date - (today or date.today())).days if depart_date else None
    trend = _trend(prices) if len(prices) >= MIN_POINTS else "flat"
    at_the_low = latest <= lowest * (1 + CHEAP_MARGIN)

    base = Recommendation(
        verdict="watch",
        reason="",
        latest_price=round(latest, 2),
        lowest_price=round(lowest, 2),
        average_price=round(average, 2),
        percent_vs_average=round((latest - average) / average * 100, 1),
        trend=trend,
        days_to_departure=days_left,
    )

    if len(prices) < MIN_POINTS:
        base.reason = (
            f"Only {len(prices)} check(s) so far — need {MIN_POINTS} to judge whether "
            f"{latest:.0f} is a good price."
        )
        return base

    if target_price is not None and latest <= target_price:
        base.verdict = "buy"
        base.reason = f"At {latest:.0f} it already meets your target of {target_price:.0f}."
        return base

    if days_left is not None and days_left <= LAST_CALL_DAYS:
        base.verdict = "buy" if at_the_low or trend == "rising" else "watch"
        base.reason = (
            f"Only {days_left} days to departure; fares usually climb from here"
            f"{' and this is the lowest seen' if at_the_low else ''}."
        )
        return base

    if at_the_low and trend != "falling":
        base.verdict = "buy"
        base.reason = (
            f"{latest:.0f} is the lowest seen ({base.percent_vs_average:+.1f}% vs average) "
            "and has stopped falling."
        )
        return base

    if trend == "falling":
        base.verdict = "wait"
        base.reason = f"Still falling — down to {latest:.0f} from an average of {average:.0f}."
        return base

    if trend == "rising":
        base.verdict = "buy" if at_the_low else "watch"
        base.reason = (
            f"Rising: {latest:.0f} is {base.percent_vs_average:+.1f}% vs average of {average:.0f}."
        )
        return base

    base.reason = (
        f"Flat around {average:.0f}; {latest:.0f} is {base.percent_vs_average:+.1f}% vs average "
        f"and {latest / lowest * 100 - 100:+.1f}% off the low of {lowest:.0f}."
    )
    return base

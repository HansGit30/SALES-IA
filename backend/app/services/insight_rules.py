from datetime import date, timedelta
from decimal import Decimal


def weekly_window(end: date):
    return {"start": end - timedelta(days=6), "end": end, "previous_start": end - timedelta(days=13),
            "previous_end": end - timedelta(days=7), "exclusive_end": end + timedelta(days=1)}


def revenue_drop(previous: Decimal, current: Decimal):
    if previous <= 0:
        return None
    change = (current - previous) / previous * 100
    if change > Decimal("-15"):
        return None
    return {"previous_7_days_revenue": str(previous), "current_7_days_revenue": str(current),
            "change_percent": str(change.quantize(Decimal("0.01"))), "threshold_percent": -15}


def insight_key(rule: str, day: date):
    return f"{rule}:{day.isoformat()}"

"""Billing model used by the replay.

Model of a per-second-billed warehouse at a fixed size (Snowflake-style rules):
  * the warehouse resumes when a query arrives while it is suspended;
  * it stays running while queries run and for AUTO_SUSPEND seconds after the last one ends;
  * each running period is billed per second with a minimum of MIN_BILL seconds.
Intervals are (start, end) in epoch seconds of query execution on that warehouse.
"""

MIN_BILL = 60.0


def periods(intervals, auto):
    """Merge query intervals into running periods [resume, suspend)."""
    if not intervals:
        return []
    iv = sorted(intervals)
    out = []
    s0, e0 = iv[0]
    for s, e in iv[1:]:
        if s <= e0 + auto:
            e0 = max(e0, e)
        else:
            out.append((s0, e0 + auto))
            s0, e0 = s, e
    out.append((s0, e0 + auto))
    return out


def billed_seconds(intervals, auto, min_bill=MIN_BILL):
    """Billed seconds = sum over running periods of max(min_bill, length)."""
    return sum(max(min_bill, e - s) for s, e in periods(intervals, auto))


def busy_seconds(intervals):
    """Seconds with at least one query executing (union of intervals)."""
    return sum(e - s for s, e in periods(intervals, 0.0))

from datetime import datetime, time, timedelta

from checks import CHICAGO, parse_cta_time

SCHOOL_START = time(8, 25)
SAFE_SLACK_MIN = 5

ROUTE_TIMES = {
    "49": {"ride": 11, "walk": 3},
    "X49": {"ride": 8, "walk": 8.5},
}

MARGINS = {
    "Reliable": 1,
    "Shaky": 3,
    "Unreliable": 6,
}


def _clock(value: datetime) -> str:
    return value.strftime("%H:%M")


def _verdict(slack: float) -> str:
    if slack >= SAFE_SLACK_MIN:
        return "Safe"
    if slack >= 0:
        return "Tight"
    return "Too late"


def _empty(arrival: dict, verdict: str) -> dict:
    return {
        **arrival,
        "plan_for": None,
        "school_arrival": None,
        "slack_minutes": None,
        "verdict": verdict,
        "recommended": False,
    }


def _evaluate(arrival: dict) -> dict:
    times = ROUTE_TIMES.get(arrival["route"])
    if times is None:
        return _empty(arrival, "Unknown route")

    if arrival["label"] == "Ghost bus":
        return _empty(arrival, "Don't count on it")

    predicted = parse_cta_time(arrival["arrival_time"])
    if predicted is None:
        return _empty(arrival, "Unknown time")

    plan_for = predicted + timedelta(minutes=MARGINS[arrival["label"]])
    school_arrival = plan_for + timedelta(minutes=times["ride"] + times["walk"])
    deadline = datetime.combine(predicted.date(), SCHOOL_START, tzinfo=CHICAGO)
    slack = round((deadline - school_arrival).total_seconds() / 60, 1)

    return {
        **arrival,
        "plan_for": _clock(plan_for),
        "school_arrival": _clock(school_arrival),
        "slack_minutes": slack,
        "verdict": _verdict(slack),
        "recommended": False,
        "_predicted": predicted,
    }


def _pick_recommended(evaluated: list[dict]) -> int | None:
    safe = [i for i, a in enumerate(evaluated) if a["verdict"] == "Safe"]
    if safe:
        return max(safe, key=lambda i: evaluated[i]["_predicted"])

    tight = [i for i, a in enumerate(evaluated) if a["verdict"] == "Tight"]
    if tight:
        return max(tight, key=lambda i: evaluated[i]["slack_minutes"])

    return None


def add_deadline(arrivals: list[dict]) -> list[dict]:
    evaluated = [_evaluate(a) for a in arrivals]

    best = _pick_recommended(evaluated)
    if best is not None:
        evaluated[best]["recommended"] = True

    for a in evaluated:
        a.pop("_predicted", None)

    return evaluated
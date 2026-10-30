from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


CHICAGO = ZoneInfo("America/Chicago")
HISTORY_KEEP = timedelta(minutes=10)
FORGET_AFTER = timedelta(minutes=3)
STALE_GPS_AFTER = timedelta(minutes=2)
MOVE_WINDOW = timedelta(minutes=5)
MOVE_MIN_SPAN = timedelta(minutes=4)
MIN_PROGRESS_FEET = 300
TRAVEL_FEET_PER_MIN = 1760 
LAYOVER_SLACK_MIN = 3
AT_STOP_FEET = 400
MAX_PLAUSIBLE_MPH = 30
DRIFT_WINDOW = timedelta(minutes=5)
DRIFT_MIN_SPAN = timedelta(minutes=3)
DRIFT_LIMIT = timedelta(minutes=3)
BUNCH_MINUTES = 2

PENALTIES = {
    "stale_gps": 40,
    "not_moving": 35,
    "impossible_eta": 30,
    "drift": 25,
    "bunched": 15,
    "delayed": 10,
}


def parse_cta_time(value):
    if not value:
        return None

    for fmt in ("%Y%m%d %H:%M:%S", "%Y%m%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=CHICAGO)
        except ValueError:
            continue

    return None

def parse_countdown(value):
    if value is None:
        return None

    if str(value).upper() == "DUE":
        return 0

    try:
        return int(value)
    except ValueError:
        return None

def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_vehicles(raw_vehicles):
    return {
        v["vid"]: {"gps_time": parse_cta_time(v.get("tmstmp"))}
        for v in raw_vehicles
        if v.get("vid")
    }


@dataclass
class Reading:
    taken_at: datetime
    feet: int | None
    arrival: datetime | None


history: dict[tuple[str, str], deque] = {}

def record(stop_id, vid, feet, arrival, now):
    readings = history.setdefault((stop_id, vid), deque())
    readings.append(Reading(now, feet, arrival))
    while readings and now - readings[0].taken_at > HISTORY_KEEP:
        readings.popleft()


def forget_missing(now):
    gone = [k for k, r in history.items() if now - r[-1].taken_at > FORGET_AFTER]
    for key in gone:
        del history[key]

def _recent(readings, now, window):
    return [r for r in readings if now - r.taken_at <= window]




def check_stale_gps(vehicle, now):
    gps_time = (vehicle or {}).get("gps_time")
    if gps_time is None:
        return None

    age = now - gps_time
    if age > STALE_GPS_AFTER:
        return f"No GPS update in {int(age.total_seconds() // 60)} min"

    return None


def check_not_moving(readings, now, minutes):
    recent = _recent(readings, now, MOVE_WINDOW)
    if len(recent) < 2:
        return None
    first, last = recent[0], recent[-1]
    span = last.taken_at - first.taken_at
    if span < MOVE_MIN_SPAN:
        return None
    if first.feet is None or last.feet is None or last.feet < AT_STOP_FEET:
        return None
    progress = first.feet - last.feet
    if progress < MIN_PROGRESS_FEET:

        if minutes is not None:
            drive_minutes = last.feet / TRAVEL_FEET_PER_MIN
            if minutes > drive_minutes + LAYOVER_SLACK_MIN:
                return None
        minutes = round(span.total_seconds() / 60)
        return f"Bus has moved only {max(progress, 0)} ft in {minutes} min"
    return None


def check_impossible_eta(feet, minutes):
    if feet is None or minutes is None:
        return None

    mph = (feet / 5280) / (max(minutes, 1) / 60)
    if feet > 1500 and mph > MAX_PLAUSIBLE_MPH:
        return f"ETA implies {mph:.0f} mph"

    return None


def check_drift(readings, now):
    recent = [r for r in _recent(readings, now, DRIFT_WINDOW) if r.arrival]
    if len(recent) < 2:
        return None

    first, last = recent[0], recent[-1]

    span = last.taken_at - first.taken_at
    if span < DRIFT_MIN_SPAN:
        return None

    slip = last.arrival - first.arrival

    if slip >= DRIFT_LIMIT:
        return (
            f"Arrival estimate slid {round(slip.total_seconds() / 60)} min later "
            f"in the last {round(span.total_seconds() / 60)} min"
        )

    return None


def find_bunched(preds):
    groups = {}
    for p in preds:
        if p["minutes"] is None:
            continue
        key = (p["route"], p.get("direction") or p.get("destination"))
        groups.setdefault(key, []).append(p)
 
    bunched = set()
    for group in groups.values():
        group.sort(key=lambda p: p["minutes"])
        for a, b in zip(group, group[1:]):
            if b["minutes"] - a["minutes"] <= BUNCH_MINUTES:
                bunched.add(a["vehicle_id"])
                bunched.add(b["vehicle_id"])
    return bunched





def _label(score, ghost):
    if ghost:
        return "Ghost bus"

    if score >= 80:
        return "Reliable"

    if score >= 40:
        return "Shaky"

    return "Unreliable"





def analyze_stop(stop_id, predictions, vehicles, now=None):

    now = now or datetime.now(CHICAGO)

    enriched = []
    for p in predictions:
        if not p.get("vehicle_id"):
            continue

        e = {
            **p,
            "minutes": parse_countdown(p.get("minutes_away")),
            "feet": _to_int(p.get("feet_from_stop")),
            "arrival": parse_cta_time(p.get("arrival_time")),
        }

        record(stop_id, e["vehicle_id"], e["feet"], e["arrival"], now)
        enriched.append(e)

    forget_missing(now)


    bunched = find_bunched(enriched)

    results = []

    for e in enriched:
        vid = e["vehicle_id"]
        readings = history[(stop_id, vid)]
        found = {
            "stale_gps": check_stale_gps(vehicles.get(vid), now),
            "not_moving": check_not_moving(readings, now, e["minutes"]),
            "impossible_eta": check_impossible_eta(e["feet"], e["minutes"]),
            "drift": check_drift(readings, now),
            "bunched": "Bunched with another bus on this route" if vid in bunched else None,
            "delayed": "CTA marks this bus delayed" if e.get("delayed") else None,
        }

        fired = {name: msg for name, msg in found.items() if msg}
        score = max(0, 100 - sum(PENALTIES[name] for name in fired))
        ghost = "stale_gps" in fired and "not_moving" in fired
        results.append(
            {
                "vehicle_id": vid,
                "route": e["route"],
                "destination": e["destination"],
                "arrival_time": e["arrival_time"],
                "minutes_away": e["minutes_away"],
                "minutes": e["minutes"],
                "feet": e["feet"],
                "score": score,
                "label": _label(score, ghost),
                "flags": list(fired.values()),
            }
        )

    results.sort(key=lambda r: (r["minutes"] is None, r["minutes"] or 0))
    return results
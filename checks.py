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
AT_STOP_FEET = 400
MAX_PLAUSIBLE_MPH = 30
DRIFT_WINDOW = timedelta(minutes=5)
DRIFT_MIN_SPAN = timedelta(minutes=3)
DRIFT_LIMIT = timedelta(minutes=3)
BUNCH_FEET = 1500
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
            return datetime.strftime(value, fmt).replace(tzinfo=CHICAGO)
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


def check_not_moving(readings, now):
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
        minutes = round(span.total_seconds() / 60)
        return f"Bus has moved only {max(progress, 0)} ft in {minutes} min"

    return None


import asyncio
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, time

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from checks import CHICAGO, analyze_stop, parse_vehicles
from deadline import add_deadline

load_dotenv()

CTA_API_KEY = os.environ.get("CTA_API_KEY", "")
CTA_BASE_URL = "https://www.ctabustracker.com/bustime/api/v3"

STOP_IDS = ["8187"]
POLL_SECONDS = 30
WINDOW_START = time(6, 30)
WINDOW_END = time(9, 0)
ALWAYS_POLL = os.environ.get("ALWAYS_POLL") == "1"

latest: dict[str, dict] = {}


def in_window(now: datetime) -> bool:
    return WINDOW_START <= now.time() <= WINDOW_END


async def get_predictions(stop_id: str) -> list[dict]:

    params = {
        "key":CTA_API_KEY,
        "stpid":stop_id,
        "format":"json",
    }

    async with httpx.AsyncClient(
    timeout=10,
    transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
    ) as client:
        response = await client.get(f"{CTA_BASE_URL}/getpredictions", params=params)
        response.raise_for_status()
        data = response.json()

    body = data.get("bustime-response", {})

    raw_predictions = body.get("prd", [])
    cleaned = []

    for p in raw_predictions:
        cleaned.append(
            {
                "vehicle_id": p.get("vid"),
                "route": p.get("rt"),
                "direction": p.get("rtdir"),
                "destination": p.get("des"),
                "arrival_time": p.get("prdtm"),
                "minutes_away": p.get("prdctdn"),
                "feet_from_stop": p.get("dstp"),
                "delayed": p.get("dly", False),
            }
        )

    return cleaned


async def get_vehicles(vehicle_ids: list[str]) -> list[dict]:
    unique_ids = list(dict.fromkeys(vehicle_ids))
    if not unique_ids:
        return []

    vehicles = []

    async with httpx.AsyncClient(
        timeout=10,
        transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
    ) as client:
        for start in range(0, len(unique_ids), 10):
            batch = unique_ids[start:start + 10]
            params = {
                "key": CTA_API_KEY,
                "vid": ",".join(batch),
                "format": "json",
                "tmres": "s",
            }
            response = await client.get(f"{CTA_BASE_URL}/getvehicles", params=params)
            response.raise_for_status()
            body = response.json().get("bustime-response", {})
            vehicles.extend(body.get("vehicle", []))

    return vehicles


async def poll_once() -> None:
    now = datetime.now(CHICAGO)

    predictions_by_stop = {}
    for stop_id in STOP_IDS:
        predictions_by_stop[stop_id] = await get_predictions(stop_id)

    vehicle_ids = [
        p["vehicle_id"]
        for predictions in predictions_by_stop.values()
        for p in predictions
        if p["vehicle_id"]
    ]
    vehicles = parse_vehicles(await get_vehicles(vehicle_ids))

    for stop_id, predictions in predictions_by_stop.items():
        latest[stop_id] = {
            "updated_at": now.isoformat(),
            "arrivals": add_deadline(analyze_stop(stop_id, predictions, vehicles, now)),
        }


async def poll_loop() -> None:
    while True:
        try:
            if ALWAYS_POLL or in_window(datetime.now(CHICAGO)):
                await poll_once()
        except Exception as exc:
            print(f"Poll failed, keeping last results: {exc!r}")
        await asyncio.sleep(POLL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="BrutallyHonestTracker", lifespan=lifespan)


@app.get("/stops/{stop_id}/predictions")
async def predictions_for_stop(stop_id: str):
    if stop_id not in STOP_IDS:
        raise HTTPException(status_code=404, detail="That stop is not being tracked")

    data = latest.get(stop_id, {"updated_at": None, "arrivals": []})
    return {
        **data,
        "polling_now": ALWAYS_POLL or in_window(datetime.now(CHICAGO)),
    }
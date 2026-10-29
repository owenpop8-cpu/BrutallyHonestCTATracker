import os
import httpx
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

CTA_API_KEY = os.environ.get("CTA_API_KEY", "")
CTA_BASE_URL = "https://www.ctabustracker.com/bustime/api/v3"

app = FastAPI(title="BrutallyHonestTracker")

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


    
@app.get("/stops/{stop_id}/predictions")
async def predictions_for_stop(stop_id: str):
    return await get_predictions(stop_id)


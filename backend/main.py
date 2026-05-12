# main.py
# FastAPI backend — all API routes
#
# Routes:
#   GET /                          — health check
#   GET /train/{train_no}/summary  — overall train stats
#   GET /train/{train_no}/by-station — delay per station
#   GET /train/{train_no}/by-day   — delay by day of week
#   GET /train/{train_no}/by-month — monthly trend
#   GET /zones/summary             — zone-wise punctuality
#   GET /search?q=rajdhani         — search trains

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from analytics import (
    get_train_summary,
    get_delay_by_station,
    get_delay_by_day,
    get_delay_by_month,
    get_zone_summary,
    search_trains
)

# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────

app = FastAPI(
    title       = "Train Delay Intelligence API",
    description = "Analytics API for Indian Railways delay patterns",
    version     = "1.0.0"
)

# Allow frontend (Vercel) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],   # tighten this after deployment
    allow_methods  = ["GET"],
    allow_headers  = ["*"],
)


# ─────────────────────────────────────────
# Route 1 — Health Check
# ─────────────────────────────────────────

@app.get("/")
def root():
    """
    Health check — confirms API is running.
    Vercel and Render use this to verify deployment.
    """
    return {
        "status":  "ok",
        "message": "Train Delay Intelligence API is running",
        "version": "1.0.0",
        "routes": [
            "/train/{train_no}/summary",
            "/train/{train_no}/by-station",
            "/train/{train_no}/by-day",
            "/train/{train_no}/by-month",
            "/zones/summary",
            "/search?q=<query>"
        ]
    }


# ─────────────────────────────────────────
# Route 2 — Train Summary
# ─────────────────────────────────────────

@app.get("/train/{train_no}/summary")
def train_summary(train_no: str):
    """
    Returns overall stats for a train:
    - Average delay, on-time %, worst station,
      best/worst day, total records collected.

    Example: GET /train/12650/summary
    """
    # Validate train number — must be digits only
    if not train_no.isdigit():
        raise HTTPException(
            status_code = 400,
            detail      = "Train number must contain digits only"
        )

    data = get_train_summary(train_no)

    if not data:
        raise HTTPException(
            status_code = 404,
            detail      = f"No data found for train {train_no}. "
                          f"Data may not have been collected yet."
        )

    return {
        "status": "ok",
        "train_no": train_no,
        "data": data
    }


# ─────────────────────────────────────────
# Route 3 — Delay by Station
# ─────────────────────────────────────────

@app.get("/train/{train_no}/by-station")
def delay_by_station(train_no: str):
    """
    Returns average delay at each station on the route.
    Ordered by delay rank (worst first).
    Used for the station bar chart on frontend.

    Example: GET /train/12650/by-station
    """
    if not train_no.isdigit():
        raise HTTPException(status_code=400, detail="Invalid train number")

    data = get_delay_by_station(train_no)

    if not data:
        raise HTTPException(
            status_code = 404,
            detail      = f"No station data found for train {train_no}"
        )

    return {
        "status":   "ok",
        "train_no": train_no,
        "count":    len(data),
        "data":     data
    }


# ─────────────────────────────────────────
# Route 4 — Delay by Day of Week
# ─────────────────────────────────────────

@app.get("/train/{train_no}/by-day")
def delay_by_day(train_no: str):
    """
    Returns average delay per day of week (Mon-Sun).
    Shows which day this train is most likely to be late.
    Used for the day-of-week bar chart.

    Example: GET /train/12650/by-day
    """
    if not train_no.isdigit():
        raise HTTPException(status_code=400, detail="Invalid train number")

    data = get_delay_by_day(train_no)

    return {
        "status":   "ok",
        "train_no": train_no,
        "data":     data
    }


# ─────────────────────────────────────────
# Route 5 — Delay by Month
# ─────────────────────────────────────────

@app.get("/train/{train_no}/by-month")
def delay_by_month(train_no: str):
    """
    Returns average delay per month.
    Shows monsoon vs winter performance trend.
    Used for the monthly trend line chart.

    Example: GET /train/12650/by-month
    """
    if not train_no.isdigit():
        raise HTTPException(status_code=400, detail="Invalid train number")

    data = get_delay_by_month(train_no)

    return {
        "status":   "ok",
        "train_no": train_no,
        "data":     data
    }


# ─────────────────────────────────────────
# Route 6 — Zone Summary
# ─────────────────────────────────────────

@app.get("/zones/summary")
def zones_summary():
    """
    Returns punctuality ranking across all railway zones.
    Uses CTE + window function in SQL.
    Powers the zone heatmap page.

    Example: GET /zones/summary
    """
    data = get_zone_summary()

    if not data:
        raise HTTPException(
            status_code = 404,
            detail      = "No zone data available yet"
        )

    return {
        "status": "ok",
        "count":  len(data),
        "data":   data
    }


# ─────────────────────────────────────────
# Route 7 — Search Trains
# ─────────────────────────────────────────

@app.get("/search")
def search(q: str = Query(..., min_length=1, description="Train name or number")):
    """
    Search trains by name or number.
    Partial match, case insensitive.

    Example: GET /search?q=rajdhani
             GET /search?q=12650
    """
    results = search_trains(q)

    return {
        "status": "ok",
        "query":  q,
        "count":  len(results),
        "data":   results
    }
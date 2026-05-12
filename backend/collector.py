# collector.py
# Uses IRCTC API on RapidAPI — irctc1 by IRCTCAPI

import os
import json
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("ERAIL_API_KEY", "")
BASE_URL = "https://irctc1.p.rapidapi.com/api/v1/liveTrainStatus"

HEADERS = {
    "x-rapidapi-key":  API_KEY,
    "x-rapidapi-host": "irctc1.p.rapidapi.com"
}

TRAINS = ["12650", "12951", "12301"]


def get_today():
    return date.today().strftime("%Y%m%d")


def fetch_train_status(train_no, travel_date=None):
    if travel_date is None:
        travel_date = get_today()

    params = {
        "trainNo":   train_no,
        "startingStation": "",
        "endingStation":   "",
        "departureDate":   travel_date
    }

    print(f"\n📡 Fetching train {train_no} for date {travel_date}...")

    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)

        print(f"   HTTP Status: {response.status_code}")

        if response.status_code != 200:
            print(f"   ❌ Error: {response.text[:200]}")
            return None

        data = response.json()

        if not data.get("status"):
            print(f"   ⚠️  API returned: {data.get('message', 'Unknown error')}")
            return None

        stations = data.get("data", {}).get("upcoming_stations", [])
        print(f"   ✅ Got data — {len(stations)} upcoming stations found")
        return data

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def print_raw_response(data):
    if not data:
        print("No data.")
        return

    info = data.get("data", {})
    print("\n" + "="*60)
    print(f"🚆 Train : {info.get('train_name')} ({info.get('train_number')})")
    print(f"   From  : {info.get('source_stn_name')} ({info.get('source')})")
    print(f"   To    : {info.get('dest_stn_name')} ({info.get('destination')})")
    print(f"   Status: {info.get('status_as_of')}")
    print(f"   Delay : {info.get('delay')} mins")
    print(f"   Currently at: {info.get('current_station_name')} ({info.get('current_station_code')})")
    print(f"   Distance covered: {info.get('distance_from_source')} / {info.get('total_distance')} km")

    stations = info.get("upcoming_stations", [])
    print(f"\n📍 Upcoming Stations ({len(stations)} total):")
    print(f"   {'Name':<30} {'STA':<8} {'ETA':<8} {'Delay'}")
    print(f"   {'-'*30} {'-'*8} {'-'*8} {'-'*8}")

    for s in stations:
        name  = s.get("station_name", "")[:29]
        sta   = s.get("sta", "--")
        eta   = s.get("eta", "--")
        delay = s.get("arrival_delay", "-")
        print(f"   {name:<30} {sta:<8} {eta:<8} {delay}")

    print("\n🔍 First station raw JSON:")
    if stations:
        print(json.dumps(stations[0], indent=4))
    print("="*60)


def test_single_train():
    if not API_KEY:
        print("❌ API key not found in .env")
        return

    print("🚀 Testing IRCTC RapidAPI...")
    print(f"   Key: {API_KEY[:6]}{'*'*(len(API_KEY)-6)}")

    data = fetch_train_status("12650")
    print_raw_response(data)


if __name__ == "__main__":
    test_single_train()
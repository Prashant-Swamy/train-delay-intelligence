# collector.py
# Day 5 — parse station delay data from IRCTC RapidAPI
# Produces clean list of delay records ready for DB insert (Day 6)

import os
import json
import requests
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("ERAIL_API_KEY", "")
BASE_URL = "https://irctc1.p.rapidapi.com/api/v1/liveTrainStatus"

HEADERS = {
    "x-rapidapi-key":  API_KEY,
    "x-rapidapi-host": "irctc1.p.rapidapi.com"
}

# ─────────────────────────────────────────
# 50 popular trains to track
# ─────────────────────────────────────────
TRAINS = [
    "12650", "12651",  # Karnataka Sampark Kranti
    "12951", "12952",  # Mumbai Rajdhani
    "12301", "12302",  # Howrah Rajdhani
    "22221", "22222",  # CSMT Rajdhani
    "12002",           # Bhopal Shatabdi
    "12009", "12010",  # Mumbai Shatabdi
    "12627", "12628",  # Karnataka Express
    "12657", "12658",  # Chennai Mail
    "16093", "16094",  # Lucknow Express
    "12491", "12492",  # Maur Dhawaj Express
    "12451", "12452",  # Shram Shakti Express
    "12589", "12590",  # Gorakhpur Express
    "12391", "12392",  # Shramjeevi Express
    "12553", "12554",  # Vaishali Express
    "12559", "12560",  # Shiv Ganga Express
    "12381", "12382",  # Poorva Express
    "12801", "12802",  # Purushottam Express
    "12875", "12876",  # Neelachal Express
    "12505", "12506",  # North East Express
    "12273", "12274",  # Duronto Express
    "12259", "12260",  # Sealdah Duronto
    "12019", "12020",  # Howrah Shatabdi
    "12023", "12024",  # Pune Shatabdi
    "12011", "12012",  # Kalka Shatabdi
]


# ─────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────

def get_today():
    """Returns today's date in YYYYMMDD format for API call."""
    return date.today().strftime("%Y%m%d")


def clean_station_name(name):
    """
    Removes dirty characters from station names.
    API sometimes returns 'BHANDAI~' or 'AGRA CANTT~'
    """
    return name.replace("~", "").strip()


def parse_delay_mins(delay_value):
    """
    Converts delay value from API to integer minutes.
    API returns integer directly — but we guard against None or empty.
    """
    try:
        return int(delay_value)
    except (TypeError, ValueError):
        return 0


def get_day_of_week(date_obj=None):
    """Returns day name like 'Monday', 'Tuesday' etc."""
    if date_obj is None:
        date_obj = date.today()
    return date_obj.strftime("%A")


def get_month(date_obj=None):
    """Returns month as integer 1-12."""
    if date_obj is None:
        date_obj = date.today()
    return date_obj.month


# ─────────────────────────────────────────
# API fetch
# ─────────────────────────────────────────

def fetch_train_status(train_no, travel_date=None):
    """
    Calls IRCTC RapidAPI for a single train.
    Returns full JSON response or None on failure.
    """
    if travel_date is None:
        travel_date = get_today()

    params = {
        "trainNo":         train_no,
        "startingStation": "",
        "endingStation":   "",
        "departureDate":   travel_date
    }

    try:
        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            print(f"   ❌ HTTP {response.status_code} for train {train_no}")
            return None

        data = response.json()

        if not data.get("status"):
            print(f"   ⚠️  API error for {train_no}: {data.get('message')}")
            return None

        return data

    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout for train {train_no}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error for train {train_no}")
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error for train {train_no}: {e}")
        return None


# ─────────────────────────────────────────
# Core parser — this is the main function
# ─────────────────────────────────────────

def parse_delay_records(train_no, raw_data):
    """
    Takes raw API response and returns a clean list of delay records.
    Each record = one station's delay data for today.

    Returns list of dicts like:
    {
        "train_no":      "12650",
        "station_code":  "GWL",
        "station_name":  "GWALIOR JN",
        "scheduled_arr": "11:43",
        "actual_arr":    "11:43",
        "delay_mins":    0,
        "recorded_on":   date(2026, 5, 14),
        "day_of_week":   "Thursday",
        "month":         5
    }
    """
    if not raw_data:
        return []

    info     = raw_data.get("data", {})
    today    = date.today()
    records  = []

    # Get upcoming stations list
    upcoming = info.get("upcoming_stations", [])

    # Also grab current station separately
    current_code = info.get("current_station_code", "")
    current_name = info.get("current_station_name", "")
    current_delay = info.get("delay", 0)
    cur_sta  = info.get("cur_stn_sta", "")
    cur_eta  = info.get("eta", "")

    # Add current station as a record if it has valid data
    if current_code and current_code.strip():
        records.append({
            "train_no":      train_no,
            "station_code":  current_code.strip(),
            "station_name":  clean_station_name(current_name),
            "scheduled_arr": cur_sta,
            "actual_arr":    cur_eta,
            "delay_mins":    parse_delay_mins(current_delay),
            "recorded_on":   today,
            "day_of_week":   get_day_of_week(today),
            "month":         get_month(today)
        })

    # Parse each upcoming station
    for station in upcoming:
        code  = station.get("station_code", "").strip()
        name  = station.get("station_name", "").strip()

        # Skip blank/empty stations (first entry in API is sometimes empty)
        if not code or not name:
            continue

        sta   = station.get("sta", "")       # scheduled arrival
        eta   = station.get("eta", "")       # estimated actual arrival
        delay = station.get("arrival_delay", 0)

        record = {
            "train_no":      train_no,
            "station_code":  code,
            "station_name":  clean_station_name(name),
            "scheduled_arr": sta,
            "actual_arr":    eta,
            "delay_mins":    parse_delay_mins(delay),
            "recorded_on":   today,
            "day_of_week":   get_day_of_week(today),
            "month":         get_month(today)
        }
        records.append(record)

    return records


def print_parsed_records(train_no, records, raw_data):
    """Prints parsed delay records in a clean readable format."""

    info = raw_data.get("data", {})

    print("\n" + "=" * 65)
    print(f"🚆 {info.get('train_name')} ({train_no})")
    print(f"   {info.get('source_stn_name')} → {info.get('dest_stn_name')}")
    print(f"   Current delay : {info.get('delay')} mins")
    print(f"   Currently at  : {clean_station_name(info.get('current_station_name', ''))}")
    print(f"   Recorded on   : {date.today()} ({get_day_of_week()})")
    print(f"   Total records : {len(records)} stations")
    print("=" * 65)

    print(f"\n{'#':<4} {'Code':<8} {'Station Name':<30} {'Sched':<8} {'Actual':<8} {'Delay'}")
    print(f"{'-'*4} {'-'*8} {'-'*30} {'-'*8} {'-'*8} {'-'*6}")

    for i, r in enumerate(records, 1):
        delay_str = f"{r['delay_mins']} min" if r['delay_mins'] > 0 else "On time"
        print(
            f"{i:<4} "
            f"{r['station_code']:<8} "
            f"{r['station_name']:<30} "
            f"{r['scheduled_arr']:<8} "
            f"{r['actual_arr']:<8} "
            f"{delay_str}"
        )

    print("\n✅ Sample record (what will go into DB tomorrow):")
    if records:
        print(json.dumps(
            {**records[0], "recorded_on": str(records[0]["recorded_on"])},
            indent=4
        ))
    print("=" * 65)


# ─────────────────────────────────────────
# Database save
# ─────────────────────────────────────────

def save_records_to_db(records):
    """
    Saves a list of parsed delay records into the delay_records table.
    Skips duplicates — same train + station + date won't be inserted twice.
    Returns count of newly inserted records.
    """
    if not records:
        return 0

    # Import here to avoid circular imports
    from database import SessionLocal
    from models import DelayRecord
    from datetime import time as dtime

    db = SessionLocal()
    inserted = 0
    skipped  = 0

    try:
        for r in records:
            # Check for duplicate — same train, station, date
            existing = db.query(DelayRecord).filter_by(
                train_no     = r["train_no"],
                station_code = r["station_code"],
                recorded_on  = r["recorded_on"]
            ).first()

            if existing:
                skipped += 1
                continue

            # Parse scheduled_arr string to time object
            def parse_time(t_str):
                """Converts '11:43' string to Python time object."""
                try:
                    return datetime.strptime(t_str, "%H:%M").time()
                except (ValueError, TypeError):
                    return None

            record = DelayRecord(
                train_no      = r["train_no"],
                station_code  = r["station_code"],
                station_name  = r["station_name"],
                scheduled_arr = parse_time(r["scheduled_arr"]),
                actual_arr    = parse_time(r["actual_arr"]),
                delay_mins    = r["delay_mins"],
                recorded_on   = r["recorded_on"],
                day_of_week   = r["day_of_week"],
                month         = r["month"]
            )
            db.add(record)
            inserted += 1

        db.commit()
        return inserted

    except Exception as e:
        db.rollback()
        print(f"   ❌ DB error: {e}")
        return 0

    finally:
        db.close()


# ─────────────────────────────────────────
# Full collection run — all trains
# ─────────────────────────────────────────

def run_collection():
    """
    Main pipeline — runs for all trains in TRAINS list.
    Fetch → Parse → Save for each train.
    Called by scheduler every 6 hours.
    """
    import time

    today     = date.today()
    total_inserted = 0
    total_failed   = 0

    print("\n" + "🔁 "*20)
    print(f"🚀 Starting collection run — {today} ({get_day_of_week()})")
    print(f"   Trains to process: {len(TRAINS)}")
    print("🔁 "*20)

    for i, train_no in enumerate(TRAINS, 1):
        print(f"\n[{i}/{len(TRAINS)}] Train {train_no}")

        # Fetch
        raw_data = fetch_train_status(train_no)
        if not raw_data:
            print(f"   ⚠️  Skipping — no data returned")
            total_failed += 1
            time.sleep(2)
            continue

        # Parse
        records = parse_delay_records(train_no, raw_data)
        if not records:
            print(f"   ⚠️  Skipping — no stations parsed")
            total_failed += 1
            time.sleep(2)
            continue

        print(f"   📊 Parsed {len(records)} station records")

        # Save
        inserted = save_records_to_db(records)
        print(f"   💾 Saved {inserted} new records to DB")

        total_inserted += inserted

        # Polite delay between API calls — avoid rate limiting
        time.sleep(3)

    print("\n" + "="*50)
    print(f"✅ Collection run complete!")
    print(f"   Trains processed : {len(TRAINS) - total_failed}/{len(TRAINS)}")
    print(f"   Records inserted : {total_inserted}")
    print(f"   Trains failed    : {total_failed}")
    print("="*50)


# ─────────────────────────────────────────
# Test — single train full pipeline
# ─────────────────────────────────────────

def test_full_pipeline():
    """
    Tests complete pipeline for one train:
    Fetch → Parse → Save → Verify from DB
    """
    if not API_KEY:
        print("❌ API key not found in .env")
        return

    from database import SessionLocal
    from models import DelayRecord

    print("🚀 Day 6 — Testing full pipeline (fetch → parse → save)...")
    print(f"   API Key: {API_KEY[:6]}{'*' * (len(API_KEY)-6)}\n")

    train_no = "12650"

    # Step 1 — Fetch
    print(f"📡 Step 1: Fetching train {train_no}...")
    raw_data = fetch_train_status(train_no)
    if not raw_data:
        print("❌ Fetch failed")
        return
    print(f"   ✅ Fetched successfully")

    # Step 2 — Parse
    print(f"\n📊 Step 2: Parsing station records...")
    records = parse_delay_records(train_no, raw_data)
    print(f"   ✅ Parsed {len(records)} station records")

    # Step 3 — Save
    print(f"\n💾 Step 3: Saving to PostgreSQL...")
    inserted = save_records_to_db(records)
    print(f"   ✅ Inserted {inserted} new records")

    # Step 4 — Verify from DB
    print(f"\n🔍 Step 4: Verifying from database...")
    db = SessionLocal()
    try:
        db_records = db.query(DelayRecord).filter_by(
            train_no    = train_no,
            recorded_on = date.today()
        ).all()

        print(f"   ✅ Found {len(db_records)} records in DB for today")
        print(f"\n   Sample records from DB:")
        print(f"   {'Code':<8} {'Station':<28} {'Delay':<8} {'Day'}")
        print(f"   {'-'*8} {'-'*28} {'-'*8} {'-'*10}")

        for rec in db_records[:5]:  # show first 5
            print(
                f"   {rec.station_code:<8} "
                f"{rec.station_name:<28} "
                f"{rec.delay_mins:<8} "
                f"{rec.day_of_week}"
            )

        if len(db_records) > 5:
            print(f"   ... and {len(db_records) - 5} more records")

    finally:
        db.close()

    print(f"\n🎉 Full pipeline working! Data is in PostgreSQL.")


if __name__ == "__main__":
    test_full_pipeline()
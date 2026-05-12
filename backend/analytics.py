# analytics.py
# All SQL analytics queries for the dashboard
# Called by FastAPI routes in main.py
#
# Queries:
#   1. get_train_summary()       — on-time %, avg delay, worst station
#   2. get_delay_by_station()    — delay per station on route
#   3. get_delay_by_day()        — avg delay per day of week
#   4. get_delay_by_month()      — monthly trend
#   5. get_zone_summary()        — zone-wise punctuality
#   6. search_trains()           — search by train name/number

from sqlalchemy import text
from database import SessionLocal


# ─────────────────────────────────────────
# Helper
# ─────────────────────────────────────────

def get_db():
    """Returns a new DB session."""
    return SessionLocal()


# ─────────────────────────────────────────
# Query 1 — Train Summary
# ─────────────────────────────────────────

def get_train_summary(train_no):
    """
    Returns overall summary for a train:
    - Average delay in minutes
    - On-time percentage (delay <= 5 mins)
    - Worst station (highest avg delay)
    - Best day (lowest avg delay)
    - Worst day (highest avg delay)
    - Total records collected
    """
    db = get_db()
    try:
        result = db.execute(text("""
            SELECT
                train_no,
                ROUND(AVG(delay_mins), 1)                              AS avg_delay,
                ROUND(
                    COUNT(*) FILTER (WHERE delay_mins <= 5) * 100.0
                    / NULLIF(COUNT(*), 0)
                , 1)                                                    AS on_time_pct,
                COUNT(*)                                                AS total_records
            FROM delay_records
            WHERE train_no = :train_no
            AND   recorded_on >= NOW() - INTERVAL '30 days'
            GROUP BY train_no
        """), {"train_no": train_no}).fetchone()

        if not result:
            return None

        # Get worst station using window function
        worst = db.execute(text("""
            SELECT station_name,
                   ROUND(AVG(delay_mins), 1) AS avg_delay
            FROM delay_records
            WHERE train_no = :train_no
            GROUP BY station_name
            ORDER BY AVG(delay_mins) DESC
            LIMIT 1
        """), {"train_no": train_no}).fetchone()

        # Get best and worst day
        days = db.execute(text("""
            SELECT day_of_week,
                   ROUND(AVG(delay_mins), 1) AS avg_delay
            FROM delay_records
            WHERE train_no = :train_no
            GROUP BY day_of_week
            ORDER BY AVG(delay_mins) ASC
        """), {"train_no": train_no}).fetchall()

        return {
            "train_no":      train_no,
            "avg_delay":     float(result.avg_delay or 0),
            "on_time_pct":   float(result.on_time_pct or 0),
            "total_records": int(result.total_records or 0),
            "worst_station": worst.station_name if worst else "N/A",
            "worst_station_delay": float(worst.avg_delay or 0) if worst else 0,
            "best_day":      days[0].day_of_week if days else "N/A",
            "worst_day":     days[-1].day_of_week if days else "N/A",
        }

    finally:
        db.close()


# ─────────────────────────────────────────
# Query 2 — Delay by Station
# ─────────────────────────────────────────

def get_delay_by_station(train_no):
    """
    Returns average delay at each station on the route.
    Used for the bar chart on train detail page.
    Includes delay rank using window function.
    """
    db = get_db()
    try:
        results = db.execute(text("""
            SELECT
                station_code,
                station_name,
                ROUND(AVG(delay_mins), 1)   AS avg_delay,
                COUNT(*)                     AS sample_count,
                RANK() OVER (
                    ORDER BY AVG(delay_mins) DESC
                )                            AS delay_rank
            FROM delay_records
            WHERE train_no = :train_no
            GROUP BY station_code, station_name
            ORDER BY delay_rank
        """), {"train_no": train_no}).fetchall()

        return [
            {
                "station_code":  r.station_code,
                "station_name":  r.station_name,
                "avg_delay":     float(r.avg_delay or 0),
                "sample_count":  int(r.sample_count),
                "delay_rank":    int(r.delay_rank)
            }
            for r in results
        ]

    finally:
        db.close()


# ─────────────────────────────────────────
# Query 3 — Delay by Day of Week
# ─────────────────────────────────────────

def get_delay_by_day(train_no):
    """
    Returns average delay per day of week — Mon to Sun.
    Used for the day-of-week bar chart.
    Shows which day this train is most likely to be late.
    """
    db = get_db()

    # Fixed order for days
    day_order = [
        "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday"
    ]

    try:
        results = db.execute(text("""
            SELECT
                day_of_week,
                ROUND(AVG(delay_mins), 1) AS avg_delay,
                COUNT(*)                  AS sample_count
            FROM delay_records
            WHERE train_no = :train_no
            GROUP BY day_of_week
            ORDER BY AVG(delay_mins) DESC
        """), {"train_no": train_no}).fetchall()

        # Build dict for easy lookup
        day_map = {r.day_of_week: r for r in results}

        return [
            {
                "day":          day,
                "avg_delay":    float(day_map[day].avg_delay) if day in day_map else 0.0,
                "sample_count": int(day_map[day].sample_count) if day in day_map else 0
            }
            for day in day_order
        ]

    finally:
        db.close()


# ─────────────────────────────────────────
# Query 4 — Delay by Month
# ─────────────────────────────────────────

def get_delay_by_month(train_no):
    """
    Returns average delay per month.
    Shows monsoon vs winter performance trend.
    """
    db = get_db()

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    try:
        results = db.execute(text("""
            SELECT
                month,
                ROUND(AVG(delay_mins), 1) AS avg_delay,
                COUNT(*)                  AS sample_count
            FROM delay_records
            WHERE train_no = :train_no
            GROUP BY month
            ORDER BY month ASC
        """), {"train_no": train_no}).fetchall()

        return [
            {
                "month":        r.month,
                "month_name":   month_names.get(r.month, str(r.month)),
                "avg_delay":    float(r.avg_delay or 0),
                "sample_count": int(r.sample_count)
            }
            for r in results
        ]

    finally:
        db.close()


# ─────────────────────────────────────────
# Query 5 — Zone Summary
# ─────────────────────────────────────────

def get_zone_summary():
    """
    Returns punctuality stats per railway zone.
    Uses CTE + window function for zone ranking.
    Powers the zone heatmap page.
    """
    db = get_db()
    try:
        results = db.execute(text("""
            WITH zone_stats AS (
                SELECT
                    t.zone,
                    ROUND(AVG(d.delay_mins), 1)                          AS avg_delay,
                    ROUND(
                        COUNT(*) FILTER (WHERE d.delay_mins <= 5) * 100.0
                        / NULLIF(COUNT(*), 0)
                    , 1)                                                  AS on_time_pct,
                    COUNT(DISTINCT d.train_no)                            AS trains_tracked,
                    COUNT(*)                                              AS total_records
                FROM delay_records d
                JOIN trains t USING (train_no)
                WHERE d.recorded_on >= NOW() - INTERVAL '30 days'
                GROUP BY t.zone
            )
            SELECT
                zone,
                avg_delay,
                on_time_pct,
                trains_tracked,
                total_records,
                RANK() OVER (ORDER BY on_time_pct DESC) AS punctuality_rank
            FROM zone_stats
            ORDER BY punctuality_rank
        """)).fetchall()

        return [
            {
                "zone":              r.zone,
                "avg_delay":         float(r.avg_delay or 0),
                "on_time_pct":       float(r.on_time_pct or 0),
                "trains_tracked":    int(r.trains_tracked),
                "total_records":     int(r.total_records),
                "punctuality_rank":  int(r.punctuality_rank)
            }
            for r in results
        ]

    finally:
        db.close()


# ─────────────────────────────────────────
# Query 6 — Search Trains
# ─────────────────────────────────────────

def search_trains(query):
    """
    Returns matching trains by name or number.
    Case insensitive partial match.
    """
    db = get_db()
    try:
        results = db.execute(text("""
            SELECT
                train_no,
                train_name,
                zone,
                from_station,
                to_station
            FROM trains
            WHERE train_no   ILIKE :q
            OR    train_name ILIKE :q
            ORDER BY train_name
            LIMIT 10
        """), {"q": f"%{query}%"}).fetchall()

        return [
            {
                "train_no":     r.train_no,
                "train_name":   r.train_name,
                "zone":         r.zone,
                "from_station": r.from_station,
                "to_station":   r.to_station
            }
            for r in results
        ]

    finally:
        db.close()


# ─────────────────────────────────────────
# Test all queries
# ─────────────────────────────────────────

def test_analytics():
    """Run all analytics queries and print results."""

    TEST_TRAIN = "12650"

    print("🧪 Testing all analytics queries...")
    print(f"   Test train: {TEST_TRAIN}\n")

    # Query 1
    print("─" * 50)
    print("📊 Query 1 — Train Summary")
    summary = get_train_summary(TEST_TRAIN)
    if summary:
        print(f"   Avg delay     : {summary['avg_delay']} mins")
        print(f"   On-time %     : {summary['on_time_pct']}%")
        print(f"   Worst station : {summary['worst_station']}")
        print(f"   Best day      : {summary['best_day']}")
        print(f"   Worst day     : {summary['worst_day']}")
        print(f"   Total records : {summary['total_records']}")
    else:
        print("   ⚠️  No data yet — need more collection runs")

    # Query 2
    print("\n─" * 50)
    print("📊 Query 2 — Delay by Station")
    stations = get_delay_by_station(TEST_TRAIN)
    if stations:
        print(f"   {'Rank':<6} {'Code':<8} {'Station':<28} {'Avg Delay'}")
        for s in stations[:5]:
            print(f"   {s['delay_rank']:<6} {s['station_code']:<8} {s['station_name']:<28} {s['avg_delay']} mins")
        if len(stations) > 5:
            print(f"   ... and {len(stations)-5} more stations")
    else:
        print("   ⚠️  No data yet")

    # Query 3
    print("\n─" * 50)
    print("📊 Query 3 — Delay by Day of Week")
    days = get_delay_by_day(TEST_TRAIN)
    if days:
        for d in days:
            bar = "█" * int(d['avg_delay']) if d['avg_delay'] > 0 else "░"
            print(f"   {d['day']:<12} {bar:<20} {d['avg_delay']} mins ({d['sample_count']} samples)")
    else:
        print("   ⚠️  No data yet")

    # Query 4
    print("\n─" * 50)
    print("📊 Query 4 — Delay by Month")
    months = get_delay_by_month(TEST_TRAIN)
    if months:
        for m in months:
            print(f"   {m['month_name']:<6} {m['avg_delay']} mins ({m['sample_count']} samples)")
    else:
        print("   ⚠️  No data yet")

    # Query 5
    print("\n─" * 50)
    print("📊 Query 5 — Zone Summary")
    zones = get_zone_summary()
    if zones:
        print(f"   {'Rank':<6} {'Zone':<6} {'On-time%':<12} {'Avg Delay':<12} {'Trains'}")
        for z in zones:
            print(f"   {z['punctuality_rank']:<6} {z['zone']:<6} {z['on_time_pct']:<12} {z['avg_delay']:<12} {z['trains_tracked']}")
    else:
        print("   ⚠️  No data yet — need trains table joined with delay_records")

    # Query 6
    print("\n─" * 50)
    print("📊 Query 6 — Search Trains")
    results = search_trains("rajdhani")
    if results:
        for r in results:
            print(f"   {r['train_no']} — {r['train_name']} ({r['zone']})")
    else:
        print("   ⚠️  No trains found — check trains table is seeded")

    print("\n✅ Analytics test complete!")


if __name__ == "__main__":
    test_analytics()
# models.py
# Defines all database tables using SQLAlchemy ORM
# Three tables: trains, delay_records, zone_summary

from sqlalchemy import (
    Column, String, Integer, Float,
    Date, Time, ForeignKey, Text
)
from database import Base, engine


# ─────────────────────────────────────────
# Table 1 — trains
# One row per train we are tracking
# ─────────────────────────────────────────
class Train(Base):
    __tablename__ = "trains"

    train_no      = Column(String(10), primary_key=True)
    train_name    = Column(String(100), nullable=False)
    zone          = Column(String(10))   # CR, SR, NR, ER, WR etc.
    from_station  = Column(String(10))   # origin station code
    to_station    = Column(String(10))   # destination station code

    def __repr__(self):
        return f"<Train {self.train_no} — {self.train_name}>"


# ─────────────────────────────────────────
# Table 2 — delay_records
# Core table — one row per station per train per day
# ─────────────────────────────────────────
class DelayRecord(Base):
    __tablename__ = "delay_records"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    train_no      = Column(String(10), ForeignKey("trains.train_no"), nullable=False)
    station_code  = Column(String(10), nullable=False)
    station_name  = Column(String(100))
    scheduled_arr = Column(Time)         # scheduled arrival time
    actual_arr    = Column(Time)         # actual arrival time
    delay_mins    = Column(Integer)      # actual - scheduled in minutes
    recorded_on   = Column(Date, nullable=False)
    day_of_week   = Column(String(10))   # Monday, Tuesday...
    month         = Column(Integer)      # 1–12

    def __repr__(self):
        return f"<DelayRecord {self.train_no} @ {self.station_code} — {self.delay_mins} mins>"


# ─────────────────────────────────────────
# Table 3 — zone_summary
# Updated weekly by cron job
# Aggregated punctuality per railway zone
# ─────────────────────────────────────────
class ZoneSummary(Base):
    __tablename__ = "zone_summary"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    zone            = Column(String(10), nullable=False)  # CR, SR, NR etc.
    week_start      = Column(Date, nullable=False)
    avg_delay       = Column(Float)       # average delay in minutes
    on_time_pct     = Column(Float)       # % of trains with delay <= 5 mins
    trains_tracked  = Column(Integer)     # how many trains contributed

    def __repr__(self):
        return f"<ZoneSummary {self.zone} w/e {self.week_start} — {self.on_time_pct}% on time>"


# ─────────────────────────────────────────
# Create all tables in the database
# ─────────────────────────────────────────
def create_tables():
    """
    Creates all tables if they do not already exist.
    Safe to run multiple times — won't drop existing data.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
    print("   Tables: trains, delay_records, zone_summary")


if __name__ == "__main__":
    create_tables()
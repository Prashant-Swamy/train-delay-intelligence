# seed.py
# One-time script to load trains from CSV into the trains table
# Run once: python seed.py

import csv
import os
import sys

# Make sure imports work from backend folder
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Train, create_tables

def seed_trains():
    """Read train_list.csv and insert rows into trains table."""

    # Path to CSV — one level up from backend/
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "train_list.csv")

    db = SessionLocal()

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0

            for row in reader:
                # Check if train already exists — avoid duplicates
                existing = db.query(Train).filter_by(train_no=row["train_no"]).first()
                if existing:
                    print(f"   ⚠️  Train {row['train_no']} already exists — skipping")
                    continue

                train = Train(
                    train_no     = row["train_no"].strip(),
                    train_name   = row["train_name"].strip(),
                    zone         = row["zone"].strip(),
                    from_station = row["from_station"].strip(),
                    to_station   = row["to_station"].strip()
                )
                db.add(train)
                count += 1
                print(f"   ✅ Added: {row['train_no']} — {row['train_name']}")

            db.commit()
            print(f"\n🎉 Done! {count} trains inserted into database.")

    except FileNotFoundError:
        print("❌ train_list.csv not found. Make sure data/train_list.csv exists.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()   # make sure tables exist first
    seed_trains()
# scheduler.py
# Runs the data collector automatically every 6 hours
# Uses APScheduler — already installed in requirements.txt
#
# Schedule:
#   06:00 AM — morning collection
#   12:00 PM — afternoon collection
#   06:00 PM — evening collection
#   12:00 AM — midnight collection

import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from collector import run_collection

# ─────────────────────────────────────────
# Logging setup
# Writes logs to console + scheduler.log file
# ─────────────────────────────────────────

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers = [
        logging.StreamHandler(),                  # print to console
        logging.FileHandler("scheduler.log")      # save to file
    ]
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Job wrapper
# ─────────────────────────────────────────

def collection_job():
    """
    Wrapper around run_collection().
    Logs start and end time of each run.
    Catches any unexpected errors so scheduler keeps running.
    """
    start = datetime.now()
    logger.info("="*50)
    logger.info(f"Collection job STARTED at {start.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        run_collection()
        end = datetime.now()
        duration = (end - start).seconds
        logger.info(f"Collection job COMPLETED in {duration} seconds")

    except Exception as e:
        logger.error(f"Collection job FAILED: {e}")

    logger.info("="*50)


# ─────────────────────────────────────────
# Scheduler setup
# ─────────────────────────────────────────

def start_scheduler():
    """
    Creates and starts the scheduler.
    Runs collection_job at 6AM, 12PM, 6PM, 12AM every day.
    Blocking — keeps running until you press Ctrl+C.
    """
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    # Run at 6AM IST
    scheduler.add_job(
        collection_job,
        CronTrigger(hour=6, minute=0, timezone="Asia/Kolkata"),
        id   = "morning_collection",
        name = "Morning Collection (6AM IST)"
    )

    # Run at 12PM IST
    scheduler.add_job(
        collection_job,
        CronTrigger(hour=12, minute=0, timezone="Asia/Kolkata"),
        id   = "afternoon_collection",
        name = "Afternoon Collection (12PM IST)"
    )

    # Run at 6PM IST
    scheduler.add_job(
        collection_job,
        CronTrigger(hour=18, minute=0, timezone="Asia/Kolkata"),
        id   = "evening_collection",
        name = "Evening Collection (6PM IST)"
    )

    # Run at 12AM IST
    scheduler.add_job(
        collection_job,
        CronTrigger(hour=0, minute=0, timezone="Asia/Kolkata"),
        id   = "midnight_collection",
        name = "Midnight Collection (12AM IST)"
    )

    logger.info("="*50)
    logger.info("🚀 Train Delay Scheduler STARTED")
    logger.info("   Timezone : Asia/Kolkata (IST)")
    logger.info("   Schedule : 6AM | 12PM | 6PM | 12AM")
    logger.info("   Press Ctrl+C to stop")
    logger.info("="*50)

    # Print next run times
    print("\n📅 Scheduled jobs:")
    for job in scheduler.get_jobs():
        print(f"   • {job.name}")
        print(f"     Next run: {job.next_run_time}")

    print("\n⏳ Scheduler is running... (Ctrl+C to stop)\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user (Ctrl+C)")
        print("\n⛔ Scheduler stopped.")


# ─────────────────────────────────────────
# Test — run collection once immediately
# ─────────────────────────────────────────

def test_run_now():
    """
    Runs one collection immediately without waiting for schedule.
    Use this to test the full pipeline end to end.
    """
    print("🧪 Running one collection immediately for testing...")
    print("   (In production, scheduler.py runs this every 6 hours)\n")
    collection_job()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Run once immediately: python scheduler.py --now
        test_run_now()
    else:
        # Start the full scheduler: python scheduler.py
        start_scheduler()
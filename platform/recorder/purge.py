"""Retention job: delete recorded runs older than N days.

    python platform/recorder/purge.py <recorder.db> <days>

Run it from cron / Task Scheduler. Safe while the gateway runs (WAL; one short write transaction).
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recorder import Recorder  # noqa: E402


def main(db: str, days: float) -> int:
    rec = Recorder(db)
    try:
        return asyncio.run(rec.purge_before(time.time() - days * 86400))
    finally:
        rec.close()


if __name__ == "__main__":
    print(f"deleted {main(sys.argv[1], float(sys.argv[2]))} runs")

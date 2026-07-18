"""Prepare a single-patient, blank-slate demo: Rosa Alvarez (hero-a-stroke) only.

Run AFTER `python -m iliad.cli reset` (fresh seed). This script then:
  1. backs up the freshly seeded DB to iliad.full.db (restore = copy it back),
  2. deletes every other patient's rows (Rosa is the only patient left),
  3. scrubs Rosa's pre-seeded Placer artifacts — dispo assessments, care tasks,
     call log, placer chat thread, events — leaving only her base clinical
     chart, so Placer visibly builds everything itself from zero.

Usage:  python engine/scripts/solo_demo.py [--keep hero-a-stroke] [--db path]
Also wipe engine/placer.db before restarting the engine for a true cold start.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

PLACER_TABLES = ["dispo_assessments", "care_tasks", "communications", "placer_messages"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", default="hero-a-stroke")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parents[2] / "backend" / "iliad.db"))
    args = parser.parse_args()

    db = Path(args.db)
    if not db.exists():
        raise SystemExit(f"DB not found: {db} — run `python -m iliad.cli reset` first")

    backup = db.with_suffix(".full.db")
    shutil.copyfile(db, backup)
    print(f"backup -> {backup}")

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Every table carrying a patient_id column loses all non-kept patients.
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
        if "patient_id" in cols:
            cur.execute(f"DELETE FROM {table} WHERE patient_id IS NOT NULL AND patient_id != ?", (args.keep,))
            if cur.rowcount:
                print(f"  {table}: removed {cur.rowcount} other-patient rows")
    cur.execute("DELETE FROM patients WHERE id != ?", (args.keep,))
    print(f"  patients: removed {cur.rowcount}")

    # Blank Placer slate for the kept patient: base clinical chart only.
    for table in PLACER_TABLES:
        if table in tables:
            cur.execute(f"DELETE FROM {table} WHERE patient_id = ?", (args.keep,))
            print(f"  {table}: scrubbed {cur.rowcount} pre-seeded rows for {args.keep}")
    if "events" in tables:
        cur.execute("DELETE FROM events")
        print(f"  events: cleared {cur.rowcount} (fresh cursor for the engine)")

    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    print("done — restart backend + engine (rm engine/placer.db for a cold engine start)")


if __name__ == "__main__":
    main()

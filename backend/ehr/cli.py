"""Command-line interface: seed, reset, stats, and serve.

Usage:
    python -m ehr.cli reset            # drop + recreate + reseed (FHIR + heroes)
    python -m ehr.cli reset --no-fhir  # heroes + facilities only (fast)
    python -m ehr.cli seed             # seed only if the DB is empty
    python -m ehr.cli stats            # print row counts
    python -m ehr.cli serve --reload   # run the API with uvicorn
"""

from __future__ import annotations

import argparse
import json
import sys

from sqlmodel import Session, select

from . import config
from .db import engine, init_db
from .models import Patient
from .seed import reset_and_seed, row_counts


def _print_counts(counts: dict) -> None:
    width = max(len(k) for k in counts)
    for name, n in counts.items():
        print(f"  {name.ljust(width)}  {n}")


def cmd_reset(args: argparse.Namespace) -> int:
    print(f"Resetting database at {config.DATABASE_PATH} ...")
    counts = reset_and_seed(include_heroes=not args.no_heroes, include_fhir=not args.no_fhir)
    print("Done. Row counts:")
    _print_counts(counts)
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    init_db()
    with Session(engine) as session:
        empty = session.exec(select(Patient).limit(1)).first() is None
    if not empty and not args.force:
        print("Database already has data; use `reset` or pass --force to reseed.")
        return 0
    counts = reset_and_seed()
    print("Seeded. Row counts:")
    _print_counts(counts)
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    init_db()
    with Session(engine) as session:
        print(json.dumps(row_counts(session), indent=2))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("ehr.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ehr", description="Placer dummy EHR management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_reset = sub.add_parser("reset", help="Drop, recreate, and reseed the database")
    p_reset.add_argument("--no-heroes", action="store_true", help="Skip hero patients")
    p_reset.add_argument("--no-fhir", action="store_true", help="Skip importing the 25 FHIR patients")
    p_reset.set_defaults(func=cmd_reset)

    p_seed = sub.add_parser("seed", help="Seed the database if empty")
    p_seed.add_argument("--force", action="store_true", help="Reseed even if data exists")
    p_seed.set_defaults(func=cmd_seed)

    p_stats = sub.add_parser("stats", help="Print row counts")
    p_stats.set_defaults(func=cmd_stats)

    p_serve = sub.add_parser("serve", help="Run the API server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

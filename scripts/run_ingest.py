from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.config import get_settings
from pipeline.ingest import backfill_range, backfill_season, ingest_single_race


def main() -> None:
    parser = argparse.ArgumentParser(description="Run F1 Race Decoder ingestion workflows.")
    parser.add_argument("mode", choices=["single", "season", "range"])
    parser.add_argument("--season", type=int)
    parser.add_argument("--round", dest="round_number", type=int)
    parser.add_argument("--session-type", default="R")
    parser.add_argument("--season-start", type=int)
    parser.add_argument("--season-end", type=int)
    args = parser.parse_args()

    settings = get_settings()

    if args.mode == "single":
        if args.season is None or args.round_number is None:
            raise ValueError("single mode requires --season and --round")
        result = ingest_single_race(
            season=args.season,
            round_number=args.round_number,
            session_type=args.session_type,
            code_version=settings.code_version,
        )
    elif args.mode == "season":
        if args.season is None:
            raise ValueError("season mode requires --season")
        result = backfill_season(
            season=args.season,
            session_type=args.session_type,
            code_version=settings.code_version,
        )
    else:
        if args.season_start is None or args.season_end is None:
            raise ValueError("range mode requires --season-start and --season-end")
        result = backfill_range(
            season_start=args.season_start,
            season_end=args.season_end,
            session_type=args.session_type,
            code_version=settings.code_version,
        )

    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()

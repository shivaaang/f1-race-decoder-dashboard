from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.db import bootstrap_warehouse, query_df
from pipeline.ingest import refresh_schedule_for_season


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retry-based backfill for F1 races until all target seasons are ingested."
    )
    parser.add_argument("--season-start", type=int, default=2018)
    parser.add_argument("--season-end", type=int, default=2025)
    parser.add_argument("--max-passes", type=int, default=8)
    parser.add_argument("--sleep-race", type=float, default=1.0)
    parser.add_argument("--sleep-pass", type=float, default=20.0)
    parser.add_argument("--session-type", type=str, default="R")
    parser.add_argument("--code-version", type=str, default="dev")
    parser.add_argument("--single-timeout-seconds", type=int, default=1200)
    return parser.parse_args()


def _missing_rounds(season: int, session_type: str) -> list[int]:
    missing = query_df(
        """
        SELECT round
        FROM metadata.races_catalog
        WHERE season = %(season)s
          AND session_type = %(session_type)s
          AND round > 0
          AND is_ingested = FALSE
        ORDER BY round
        """,
        {"season": season, "session_type": session_type},
    )
    return [int(r) for r in missing["round"].tolist()]


def _remaining_count(season_start: int, season_end: int, session_type: str) -> int:
    remaining = query_df(
        """
        SELECT COUNT(*) AS c
        FROM metadata.races_catalog
        WHERE season BETWEEN %(season_start)s AND %(season_end)s
          AND session_type = %(session_type)s
          AND is_ingested = FALSE
        """,
        {
            "season_start": season_start,
            "season_end": season_end,
            "session_type": session_type,
        },
    )
    return int(remaining.iloc[0]["c"]) if not remaining.empty else 0


def _print_totals(season_start: int, season_end: int, session_type: str) -> None:
    totals = query_df(
        """
        SELECT season,
               COUNT(*) FILTER (WHERE is_ingested) AS ingested,
               COUNT(*) AS total
        FROM metadata.races_catalog
        WHERE season BETWEEN %(season_start)s AND %(season_end)s
          AND session_type = %(session_type)s
        GROUP BY season
        ORDER BY season
        """,
        {
            "season_start": season_start,
            "season_end": season_end,
            "session_type": session_type,
        },
    )
    print("season totals:")
    if totals.empty:
        print("  (no schedule rows found)")
    else:
        print(totals.to_string(index=False))


def _run_single_ingest(
    season: int,
    round_number: int,
    session_type: str,
    code_version: str,
    timeout_seconds: int,
) -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        "scripts/run_ingest.py",
        "single",
        "--season",
        str(season),
        "--round",
        str(round_number),
        "--session-type",
        session_type,
    ]
    env = os.environ.copy()
    env["CODE_VERSION"] = code_version

    try:
        completed = subprocess.run(  # noqa: S603
            cmd,
            cwd=repo_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
        )
        return completed.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main() -> None:
    args = parse_args()
    bootstrap_warehouse()

    for current_pass in range(1, args.max_passes + 1):
        print(f"=== pass {current_pass}/{args.max_passes} ===", flush=True)
        any_progress = False

        for season in range(args.season_start, args.season_end + 1):
            try:
                refresh_schedule_for_season(season=season, session_type=args.session_type)
                print(f"schedule_ok season={season}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"schedule_fail season={season} error={exc}", flush=True)
                continue

            rounds = _missing_rounds(season=season, session_type=args.session_type)
            print(f"season={season} missing={rounds}", flush=True)

            for round_number in rounds:
                try:
                    success = _run_single_ingest(
                        season=season,
                        round_number=round_number,
                        session_type=args.session_type,
                        code_version=args.code_version,
                        timeout_seconds=args.single_timeout_seconds,
                    )
                    if success:
                        print(
                            f"ingest_ok season={season} round={round_number} status=success",
                            flush=True,
                        )
                        any_progress = True
                    else:
                        print(
                            f"ingest_fail season={season} round={round_number} "
                            f"error=non_zero_or_timeout",
                            flush=True,
                        )
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"ingest_fail season={season} round={round_number} error={exc}",
                        flush=True,
                    )
                time.sleep(args.sleep_race)

        _print_totals(
            season_start=args.season_start,
            season_end=args.season_end,
            session_type=args.session_type,
        )
        remaining = _remaining_count(
            season_start=args.season_start,
            season_end=args.season_end,
            session_type=args.session_type,
        )
        print(f"remaining={remaining}", flush=True)

        if remaining == 0:
            print("ALL_DONE", flush=True)
            return

        if not any_progress:
            print("NO_PROGRESS_THIS_PASS", flush=True)

        time.sleep(args.sleep_pass)

    print("FINISHED_WITH_REMAINING", flush=True)


if __name__ == "__main__":
    main()

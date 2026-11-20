"""Fetch the Euroleague box scores of the LBA clubs that play it, for the starting-fives grid of the opponent analysis.

    python notebooks/euroleague_fetch.py              # every Euroleague club that is also an LBA team (matchup_report.EC_TEAM_MAP)
    python notebooks/euroleague_fetch.py --clubs VIR  # chosen EuroLeague club codes

Writes data/euroleague/results.csv (every game of the season) and appends the played games of those clubs to
data/euroleague_2026_raw.txt, the format of the EuroCup raw file (notebooks/eurocup_fetch.md).
"""
from __future__ import annotations

import argparse

import pandas as pd

import eurocup as ec
from matchup_report import EC_TEAM_MAP

DATA = ec.ROOT / "data"


def lba_club_codes(results: pd.DataFrame) -> list[str]:
    """Return the club codes of the teams in ``results`` that are also LBA teams (their name is in ``EC_TEAM_MAP``)."""
    names = {**dict(zip(results.home_code, results.home)), **dict(zip(results.away_code, results.away))}
    return sorted(code for code, name in names.items() if name.upper() in EC_TEAM_MAP)


def main() -> None:
    """Fetch the Euroleague results and the box scores of the chosen clubs into the data folder."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--clubs", nargs="*", help="EuroLeague club codes (default: the Euroleague clubs that are LBA teams)")
    a = ap.parse_args()
    results_csv = DATA / ec.EL_RESULTS_NAME
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    results = ec.fetch_results(competition=ec.EL_COMPETITION_CODE)
    results.to_csv(results_csv, index=False)
    clubs = a.clubs or lba_club_codes(results)
    added = ec.update_raw(results[results.home_code.isin(clubs) | results.away_code.isin(clubs)], DATA / ec.EL_RAW_NAME,
                          ec.EL_COMPETITION_CODE)
    print(f"{len(results)} Euroleague games -> {results_csv}; box scores of {len(added)} new game(s) of {clubs}: {added}")


if __name__ == "__main__":
    main()

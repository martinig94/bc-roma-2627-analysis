"""Fetch EuroCup results and club rosters (headshots) into data/eurocup/. See eurocup.py for what is written.

    python notebooks/eurocup_fetch.py                  # results, box scores and play-by-play of the new games + the rosters of the team and of every opponent in the schedule
    python notebooks/eurocup_fetch.py --clubs BCR MAN  # chosen EuroLeague club codes
"""
from __future__ import annotations

import argparse

import pandas as pd

import eurocup as ec
import weekly_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clubs", nargs="*", help="club codes whose rosters to fetch (default: the team, its opponents so far and the EuroCup opponents in weekly/schedule.csv)")
    a = ap.parse_args()
    team = weekly_config.load()["team"]
    ec.DATA.mkdir(parents=True, exist_ok=True)
    results = ec.fetch_results()
    results.to_csv(ec.DATA / "results.csv", index=False)
    print(f"{len(results)} games ({int(results.played.sum())} played) -> {ec.DATA / 'results.csv'}")
    added = ec.update_raw(results)
    print(f"box scores of {len(added)} new game(s) added to {ec.RAW.relative_to(ec.ROOT)}: {added}")
    added_pbp = ec.update_pbp(results)
    print(f"play-by-play of {len(added_pbp)} new game(s) added to {ec.PBP.relative_to(ec.ROOT)}: {added_pbp}")
    codes = a.clubs
    if not codes:
        codes = ec.club_codes(results, team, ec.ROOT / "weekly" / "schedule.csv")
    people = []
    for club in codes:
        try:
            people.append(ec.fetch_people(club))
        except Exception as exc:    # one club failing must not lose the others
            print(f"roster {club}: {exc}")
    if people:
        all_people = pd.concat(people, ignore_index=True)
        all_people.to_csv(ec.DATA / "people.csv", index=False)
        print(f"{len(all_people)} players, {ec.save_photos(all_people)} new headshots")


if __name__ == "__main__":
    main()

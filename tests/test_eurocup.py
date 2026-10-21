"""EuroCup standings from the results feed: groups, as-of-date tables, tie order. Synthetic data, no network."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "notebooks"))

import eurocup as ec  # noqa: E402


def results():
    rows = [
        # group 1: A, B, C, D (A beat B, B beat C, C beat A, everybody beat D; round 3 still to play)
        (1, 1, "2026-09-30", "A", "A", 90, "B", "B", 80, True),
        (2, 1, "2026-09-30", "C", "C", 85, "D", "D", 70, True),
        (3, 2, "2026-10-07", "B", "B", 88, "C", "C", 84, True),
        (4, 2, "2026-10-07", "D", "D", 60, "A", "A", 95, True),
        (5, 3, "2026-10-14", "C", "C", 0, "A", "A", 0, False),
        # group 2: E, F (never meet group 1)
        (6, 1, "2026-09-30", "E", "E", 70, "F", "F", 75, True),
    ]
    return pd.DataFrame(rows, columns=ec.RESULT_COLS)


def test_group_is_the_connected_teams():
    r = results()
    assert ec.group_teams(r, "A") == {"A", "B", "C", "D"}
    assert ec.group_teams(r, "E") == {"E", "F"}


def test_standings_only_use_games_before_the_date():
    r = results()
    t = ec.standings_before(r, "A", "2026-10-07")        # only the 30 Sep games
    assert set(t.index) == {"A", "B", "C", "D"}
    assert t.loc["A", "w"] == 1 and t.loc["B", "w"] == 0 and t.loc["D", "gp"] == 1
    t = ec.standings_before(r, "A", "2026-10-14")        # both played rounds, the third is not counted
    assert t.loc["A", "w"] == 2 and t.loc["A", "pos"] == 1
    assert t.loc["D", "l"] == 2


def test_other_group_is_not_mixed_in():
    t = ec.standings_before(results(), "E", "2026-10-14")
    assert set(t.index) == {"E", "F"} and t.loc["F", "pos"] == 1


def test_find_team_matches_spelling_differences():
    assert ec.find_team({"Kids&Us Manresa", "BC Roma"}, "Kids&Us Manresa") == "Kids&Us Manresa"
    assert ec.find_team({"Bahcesehir College Istanbul"}, "BAHCESEHIR COLLEGE ISTANBUL") == "Bahcesehir College Istanbul"


def test_club_codes_include_the_next_opponent_from_the_schedule(tmp_path):
    r = results().assign(home_code=lambda d: d.home, away_code=lambda d: d.away)
    sched = tmp_path / "schedule.csv"
    sched.write_text("date,time,competition,opponent,home,analysis\n2026-10-20,,EuroCup,D,0,\n2026-10-24,,LBA,Varese,1,\n")
    assert ec.club_codes(r, "A") == ["A", "B", "C", "D"]                  # A's opponents so far, A included
    assert ec.club_codes(r, "E", None) == ["E", "F"]                      # without the schedule: E and its opponent F
    assert ec.club_codes(r, "E", sched) == ["D", "E", "F"]                # the EuroCup row adds D, the LBA row is ignored


def test_raw_file_parser_takes_dates_and_club_codes_from_the_results_feed(tmp_path):
    """Games of any EuroCup team are in the raw file: dates and zone team names come from data/eurocup/results.csv, not from a fixed map."""
    from matchup_report import parse_eurocup
    (tmp_path / "eurocup").mkdir()
    r = results()
    r.loc[len(r)] = (7, 4, "2026-10-21", "BOS", "Bosna Bh Telecom Sarajevo", 80, "MAN", "Kids&Us Manresa", 70, True)
    r.to_csv(tmp_path / "eurocup" / "results.csv", index=False)
    row = lambda team, who, pts: f"7|{team}|{who}|1|10:00|{pts}|1|2|1|2|1|2|1|2|1|1|1|0|2|2|0|9"
    raw = tmp_path / "raw.txt"
    raw.write_text("\n".join(["BOX", row("BOSNA BH TELECOM SARAJEVO", "PERRY, REGINALD", 8), "7|BOSNA BH TELECOM SARAJEVO|TOTAL|||80|1|2|1|2|1|2|1|2|1|1|1|0|2|2||90",
                              "7|KIDS&US MANRESA|TOTAL|||70|1|2|1|2|1|2|1|2|1|1|1|0|2|2||80", "ZONES", "7|BOS|B|2FGM|4"]) + "\n", encoding="utf-8")
    box, zones = parse_eurocup(raw)
    assert set(box.date) == {"2026-10-21"} and set(box.team) == {"Bosna Bh Telecom Sarajevo", "Kids&Us Manresa"}
    assert list(zones.team) == ["Bosna Bh Telecom Sarajevo"]


def test_eurocup_shot_positions_round_trip_through_the_lba_shot_code():
    """data/eurocup/pbp.csv stores the EuroLeague centimetre coordinates as the percent-of-court x/y of the LBA play-by-play."""
    import lba_style
    cx, cy = 169.0, 696.0                                    # a corner-ish three, basket at the origin
    pbp = pd.DataFrame({"event": ["3 punti segnato"], "x": [(cy + 157.5) / 28], "y": [cx / 15 + 50], "player_surname": ["Sims"]})
    s = lba_style.shots_cm(pbp)
    assert abs(s.cx.iloc[0] - cx) < 1 and abs(s.cy.iloc[0] - cy) < 1 and s.made.iloc[0] and s.pts.iloc[0] == 3

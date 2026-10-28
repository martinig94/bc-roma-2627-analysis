"""
Energy indices per player — two separate scores, from box scores + play-by-play only (no play-style judgement):

  Rim activity = offensive rebounds, blocks, dunks and fouls drawn per 40 minutes
  High pace    = drive finishes ("Da penetrazione" / "Tiro in corsa"), fast-break shots + assists ("contropiede"),
                 fouls drawn and steals per 40 minutes, plus the share of own FGA taken within 8 s of the possession start
                 (fouls drawn count in both indices, on purpose)

Each component is z-scored against all league players with >= 40 minutes (clipped at ±3), the z-scores of an index are
averaged, and the average is shrunk towards 0 by minutes / (minutes + 120). The figure shows league percentiles.

LBA (legabasket play-by-play, data/pbp.csv + data/box_scores.csv):
    python notebooks/energy_indices.py "Openjobmetis Varese"            # one figure per team given; BC Roma always added
    python notebooks/energy_indices.py "Openjobmetis Varese" --through 2026-10-20   # only games up to a date

EuroCup opponent (EuroCup box scores + play-by-play, drives/transition from a Synergy pull):
    python notebooks/energy_indices.py --eurocup "Bosna Bh Telecom Sarajevo" --synergy data/synergy/bosna_2026-10-27
    (no dunks in the EuroCup feed; drives = Synergy "to basket" shots off P&R / isolation / spot-up / transition,
     fast break = Synergy transition shots; those two components are scaled on the LBA distribution and the
     percentiles are read off the LBA players, so the chart stays comparable with the LBA ones)

Output: reports/exploratory/energy_indices_<team>.png (--out/--name redirect the EuroCup opponent figure, e.g. into the matchup folder as 15_energy_indices.png) and energy_index_<league>.csv (all players).
"""
import argparse, datetime, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "exploratory"
sys.path.insert(0, str(ROOT / "notebooks"))

AUTHOR = "Giulia Martini"
K_MIN = 120.0          # minutes at which a player's own rates get half the weight
MIN_REF = 40           # minutes needed to be part of the league reference
RIM = ["oreb_p40", "blk_p40", "dunks_p40", "pf_drawn_p40"]
PACE = ["drive_finishes_p40", "fastbreak_inv_p40", "pf_drawn_p40", "stl_p40", "early_fga_share"]
START_EVENTS = ["Rimbalzo difensivo", "Palla recuperata", "Rimbalzi difensivi di squadra", "Inizio Tempo",
                "2 punti segnato", "3 punti segnato", "Tiro libero segnato"]
FGA_EVENTS = ["2 punti segnato", "2 punti sbagliato", "3 punti segnato", "3 punti sbagliato"]
MADE, MISS, LEAGUE = "#2563eb", "#c2410c", "#9ca3af"


def save_fig(fig, path, tries=6):
    """savefig with retries: a synced folder sometimes refuses a write for a few seconds."""
    for i in range(tries):
        try:
            fig.savefig(path, dpi=150); return
        except OSError:
            if i == tries - 1: raise
            time.sleep(2 * (i + 1))


def early_share(pbp, key):
    """Share of a player's FGA taken within 8 s of the possession start (start = last def. rebound, steal,
    period start or opponent's made basket / free throw), grouped by `key`."""
    p = pbp.sort_values(["game_id", "seq"]).copy()
    p["poss_start"] = np.where(p.event.isin(START_EVENTS), p.elapsed_sec, np.nan)
    p["poss_start"] = p.groupby("game_id").poss_start.ffill()
    f = p[p.event.isin(FGA_EVENTS)].copy()
    f["secs"] = f.elapsed_sec - f.poss_start
    f = f[(f.secs >= 0) & (f.secs <= 30)]
    return f.groupby(key).secs.apply(lambda v: (v <= 8).mean()).rename("early_fga_share")


def lba_table(through=None):
    """One row per LBA player: minutes, raw counts, per-40 rates, the two indices and their percentiles."""
    box = pd.read_csv(ROOT / "data" / "box_scores.csv")
    box = box[box.row_type == "player"].copy()
    pbp = pd.read_csv(ROOT / "data" / "pbp.csv")
    if through:
        box = box[box.match_datetime.str[:10] <= through]
        pbp = pbp[pbp.game_id.isin(box.game_id.unique())]
    t = (box.groupby(["player_id", "player_name", "player_surname"])
            .agg(team=("team", "last"), games=("game_id", "nunique"), minutes=("sec", lambda s: s.sum() / 60),
                 oreb=("oreb", "sum"), stl=("stl", "sum"), blk=("blk", "sum"), pf_drawn=("pf_drawn", "sum"), dunks=("dunks", "sum"))
            .reset_index())
    fb = pbp[((pbp.qualifier_1 == "contropiede") | (pbp.qualifier_2 == "contropiede")) & pbp.event.isin(FGA_EVENTS + ["Assist"])]
    t = (t.merge(fb.groupby("player_id").size().rename("fastbreak_inv"), on="player_id", how="left")
          .merge(fb[fb.event != "Assist"].groupby("player_id").size().rename("fastbreak_shots"), on="player_id", how="left")
          .merge(pbp[pbp.qualifier_1.isin(["Da penetrazione", "Tiro in corsa"])].groupby("player_id").size().rename("drive_finishes"), on="player_id", how="left")
          .merge(early_share(pbp, "player_id"), on="player_id", how="left"))
    t[["fastbreak_inv", "fastbreak_shots", "drive_finishes"]] = t[["fastbreak_inv", "fastbreak_shots", "drive_finishes"]].fillna(0)
    for c in ["oreb", "stl", "blk", "pf_drawn", "dunks", "fastbreak_inv", "fastbreak_shots", "drive_finishes"]:
        t[c + "_p40"] = t[c] / t.minutes * 40
    return t


def add_indices(t, ref):
    """z-score each component against `ref` (league players), average per index, shrink by minutes, rank."""
    comp = list(dict.fromkeys(RIM + PACE))
    z = ((t[comp] - ref[comp].mean()) / ref[comp].std(ddof=0)).clip(-3, 3)
    shrink = t.minutes / (t.minutes + K_MIN)
    t = t.copy()
    t["rim_activity"] = z[RIM].mean(axis=1, skipna=True) * shrink
    t["high_pace"] = z[PACE].mean(axis=1, skipna=True) * shrink
    return t


def percentiles(t, ref):
    """Percentile of each index within the reference table (ref = the LBA players)."""
    t = t.copy()
    for c in ["rim_activity", "high_pace"]:
        t[c + "_pct"] = t[c].apply(lambda v: (ref[c] <= v).mean()).round(2)   # = rank(pct=True) on the reference
    return t


def eurocup_table(team, synergy_dir, lba_ref):
    """EuroCup opponent: box components from the EuroCup box scores and play-by-play (z-scored on EuroCup players),
    drives and transition shots from the Synergy pull (z-scored on the LBA distribution)."""
    from matchup_report import parse_eurocup
    box, _ = parse_eurocup(ROOT / "data" / "eurocup_2026_raw.txt")
    box = box[box.row_type == "player"]
    t = (box.groupby(["team", "player_surname"])
            .agg(games=("game_id", "nunique"), minutes=("sec", lambda v: v.sum() / 60), oreb=("oreb", "sum"),
                 blk=("blk", "sum"), stl=("stl", "sum"), pf_drawn=("pf_drawn", "sum")).reset_index())
    for c in ["oreb", "blk", "stl", "pf_drawn"]:
        t[c + "_p40"] = t[c] / t.minutes * 40
    pbp = pd.read_csv(ROOT / "data" / "eurocup" / "pbp.csv")
    pbp["player_surname"] = pbp.player_surname.str.upper()
    t = t.merge(early_share(pbp, ["team", "player_surname"]).reset_index(), on=["team", "player_surname"], how="left")
    syn = pd.read_csv(Path(synergy_dir) / "shots.csv")
    syn["player_surname"] = syn.player.str.upper()
    # some pulls carry full names ("Breein Tyree", "Naz Mitrou-Long"): map them to the box-score surname of the team
    team_surnames = sorted(t.loc[t.team == team, "player_surname"].unique(), key=len, reverse=True)
    def to_surname(name):
        flat = name.replace("-", " ")
        return next((sn for sn in team_surnames if flat == sn or flat.endswith(" " + sn)), name)
    syn["player_surname"] = syn.player_surname.map(to_surname)
    drives = syn[(syn.shot_type == "To basket") & ~syn.play_type.isin(["Cut", "Offensive Rebounds (Put Backs)", "P&R Roll Man", "Off Screen"])]
    t = (t.merge(drives.groupby("player_surname").size().rename("drive_finishes"), on="player_surname", how="left")
          .merge(syn[syn.play_type == "Transition"].groupby("player_surname").size().rename("fastbreak_shots"), on="player_surname", how="left"))
    opp = t[(t.team == team) & (t.minutes > 0)].copy()
    opp[["drive_finishes", "fastbreak_shots"]] = opp[["drive_finishes", "fastbreak_shots"]].fillna(0)
    opp["drive_finishes_p40"] = opp.drive_finishes / opp.minutes * 40
    opp["fastbreak_shots_p40"] = opp.fastbreak_shots / opp.minutes * 40
    ec_ref = t[t.minutes >= MIN_REF]
    z = lambda col, ref: ((opp[col] - ref[col].mean()) / ref[col].std(ddof=0)).clip(-3, 3)
    zb = pd.DataFrame({c: z(c, ec_ref) for c in ["oreb_p40", "blk_p40", "pf_drawn_p40", "stl_p40", "early_fga_share"]})
    zb["drive_finishes_p40"] = z("drive_finishes_p40", lba_ref)
    zb["fastbreak_shots_p40"] = z("fastbreak_shots_p40", lba_ref)      # LBA shots-only rate as the scale
    shrink = opp.minutes / (opp.minutes + K_MIN)
    opp["rim_activity"] = zb[["oreb_p40", "blk_p40", "pf_drawn_p40"]].mean(axis=1) * shrink
    opp["high_pace"] = zb[["drive_finishes_p40", "fastbreak_shots_p40", "pf_drawn_p40", "stl_p40", "early_fga_share"]].mean(axis=1) * shrink
    return opp


def energy_figure(team, pl, slug, n_games, source, note="", out=None, filename=None):
    pl = pl.sort_values("minutes", ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(pl) + 2.2))
    fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
    y = np.arange(len(pl))[::-1]
    for (col, name, c), o in zip([("rim_activity_pct", "Rim activity", MISS), ("high_pace_pct", "High pace", MADE)], (0.15, -0.15)):
        ax.hlines(y + o, 0, pl[col], color=c, lw=1.2, alpha=0.5, zorder=2)
        ax.scatter(pl[col], y + o, color=c, s=40, label=name, zorder=3)
        for yi, v in zip(y + o, pl[col]):
            ax.text(v + 0.02, yi, f"{v:.2f}", va="center", fontsize=7, color="#374151")
    ax.axvline(0.5, color=LEAGUE, lw=1, ls="--")
    ax.set_xlim(0, 1.12); ax.set_yticks(y); ax.set_ylim(-0.6, len(pl) - 0.4)
    ax.set_yticklabels([f"{s.title()} ({int(m)}')" for s, m in zip(pl.player_surname, pl.minutes)], fontsize=9)
    for yi in y[:-1]:
        ax.axhline(yi - 0.5, color="#d1d5db", lw=0.6, zorder=0)
    ax.set_xlabel("league percentile\n(shrunk by minutes; 0.5 = league median)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8, frameon=False)
    ax.grid(axis="x", color="#e5e7eb", lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    fig.suptitle(f"{team} — energy indices, {n_games} games (data only)", fontsize=11, x=0.01, ha="left", y=0.985)
    fig.text(0.01, 0.945, "Rim activity: offensive rebounds, blocks, dunks and fouls drawn per 40 minutes.\n"
             "High pace: drive finishes, fast-break shots/assists, fouls drawn and steals per 40 minutes, and share of shots within 8 s of possession start.",
             fontsize=7.5, color="#6b7280", va="top")
    if note:
        fig.text(0.01, 0.895, note, fontsize=7.5, color="#6b7280", va="top")
    fig.text(0.99, 0.01, f"{AUTHOR} · {datetime.date.today().isoformat()} · source: {source}", ha="right", fontsize=7, color="#6b7280")
    fig.tight_layout(rect=(0, 0.03, 1, 0.88 if note else 0.9))
    folder = Path(out) if out else OUT
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (filename or f"energy_indices_{slug}.png")
    save_fig(fig, path); plt.close(fig)
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("teams", nargs="*", help="LBA team names as in data/box_scores.csv (BC Roma is always added)")
    ap.add_argument("--through", help="use only LBA games played up to this date (YYYY-MM-DD)")
    ap.add_argument("--eurocup", help="EuroCup team name as in data/eurocup_2026_raw.txt (needs --synergy)")
    ap.add_argument("--synergy", help="Synergy pull folder with a shots.csv for the EuroCup team")
    ap.add_argument("--out", help="folder for the EuroCup opponent figure (default reports/exploratory), e.g. the matchup folder of the game")
    ap.add_argument("--name", help="file name of the EuroCup opponent figure (default energy_indices_<team>.png), e.g. 15_energy_indices.png")
    a = ap.parse_args()

    lba = lba_table(a.through)
    lba = lba[lba.minutes > 0]                                  # DNP rows have no rates
    ref = lba[lba.minutes >= MIN_REF]
    lba = percentiles(add_indices(lba, ref), add_indices(lba, ref))
    n_games = pd.read_csv(ROOT / "data" / "box_scores.csv").game_id.nunique() if not a.through else lba.games.max()
    OUT.mkdir(parents=True, exist_ok=True)
    lba.sort_values("high_pace", ascending=False).to_csv(OUT / "energy_index_lba.csv", index=False)
    for team in dict.fromkeys(list(a.teams) + ["BC Roma"]):
        pl = lba[lba.team == team]
        if pl.empty:
            print(f"no LBA players for {team!r} — team names: {sorted(lba.team.unique())}"); continue
        energy_figure(team, pl, team.split()[-1].lower(), pl.games.max(), "legabasket.it play-by-play")

    if a.eurocup:
        if not a.synergy:
            sys.exit("--eurocup needs --synergy <folder with shots.csv>")
        lba_ref = add_indices(lba, ref)
        lba_ref["fastbreak_shots_p40"] = lba_ref.fastbreak_shots / lba_ref.minutes * 40
        opp = eurocup_table(a.eurocup, a.synergy, lba_ref[lba_ref.minutes >= MIN_REF])
        opp = percentiles(opp, lba_ref)
        opp.to_csv(OUT / f"energy_index_{a.eurocup.split()[0].lower()}_eurocup.csv", index=False)
        energy_figure(f"{a.eurocup} (EuroCup)", opp, a.eurocup.split()[0].lower(), opp.games.max(),
                      "EuroCup box scores & play-by-play, Synergy (drives, transition)",
                      note="EuroCup: no dunks available; drives = Synergy 'to basket' shots off P&R, isolation, spot-up, transition; fast break = Synergy transition shots "
                           "(LBA counts shots + assists).\nBox components scaled on EuroCup players, drives/transition on LBA players; percentiles read off the LBA distribution.",
                      out=a.out, filename=a.name)


if __name__ == "__main__":
    main()

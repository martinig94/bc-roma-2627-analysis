"""Add a "Leaderboard" tab to a Synergy defensive-ratings workbook (.xls, one tab per play type).

    python notebooks/synergy_leaderboard.py IN.xls [OUT.xls]

The tab is made of formulas that read the play-type tabs, so after each EuroCup / LBA game it is enough to
paste the new Synergy export over those tabs (same layout: header on row 2, one team per row, sorted by PPP):
the leaderboard recalculates by itself. Running this script again on a refreshed workbook rebuilds the tab.
Rank 1 = best defence (lowest PPP allowed). Room for MAX_TEAMS teams (EuroCup 32, LBA 16).
"""
import sys
import xlrd
import xlwt
from xlutils.copy import copy

MAX_TEAMS = 40
FIRST, LAST = 3, 60                      # data rows (1-based) of the play-type tabs searched by the formulas
BASE = "PPP - Tabella 1"
TYPES = [("TRANSITION", "Transition"), ("ISO", "Isolation"), ("POST-UP", "Post-up"),
         ("PnR BALL HANDLER", "P&R ball handler"), ("PnR ROLL MAN", "P&R roll man"),
         ("SPOT UP", "Spot up"), ("OFF SCREEN", "Off screen"), ("HAND OFF", "Hand off"),
         ("CUT", "Cut"), ("OFF REB", "Off reb (putbacks)")]


def col(n):  # 0-based index -> Excel letters
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def build(src, dst):
    rb = xlrd.open_workbook(src, formatting_info=True)
    wb = copy(rb)
    if "Leaderboard" in rb.sheet_names():
        sys.exit("Leaderboard tab already exists: refresh the play-type tabs, the formulas update by themselves")
    ws = wb.add_sheet("Leaderboard", 0)
    ws.set_panes_frozen(True)
    ws.set_horz_split_pos(4)
    ws.set_vert_split_pos(2)

    title = xlwt.easyxf("font: bold on, height 280")
    note = xlwt.easyxf("font: italic on, colour gray50")
    grp = xlwt.easyxf("font: bold on, colour white; pattern: pattern solid, fore_colour dark_blue; align: horiz center")
    hdr = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25; align: horiz center; borders: bottom thin")
    txt = xlwt.easyxf("font: bold on")
    num0 = xlwt.easyxf("align: horiz center")
    num1 = xlwt.easyxf("align: horiz center", num_format_str="0.0")
    ppp = xlwt.easyxf("align: horiz center", num_format_str="0.000")
    rk = xlwt.easyxf("align: horiz center; font: colour gray50")

    ws.write(0, 0, "Defensive leaderboard (Synergy): points per possession allowed, by play type", title)
    ws.write(1, 0, "Rank 1 = best defence (lowest PPP allowed). Formulas read the play-type tabs: paste the new "
                   "Synergy export over them after each game and this tab updates. Small samples: check Poss.", note)

    heads = ["Rank", "Team", "GP", "Poss", "PPP", "Rk"]
    for j, h in enumerate(heads):
        ws.write(3, j, h, hdr)
    ws.write_merge(2, 2, 0, 5, "OVERALL", grp)
    for i, (_, label) in enumerate(TYPES):
        c = 6 + 3 * i
        ws.write_merge(2, 2, c, c + 2, label.upper(), grp)
        for j, h in enumerate(["Poss", "PPP", "Rk"]):
            ws.write(3, c + j, h, hdr)
    ws.col(1).width = 256 * 38
    for c in range(2, 6 + 3 * len(TYPES)):
        ws.col(c).width = 256 * 8

    p = f"'{BASE}'!"
    rng = lambda tab, c: f"'{tab} - Tabella 1'!${c}${FIRST}:${c}${LAST}"
    for k in range(MAX_TEAMS):
        r = 4 + k                       # 0-based row on the leaderboard
        x = r + 1                       # Excel row
        src = FIRST + k                 # row of the team in the PPP tab
        team = f"B{x}"
        ws.write(r, 0, xlwt.Formula(f'IF(LEN({p}B{src})=0,"",{p}A{src})'), num0)
        ws.write(r, 1, xlwt.Formula(f'IF(LEN({p}B{src})=0,"",{p}B{src})'), txt)
        for c, srccol, st in ((2, "C", num0), (3, "D", num1), (4, "G", ppp)):
            ws.write(r, c, xlwt.Formula(f'IF({team}="","",{p}{srccol}{src})'), st)
        ws.write(r, 5, xlwt.Formula(f'IF({team}="","",RANK(E{x},E$5:E${4 + MAX_TEAMS},1))'), rk)
        for i, (tab, _) in enumerate(TYPES):
            c = 6 + 3 * i
            m = f"MATCH({team},{rng(tab, 'B')},0)"
            for off, srccol, st in ((0, "D", num1), (1, "G", ppp)):
                ws.write(r, c + off, xlwt.Formula(
                    f'IF({team}="","",IF(ISNA({m}),"",INDEX({rng(tab, srccol)},{m})))'), st)
            pc = col(c + 1)
            ws.write(r, c + 2, xlwt.Formula(
                f'IF({pc}{x}="","",RANK({pc}{x},{pc}$5:{pc}${4 + MAX_TEAMS},1))'), rk)
    wb.save(dst)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    build(a[0], a[1] if len(a) > 1 else a[0])

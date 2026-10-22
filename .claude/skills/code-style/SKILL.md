---
name: code-style
description: Python style guide for this project (lba_data/, notebooks/, tests/). Use whenever writing, editing or reviewing Python code - Google-style docstrings, type hints, general code conventions, and no hard-coded values.
---

# Code style

Applies to every Python file in `lba_data/`, `notebooks/` and `tests/`. When editing existing code, match the surrounding file, and bring the lines you touch up to this guide rather than reformatting untouched code.

## 1. Docstrings (Google style)

- Every module, public function, class and public method gets a docstring. Private helpers (`_name`) need one only if the logic isn't obvious.
- First line: one-sentence summary in the imperative mood ("Return...", "Build...", "Save..."), ending with a period.
- Add `Args:`, `Returns:`, `Raises:` (and `Yields:` for generators) sections when the summary alone isn't enough. Don't repeat types in the sections; the type hints carry them.
- Say what units/conventions mean when it matters (for example, court coordinates are 0-100 percent of the court, not metres).

```python
def clutch_minutes(box: pd.DataFrame, team: str, min_games: int = 3) -> pd.Series:
    """Return total clutch minutes per player for one team.

    Args:
        box: Player-level box score rows (``row_type == "player"``).
        team: Team name as it appears in ``box["team"]``.
        min_games: Players with fewer games than this are dropped.

    Returns:
        Minutes per player, indexed by player name, sorted descending.

    Raises:
        KeyError: If ``box`` lacks the ``minutes`` column.
    """
```

- Module docstring: what the module does and, for scripts, how it is run and what it writes.
- Use comments for *why*, not *what*. Keep them short.

## 2. Type hints

- Annotate all function parameters and return values (`-> None` included). Annotate module-level constants when the type isn't obvious.
- Start every module with `from __future__ import annotations`.
- Use built-in generics and union syntax: `list[str]`, `dict[str, int]`, `str | None`. Don't use `typing.List/Dict/Optional`.
- Import `Any`, `Callable`, `Iterable`, `Sequence`, `Mapping` (from `collections.abc`) only when needed. Prefer the most general input type (`Iterable`, `Mapping`) and a concrete return type.
- Name the pandas/matplotlib types: `pd.DataFrame`, `pd.Series`, `Figure`, `Axes`, `Path`. Avoid bare `dict` or `list` with no parameters.
- Use `TypedDict`, `NamedTuple` or `@dataclass` for structured records instead of loosely-keyed dicts passed around.
- Paths are `pathlib.Path`, never raw strings.

## 3. General code

- Python 3.10+, PEP 8, 4-space indent, double quotes, f-strings, line length around 100 (the existing code goes slightly past 88; don't hard-wrap to 88).
- Small functions with one job. Separate data loading, computation and plotting; computation functions return DataFrames/values and never touch the filesystem or draw.
- Prefer vectorised pandas over row loops; no `iterrows` for anything computed on whole columns. Don't mutate inputs (`df = df.copy()` before assigning columns).
- Use `pathlib` for filesystem work and `encoding="utf-8"` on text I/O.
- Imports: stdlib, third party, local, separated by blank lines; no wildcard imports; no unused imports.
- Fail loudly and specifically: raise `ValueError`/`KeyError` with a message naming the bad input. No bare `except:` and no silently swallowed errors.
- Use `logging` or the script's existing reporting for diagnostics, not stray `print` calls, except in CLI entry points.
- Scripts expose `main()` guarded by `if __name__ == "__main__":`; use `argparse` for options.
- Names: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants, descriptive (no one-letter names outside comprehensions and maths-like code). Booleans read as predicates (`is_finished`, `has_pbp`).
- Remove dead code and commented-out blocks instead of leaving them in.
- Reuse existing helpers (`notebooks/lba_style.py`, `lba_data/transform.py`) before writing new ones.
- Add or update a test in `tests/` for new logic that doesn't need the network; run `python -m pytest -q` before committing.

## 4. Avoid hard-coding

Nothing that can change between teams, seasons, games or machines should be a literal buried in a function body.

- **Team, season, author, league, paths, EuroCup file:** read from `weekly/config.json` via `notebooks/weekly_config.load()`, or take them as function arguments / CLI options. Never write `"BC Roma"` or `"2026/27"` inline in logic; add a parameter whose *default* comes from config.
- **Identifiers** (team ids, championship id, game ids, event-type strings such as `"2 punti segnato"`): module-level named constants at the top of the file, or look them up from the data (`teams.csv`, `games.csv`). Group related ones in an `Enum` or a frozen dataclass.
- **Thresholds and magic numbers** (clutch window, minimum minutes, sample-size cutoffs, retry counts, timeouts): named constants or function parameters with defaults, with a comment giving the unit and the reason.
- **Paths:** build from one `ROOT = Path(__file__).resolve().parent.parent` (or the config) with `/`. No absolute paths, no `"../data"` strings scattered around.
- **Styling:** colours, fonts, DPI and chart stamps come from `notebooks/lba_style.py` (`GOLD`, `TEXT`, `DPI`, `save_fig`, ...). Don't write hex codes in report scripts; add a new named constant to the style module if one is missing.
- **URLs and endpoints:** one `BASE` and per-endpoint paths in `lba_data/api.py`; everything else calls those functions.
- **Column names** used in more than a couple of places: constants or a single place that renames them.
- **Secrets and environment-specific values:** environment variables, never committed.
- Derive instead of repeating: loop over teams/rounds/columns found in the data rather than listing them by hand, and compute lengths/counts instead of typing them.

Acceptable literals: `0`, `1`, `-1`, empty containers, obvious unit conversions with a named factor, and format strings for display.

## Before finishing

1. Every new or edited function has type hints and a Google-style docstring.
2. No team names, seasons, paths, colours, ids or thresholds are inlined in logic.
3. Tests pass: `python -m pytest -q`.

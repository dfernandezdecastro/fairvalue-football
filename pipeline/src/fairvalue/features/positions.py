"""Position groups used for peer comparisons and model features.

Transfermarkt's position is a CURRENT snapshot label. Understat lists every
line a player was used in during a season (e.g. "D M S"; S = substitute), which
is historical but has no primary position. We therefore start from the
Transfermarkt label and only override it when that season's Understat record
shows the player never played in that line (e.g. labelled a forward today, but
used only in defence in 2016/17).
"""

from __future__ import annotations

import pandas as pd

GROUP_BY_SUB_POSITION = {
    "Goalkeeper": "GK",
    "Centre-Back": "CB",
    "Left-Back": "FB",
    "Right-Back": "FB",
    "Defensive Midfield": "CM",
    "Central Midfield": "CM",
    "Attacking Midfield": "AM_W",
    "Left Winger": "AM_W",
    "Right Winger": "AM_W",
    "Left Midfield": "AM_W",
    "Right Midfield": "AM_W",
    "Second Striker": "AM_W",
    "Centre-Forward": "ST",
}
GROUP_LABELS = {
    "GK": "Goalkeepers",
    "CB": "Centre-backs",
    "FB": "Full-backs",
    "CM": "Central & defensive midfielders",
    "AM_W": "Attacking midfielders & wingers",
    "ST": "Strikers",
}
# Understat line letters compatible with each group
_LINES = {"GK": {"GK"}, "CB": {"D"}, "FB": {"D", "M"}, "CM": {"M", "D"}, "AM_W": {"M", "F"}, "ST": {"F"}}
# Fallback group when Understat shows exactly one, incompatible line
_OVERRIDE = {"GK": "GK", "D": "CB", "M": "CM", "F": "ST"}


def tm_group(sub_position: pd.Series) -> pd.Series:
    return sub_position.map(GROUP_BY_SUB_POSITION).fillna("UNK")


def understat_lines(position: str | None) -> set[str]:
    if not isinstance(position, str):
        return set()
    return {p for p in position.split() if p != "S"}


def resolve_group(tm: str, us_position: str | None) -> tuple[str, str]:
    """(group, source) for one player-season."""
    lines = understat_lines(us_position)
    if not lines:
        return tm, "tm_current"
    if tm != "UNK" and _LINES[tm] & lines:
        return tm, "tm_current_confirmed"
    if len(lines) == 1:
        return _OVERRIDE[next(iter(lines))], "understat_season"
    return tm, "tm_current"

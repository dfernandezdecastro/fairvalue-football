import json

import pytest

from fairvalue.ingest.understat_archive import (
    decode_js_string,
    parse_players,
    read_cache,
    snapshot_status,
)

ROW = {
    "id": "1", "player_name": "Kylian Mbappé", "games": "30", "time": "2500", "goals": "20",
    "xG": "18.5", "assists": "5", "xA": "6.1", "shots": "100", "key_passes": "40",
    "yellow_cards": "2", "red_cards": "0", "position": "F S", "team_title": "Paris Saint Germain",
    "npg": "17", "npxG": "15.2", "xGChain": "22.0", "xGBuildup": "4.1",
}  # fmt: skip


def encode_like_understat(obj) -> str:
    """Escape every non-alphanumeric byte as \\xNN, as Understat does."""
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return "".join(chr(b) if b < 128 and chr(b).isalnum() else f"\\x{b:02X}" for b in raw)


def page(rows) -> str:
    return f"<script>var playersData\t= JSON.parse('{encode_like_understat(rows)}');</script>"


def test_decode_keeps_accents():
    assert decode_js_string(encode_like_understat("Mbappé")) == '"Mbappé"'


def test_parse_players_roundtrip():
    rows = parse_players(page([ROW]))
    assert rows[0]["player_name"] == "Kylian Mbappé"


def test_truncated_capture_returns_none():
    html = page([ROW, ROW])
    assert parse_players(html[: len(html) // 2]) is None
    assert parse_players("<html>We will come back soon</html>") is None


@pytest.mark.parametrize(
    "season, ts, status",
    [(2019, "20200801000000", "final"), (2024, "20250525232349", "near_final")],
)
def test_snapshot_status(season, ts, status):
    assert snapshot_status(season, ts) == status


def test_read_cache_builds_rows_and_coverage(tmp_path):
    p = tmp_path / "EPL_2019_20200801000000.html"
    p.write_text(page([ROW]), encoding="utf-8")
    rows, cov = read_cache([p])
    assert len(rows) == 1 and rows.loc[0, "xG"] == pytest.approx(18.5)
    epl19 = cov[(cov.league == "EPL") & (cov.season == 2019)].iloc[0]
    assert epl19.status == "final" and epl19.players == 1
    assert (cov.status == "missing").sum() == len(cov) - 1  # every other league-season reported missing

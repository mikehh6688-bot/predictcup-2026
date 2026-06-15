"""第三方賽事數據整合 — API-Football，匯入世界盃賽程並自動同步賽果。

策略：以 league + season 一次抓取整個世界盃賽程（含未開賽/進行中/已完賽），
upsert 進 Match（以 fixture id 對應 external_ref）。已完賽者觸發結算。
無 SPORTS_API_KEY 時所有方法安全回傳空集合（不阻斷排程 / 測試）。
"""
from datetime import datetime

from flask import current_app

from ..extensions import db
from ..models import Match
from ..constants import MatchStatus, MatchStage, BetChoice, STAGE_MULTIPLIER
from . import settlement

# API-Football fixture.status.short 分類
_FINISHED = {"FT", "AET", "PEN"}
_LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}

# league.round 關鍵字 → 賽事階段（"32" 須在 "16" 之前比對）
_ROUND_TO_STAGE = [
    ("group", MatchStage.GROUP),
    ("32", MatchStage.R32),
    ("16", MatchStage.R16),
    ("quarter", MatchStage.QF),
    ("semi", MatchStage.SF),
    ("3rd place", MatchStage.FINAL),
    ("final", MatchStage.FINAL),
]

# 常見國家隊名 → ISO3（供前端國旗顯示；未命中則留空走預設旗）
_NAME_TO_CODE = {
    "Brazil": "BRA", "Argentina": "ARG", "France": "FRA", "England": "ENG",
    "Spain": "ESP", "Germany": "GER", "Portugal": "POR", "Netherlands": "NED",
    "Japan": "JPN", "USA": "USA", "United States": "USA", "Mexico": "MEX",
    "Canada": "CAN", "Italy": "ITA", "Belgium": "BEL", "Croatia": "CRO",
    "Uruguay": "URU", "Morocco": "MAR", "South Korea": "KOR",
}


def _stage_for(round_str):
    s = (round_str or "").lower()
    for keyword, stage in _ROUND_TO_STAGE:
        if keyword in s:
            return stage
    return MatchStage.GROUP


def _status_for(short):
    if short in _FINISHED:
        return MatchStatus.FINISHED
    if short in _LIVE:
        return MatchStatus.LIVE
    return MatchStatus.SCHEDULED


def fetch_world_cup_fixtures():
    """抓取整個世界盃賽程（依 league + season）。回傳 API-Football 原始 list。"""
    if not current_app.config.get("SPORTS_API_KEY"):
        return []
    import requests

    try:
        resp = requests.get(
            f"{current_app.config['SPORTS_API_BASE']}/fixtures",
            params={
                "league": current_app.config["SPORTS_LEAGUE_ID"],
                "season": current_app.config["SPORTS_SEASON"],
            },
            headers={"x-apisports-key": current_app.config["SPORTS_API_KEY"]},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("response", [])
    except requests.RequestException:
        return []


def _upsert(item):
    """將單筆 fixture upsert 進 Match；回傳 (match, is_new, became_finished)。"""
    fixture = item.get("fixture", {})
    teams, goals, league = item.get("teams", {}), item.get("goals", {}), item.get("league", {})
    ref = str(fixture.get("id"))

    match = Match.query.filter_by(external_ref=ref).first()
    is_new = match is None
    if is_new:
        match = Match(
            home_team=teams.get("home", {}).get("name", "?"),
            away_team=teams.get("away", {}).get("name", "?"),
            kickoff_time=datetime.utcnow(),
            stage=_stage_for(league.get("round")),
            external_ref=ref,
        )
        db.session.add(match)

    # 共同欄位更新
    match.home_team = teams.get("home", {}).get("name", match.home_team)
    match.away_team = teams.get("away", {}).get("name", match.away_team)
    match.home_team_code = _NAME_TO_CODE.get(match.home_team)
    match.away_team_code = _NAME_TO_CODE.get(match.away_team)
    match.stage = _stage_for(league.get("round"))
    match.multiplier = STAGE_MULTIPLIER.get(match.stage, 1)
    iso = fixture.get("date")
    if iso:
        match.kickoff_time = datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)

    short = fixture.get("status", {}).get("short")
    new_status = _status_for(short)
    became_finished = (
        new_status == MatchStatus.FINISHED and match.status != MatchStatus.FINISHED
    )

    if new_status == MatchStatus.FINISHED:
        match.home_score = goals.get("home")
        match.away_score = goals.get("away")
        if match.stage != MatchStage.GROUP:
            match.advancing_team = (
                BetChoice.HOME if teams.get("home", {}).get("winner") else BetChoice.AWAY
            )
        # 狀態先不設 FINISHED，交由 settle_match 設定（避免重複結算）
        if not became_finished:
            match.status = MatchStatus.FINISHED
    else:
        match.status = new_status

    return match, is_new, became_finished


def import_fixtures(replace_demo=False):
    """匯入/更新世界盃賽程；已完賽者觸發結算。回傳統計。

    replace_demo=True 時先刪除手動建立的 demo 賽事（external_ref 為空）。
    """
    fixtures = fetch_world_cup_fixtures()
    if not fixtures:
        return {"imported": 0, "updated": 0, "settled": 0, "note": "no fixtures (check SPORTS_API_KEY)"}

    if replace_demo:
        Match.query.filter(Match.external_ref.is_(None)).delete()

    imported = updated = settled = 0
    for item in fixtures:
        match, is_new, became_finished = _upsert(item)
        imported += 1 if is_new else 0
        updated += 0 if is_new else 1
        db.session.flush()
        if became_finished and match.home_score is not None and match.away_score is not None:
            try:
                settlement.settle_match(match)  # 內含 commit
                settled += 1
                continue
            except settlement.SettlementError:
                db.session.rollback()
    db.session.commit()
    return {"imported": imported, "updated": updated, "settled": settled}


def sync_results(*_args, **_kwargs):
    """排程入口：等同匯入最新賽程並結算已完賽。"""
    return import_fixtures(replace_demo=False)

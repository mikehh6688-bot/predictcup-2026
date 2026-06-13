"""第三方賽事數據整合 — 以 API-Football 為例，自動同步賽果。

無 SPORTS_API_KEY 時所有方法安全地回傳空集合（不阻斷排程）。
比對策略：優先以 Match.external_ref 對應 fixture id，其次以隊名近似比對。
"""
from datetime import datetime

from flask import current_app

from ..extensions import db
from ..models import Match
from ..constants import MatchStatus, MatchStage, BetChoice
from . import settlement

# API-Football fixture.status.short 代表「已完賽」的狀態碼
_FINISHED_CODES = {"FT", "AET", "PEN"}


def _headers():
    return {"x-apisports-key": current_app.config["SPORTS_API_KEY"]}


def fetch_results_for_date(date_str):
    """抓取某日（YYYY-MM-DD）已完賽的賽果，正規化後回傳 list。"""
    if not current_app.config.get("SPORTS_API_KEY"):
        return []
    import requests

    base = current_app.config["SPORTS_API_BASE"]
    try:
        resp = requests.get(
            f"{base}/fixtures", params={"date": date_str},
            headers=_headers(), timeout=8,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException:
        return []

    results = []
    for item in payload.get("response", []):
        fixture = item.get("fixture", {})
        if fixture.get("status", {}).get("short") not in _FINISHED_CODES:
            continue
        teams, goals = item.get("teams", {}), item.get("goals", {})
        results.append({
            "external_ref": str(fixture.get("id")),
            "home_team": teams.get("home", {}).get("name"),
            "away_team": teams.get("away", {}).get("name"),
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
            "winner_home": teams.get("home", {}).get("winner"),
        })
    return results


def _match_for(result):
    """以 external_ref → 隊名 的順序找出本地對應賽事。"""
    m = Match.query.filter_by(external_ref=result["external_ref"]).first()
    if m:
        return m
    return Match.query.filter_by(
        home_team=result["home_team"], away_team=result["away_team"]
    ).first()


def sync_results(date_str=None):
    """抓取賽果寫回本地賽事並觸發結算。回傳統計 dict。"""
    date_str = date_str or datetime.utcnow().strftime("%Y-%m-%d")
    synced = settled = 0
    for r in fetch_results_for_date(date_str):
        if r["home_score"] is None or r["away_score"] is None:
            continue
        match = _match_for(r)
        if match is None or match.status == MatchStatus.FINISHED:
            continue

        match.home_score = int(r["home_score"])
        match.away_score = int(r["away_score"])
        if match.stage != MatchStage.GROUP:
            # 淘汰賽：依 API winner 旗標決定晉級隊（PK 也算）
            match.advancing_team = (
                BetChoice.HOME if r.get("winner_home") else BetChoice.AWAY
            )
        synced += 1
        try:
            settlement.settle_match(match)
            settled += 1
        except settlement.SettlementError:
            db.session.rollback()

    return {"synced": synced, "settled": settled, "date": date_str}

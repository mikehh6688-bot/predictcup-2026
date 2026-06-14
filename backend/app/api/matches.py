"""賽事大廳 — 列表、詳情、戰情儀表板、賽果結算、AI 寫入。"""
from datetime import datetime

from flask import Blueprint, request

from ..extensions import db
from ..models import Match, Bet
from ..constants import MatchStatus, MatchStage, BetChoice, STAGE_MULTIPLIER
from ..services import settlement, ai_predictor, sports_api
from ._helpers import error, ok, parse_enum

STAGE_LABELS = {
    MatchStage.GROUP: "小組賽",
    MatchStage.R16: "16 強",
    MatchStage.QF: "8 強",
    MatchStage.SF: "4 強",
    MatchStage.FINAL: "決賽",
}

bp = Blueprint("matches", __name__)


@bp.get("")
def list_matches():
    """賽事列表（三分頁籤）。Query: ?status=&stage=&date=YYYY-MM-DD"""
    q = Match.query
    try:
        status = parse_enum(MatchStatus, request.args.get("status"), "status")
        stage = parse_enum(MatchStage, request.args.get("stage"), "stage")
    except ValueError as e:
        return error("INVALID_INPUT", str(e))
    if status:
        q = q.filter_by(status=status)
    if stage:
        q = q.filter_by(stage=stage)

    date_str = request.args.get("date")
    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return error("INVALID_INPUT", "date 格式須為 YYYY-MM-DD")
        q = q.filter(db.func.date(Match.kickoff_time) == day)

    matches = q.order_by(Match.kickoff_time.asc()).all()
    return ok({"matches": [m.to_dict() for m in matches]})


@bp.get("/featured")
def featured_matches():
    """首頁焦點賽事（最近 1~2 場即將開打）。"""
    matches = (
        Match.query.filter(
            Match.status == MatchStatus.SCHEDULED,
            Match.kickoff_time >= datetime.utcnow(),
        )
        .order_by(Match.kickoff_time.asc())
        .limit(2)
        .all()
    )
    return ok({"matches": [m.to_dict() for m in matches]})


def _bet_distribution(match_id):
    """系統內用戶下注比例（圓餅圖用）。"""
    rows = (
        db.session.query(Bet.predicted_result, db.func.count(Bet.id))
        .filter_by(match_id=match_id)
        .group_by(Bet.predicted_result)
        .all()
    )
    counts = {c.value: 0 for c in BetChoice}
    for choice, n in rows:
        counts[choice.value] = n
    total = sum(counts.values()) or 1
    return {k: round(v / total, 3) for k, v in counts.items()}, sum(counts.values())


@bp.get("/<int:match_id>")
def get_match(match_id):
    """單場賽事詳情（含 AI 勝率、網民風向、用戶下注比例）。"""
    match = db.session.get(Match, match_id)
    if match is None:
        return error("NOT_FOUND", "賽事不存在", 404)
    dist, total = _bet_distribution(match_id)
    data = match.to_dict()
    data["user_bet_distribution"] = dist
    data["total_bets"] = total
    return ok(data)


@bp.post("")
def create_match():
    """建立賽事（MVP 手動建置）。multiplier 由 stage 自動推導。"""
    data = request.get_json(silent=True) or {}
    required = ["home_team", "away_team", "kickoff_time", "stage"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error("INVALID_INPUT", f"缺少必填欄位：{', '.join(missing)}")

    try:
        stage = parse_enum(MatchStage, data["stage"], "stage")
        kickoff = datetime.fromisoformat(data["kickoff_time"])
    except ValueError as e:
        return error("INVALID_INPUT", str(e))

    match = Match(
        home_team=data["home_team"],
        away_team=data["away_team"],
        home_team_code=data.get("home_team_code"),
        away_team_code=data.get("away_team_code"),
        kickoff_time=kickoff,
        stage=stage,  # __init__ 會自動套用 STAGE_MULTIPLIER
    )
    db.session.add(match)
    db.session.commit()
    return ok(match.to_dict(), 201)


@bp.patch("/<int:match_id>/result")
def update_result(match_id):
    """更新賽果並觸發結算（狀態轉 finished）。

    Request JSON: { "home_score", "away_score", "advancing_team": "home"|"away"|null }
    """
    match = db.session.get(Match, match_id)
    if match is None:
        return error("NOT_FOUND", "賽事不存在", 404)
    # 允許對已結算賽事再次更新（結算為可重入，會自動重算）

    data = request.get_json(silent=True) or {}
    if "home_score" not in data or "away_score" not in data:
        return error("INVALID_INPUT", "home_score 與 away_score 為必填")

    try:
        advancing = parse_enum(BetChoice, data.get("advancing_team"), "advancing_team")
    except ValueError as e:
        return error("INVALID_INPUT", str(e))
    if advancing == BetChoice.DRAW:
        return error("INVALID_INPUT", "advancing_team 僅能為 home / away")

    match.home_score = int(data["home_score"])
    match.away_score = int(data["away_score"])
    match.advancing_team = advancing

    try:
        result = settlement.settle_match(match)
    except settlement.SettlementError as e:
        db.session.rollback()
        return error("SETTLEMENT_ERROR", str(e))

    return ok({"match": match.to_dict(), "settlement": result})


@bp.post("/auto-sync")
def auto_sync():
    """自動上網收集最新賽果並重新結算。

    來源：有 SPORTS_API_KEY 走 API-Football，否則爬維基百科（免金鑰）。
    可重複執行（結算為可重入）。
    """
    from ..services import sync_service
    return ok(sync_service.auto_sync())


@bp.post("/import-fixtures")
def import_fixtures():
    """從 API-Football 匯入/更新世界盃賽程，並結算已完賽。

    Query: ?replace_demo=true 先清除手動建立的 demo 賽事
    需設定 SPORTS_API_KEY（未設則回傳 note 提示）。
    """
    replace = request.args.get("replace_demo") == "true"
    return ok(sports_api.import_fixtures(replace_demo=replace))


@bp.post("/<int:match_id>/ai-generate")
def ai_generate(match_id):
    """觸發 Claude 產生 AI 勝率預測 + 網民風向並寫入賽事。"""
    match = db.session.get(Match, match_id)
    if match is None:
        return error("NOT_FOUND", "賽事不存在", 404)
    pred = ai_predictor.generate_for_match(match, STAGE_LABELS.get(match.stage, "賽事"))
    return ok({"match": match.to_dict(), "prediction": pred})


@bp.patch("/<int:match_id>/ai-prediction")
def update_ai_prediction(match_id):
    """手動寫入 AI 勝率與網民風向（外部來源覆寫用）。"""
    match = db.session.get(Match, match_id)
    if match is None:
        return error("NOT_FOUND", "賽事不存在", 404)
    data = request.get_json(silent=True) or {}
    for field in [
        "ai_home_win_prob", "ai_draw_prob", "ai_away_win_prob", "ai_analysis",
        "public_home_pct", "public_draw_pct", "public_away_pct",
    ]:
        if field in data:
            setattr(match, field, data[field])
    db.session.commit()
    return ok(match.to_dict())

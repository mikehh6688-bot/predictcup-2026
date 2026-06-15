"""投注引擎 — 下注 / 改注 / 取消（道具互斥、下注扣除、取消退還）。"""
from flask import Blueprint, request

from ..extensions import db, limiter
from ..models import Bet, Match
from ..constants import BetChoice
from ..services import betting
from ._helpers import error, ok, parse_enum, login_required

bp = Blueprint("bets", __name__)


@bp.post("")
@login_required
@limiter.limit("30 per minute")
def place_bet(user):
    """下注（Betting Modal 送出）。"""
    data = request.get_json(silent=True) or {}
    match = db.session.get(Match, data.get("match_id"))
    if match is None:
        return error("NOT_FOUND", "賽事不存在", 404)
    try:
        predicted = parse_enum(BetChoice, data.get("predicted_result"), "predicted_result")
    except ValueError as e:
        return error("INVALID_INPUT", str(e))
    if predicted is None:
        return error("INVALID_INPUT", "predicted_result 為必填")

    try:
        bet = betting.place_bet(
            user=user,
            match=match,
            predicted_result=predicted,
            predicted_home_score=data.get("predicted_home_score"),
            predicted_away_score=data.get("predicted_away_score"),
            use_double_card=bool(data.get("use_double_card", False)),
            use_insurance_card=bool(data.get("use_insurance_card", False)),
        )
    except betting.BettingError as e:
        return error(e.code, e.message)
    return ok(bet.to_dict(), 201)


@bp.get("/<int:bet_id>")
def get_bet(bet_id):
    """單張注單詳情（含結算結果）。"""
    bet = db.session.get(Bet, bet_id)
    if bet is None:
        return error("NOT_FOUND", "注單不存在", 404)
    return ok(bet.to_dict())


@bp.patch("/<int:bet_id>")
@login_required
def update_bet(user, bet_id):
    """改注（鎖盤前）。"""
    bet = db.session.get(Bet, bet_id)
    if bet is None:
        return error("NOT_FOUND", "注單不存在", 404)
    if bet.user_id != user.id:
        return error("FORBIDDEN", "無權修改他人注單", 403)

    data = request.get_json(silent=True) or {}
    try:
        predicted = parse_enum(BetChoice, data.get("predicted_result"), "predicted_result")
    except ValueError as e:
        return error("INVALID_INPUT", str(e))

    try:
        bet = betting.update_bet(
            bet,
            predicted_result=predicted,
            predicted_home_score=data.get("predicted_home_score"),
            predicted_away_score=data.get("predicted_away_score"),
            use_double_card=data.get("use_double_card"),
            use_insurance_card=data.get("use_insurance_card"),
        )
    except betting.BettingError as e:
        return error(e.code, e.message)
    return ok(bet.to_dict())


@bp.delete("/<int:bet_id>")
@login_required
def cancel_bet(user, bet_id):
    """取消注單（鎖盤前，退還道具）。"""
    bet = db.session.get(Bet, bet_id)
    if bet is None:
        return error("NOT_FOUND", "注單不存在", 404)
    if bet.user_id != user.id:
        return error("FORBIDDEN", "無權取消他人注單", 403)
    try:
        betting.cancel_bet(bet)
    except betting.BettingError as e:
        return error(e.code, e.message)
    return "", 204

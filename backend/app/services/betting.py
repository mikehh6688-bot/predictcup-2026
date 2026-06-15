"""投注服務 — 下注 / 改注 / 取消，含驗證與道具扣除。

道具規則（依使用者決策）：
  * 翻倍卡與保險卡【互斥】，不可同時使用。
  * 道具於【下注當下扣除】，取消注單即【退還】。
  * 改注時依道具使用差異補扣 / 退還。
"""
from datetime import datetime, timedelta

from flask import current_app

from ..extensions import db
from ..constants import MatchStatus, MatchStage, BetChoice
from ..models import Bet, Match, User


def _lock_user(user):
    """鎖定使用者列（SELECT FOR UPDATE），序列化道具扣減避免併發重複扣。
    SQLite 不支援 FOR UPDATE，會自動忽略（單機測試無妨）。"""
    db.session.query(User).filter_by(id=user.id).with_for_update().first()


class BettingError(Exception):
    """下注驗證失敗（呼叫端轉 400）。"""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _lock_minutes():
    return current_app.config.get("BET_LOCK_MINUTES", 5)


def _validate_match_open(match):
    if match.status != MatchStatus.SCHEDULED:
        raise BettingError("MATCH_LOCKED", "賽事已鎖盤或結束，無法下注")
    lock_at = match.kickoff_time - timedelta(minutes=_lock_minutes())
    if datetime.utcnow() >= lock_at:
        raise BettingError("BET_LOCKED", f"開賽前 {_lock_minutes()} 分鐘已截止下注")


def _validate_choice(match, predicted_result):
    # 淘汰賽不接受「和局」
    if match.stage != MatchStage.GROUP and predicted_result == BetChoice.DRAW:
        raise BettingError("INVALID_CHOICE", "淘汰賽不可預測和局，請選擇晉級隊伍")


def _validate_items(use_double, use_insurance):
    if use_double and use_insurance:
        raise BettingError("ITEM_CONFLICT", "翻倍卡與保險卡不可同時使用")


def _apply_item_delta(user, old_double, old_insurance, new_double, new_insurance):
    """依道具使用差異補扣 / 退還；不足則拋錯。負 delta = 需扣除。"""
    double_delta = int(new_double) - int(old_double)      # +1 表示新增使用→扣 1 張
    insurance_delta = int(new_insurance) - int(old_insurance)

    if user.double_cards - double_delta < 0:
        raise BettingError("NO_DOUBLE_CARD", "翻倍卡數量不足")
    if user.insurance_cards - insurance_delta < 0:
        raise BettingError("NO_INSURANCE_CARD", "保險卡數量不足")

    user.double_cards -= double_delta
    user.insurance_cards -= insurance_delta


def place_bet(user, match, predicted_result, predicted_home_score=None,
              predicted_away_score=None, use_double_card=False,
              use_insurance_card=False):
    """建立注單並扣除道具。"""
    _validate_match_open(match)
    _validate_choice(match, predicted_result)
    _validate_items(use_double_card, use_insurance_card)

    _lock_user(user)  # 序列化道具扣減
    if Bet.query.filter_by(user_id=user.id, match_id=match.id).first():
        raise BettingError("DUPLICATE_BET", "已對此賽事下注，請使用改注")

    # 扣道具（從 0 → 使用）
    _apply_item_delta(user, False, False, use_double_card, use_insurance_card)

    bet = Bet(
        user_id=user.id,
        match_id=match.id,
        predicted_result=predicted_result,
        predicted_home_score=predicted_home_score,
        predicted_away_score=predicted_away_score,
        use_double_card=use_double_card,
        use_insurance_card=use_insurance_card,
    )
    db.session.add(bet)
    db.session.commit()
    return bet


def update_bet(bet, predicted_result=None, predicted_home_score=None,
               predicted_away_score=None, use_double_card=None,
               use_insurance_card=None):
    """改注（鎖盤前）。道具差異即時補扣 / 退還。"""
    if bet.is_settled:
        raise BettingError("ALREADY_SETTLED", "注單已結算，無法修改")
    _validate_match_open(bet.match)

    _lock_user(bet.user)  # 序列化道具補扣/退還
    new_double = bet.use_double_card if use_double_card is None else use_double_card
    new_insurance = bet.use_insurance_card if use_insurance_card is None else use_insurance_card
    _validate_items(new_double, new_insurance)

    if predicted_result is not None:
        _validate_choice(bet.match, predicted_result)
        bet.predicted_result = predicted_result

    # 道具差異調整
    _apply_item_delta(bet.user, bet.use_double_card, bet.use_insurance_card,
                      new_double, new_insurance)
    bet.use_double_card = new_double
    bet.use_insurance_card = new_insurance

    if predicted_home_score is not None:
        bet.predicted_home_score = predicted_home_score
    if predicted_away_score is not None:
        bet.predicted_away_score = predicted_away_score

    db.session.commit()
    return bet


def cancel_bet(bet):
    """取消注單並退還道具。"""
    if bet.is_settled:
        raise BettingError("ALREADY_SETTLED", "注單已結算，無法取消")
    _validate_match_open(bet.match)

    _lock_user(bet.user)  # 序列化道具退還
    # 退還道具
    if bet.use_double_card:
        bet.user.double_cards += 1
    if bet.use_insurance_card:
        bet.user.insurance_cards += 1

    db.session.delete(bet)
    db.session.commit()

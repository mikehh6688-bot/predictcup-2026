"""結算服務 — 把純運算（scoring）套用到 DB：更新注單、使用者積分、排行榜。

觸發點：PATCH /matches/{id}/result（賽事轉 finished）。
未來 Phase 3 由 Cron Job 偵測賽果後呼叫 settle_match()。
"""
from datetime import datetime

from ..extensions import db
from ..constants import MatchStatus, MatchStage, BetChoice
from ..models import Bet
from .scoring import calculate_settlement
from . import leaderboard


class SettlementError(Exception):
    """結算前置條件不符。"""


def settle_match(match):
    """結算一場賽事的所有未結算注單。

    Returns: dict 統計 { "settled": n, "affected_users": m }
    呼叫端負責先設定 home_score/away_score/(advancing_team)。
    """
    if match.home_score is None or match.away_score is None:
        raise SettlementError("賽果未填寫，無法結算")
    if match.stage != MatchStage.GROUP and match.advancing_team is None:
        raise SettlementError("淘汰賽須指定晉級隊伍（advancing_team）")

    bets = Bet.query.filter_by(match_id=match.id, is_settled=False).all()
    affected = set()

    for bet in bets:
        points, exact_hit = calculate_settlement(
            stage=match.stage,
            multiplier=match.multiplier,
            home_score=match.home_score,
            away_score=match.away_score,
            advancing_team=match.advancing_team,
            predicted_result=bet.predicted_result,
            predicted_home_score=bet.predicted_home_score,
            predicted_away_score=bet.predicted_away_score,
            use_double_card=bet.use_double_card,
            use_insurance_card=bet.use_insurance_card,
        )
        bet.points_earned = points
        bet.exact_hit = exact_hit
        bet.is_settled = True
        bet.settled_at = datetime.utcnow()

        bet.user.total_points += points
        affected.add(bet.user)

    match.status = MatchStatus.FINISHED
    db.session.commit()

    # 同步排行榜快取
    for user in affected:
        leaderboard.sync_user(user)

    return {"settled": len(bets), "affected_users": len(affected)}

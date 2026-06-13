"""
結算計算引擎（純函式，無 DB 副作用，可獨立單元測試）。
====================================================

規則來源：專案企劃書「3. 積分與結算邏輯」

小組賽（GROUP）
  - 實際勝隊 → 基準分 = 勝隊進球數
  - 實際和局 → 基準分 = 主隊+客隊進球數
  - 猜對：+基準分 × 倍率　／　猜錯：−基準分 × 倍率

淘汰賽（R16/QF/SF/FINAL）
  - 僅判定晉級隊伍（advancing_team，含 PK 後結果）
  - 基準分 = 晉級隊「常規＋延長賽」進球數（PK 進球不計入）
  - 猜對：+基準分 × 倍率　／　猜錯：−基準分 × 倍率

道具（互斥，呼叫端須先驗證不可同時使用）
  - 保險卡：僅在「猜錯」時把扣分減半（向下取整，對玩家有利）
  - 翻倍卡：最終得分 ×2（含正負）

精準比分紅利
  - 預測比分完全命中額外 +50，不受倍率、翻倍卡影響（獨立加總）
"""
from ..constants import (
    MatchStage,
    BetChoice,
    EXACT_SCORE_BONUS,
)


def _actual_outcome(stage, home_score, away_score, advancing_team):
    """回傳 (實際結果 BetChoice, 基準分 magnitude)。"""
    if stage == MatchStage.GROUP:
        if home_score > away_score:
            return BetChoice.HOME, home_score          # 主勝 → 勝隊(主)進球
        if home_score < away_score:
            return BetChoice.AWAY, away_score          # 客勝 → 勝隊(客)進球
        return BetChoice.DRAW, home_score + away_score  # 和局 → 雙方進球和
    # 淘汰賽：以晉級隊伍判定，基準分取該隊常規＋延長賽進球
    magnitude = home_score if advancing_team == BetChoice.HOME else away_score
    return advancing_team, magnitude


def calculate_settlement(
    *,
    stage,
    multiplier,
    home_score,
    away_score,
    advancing_team,           # BetChoice | None（淘汰賽必填）
    predicted_result,         # BetChoice
    predicted_home_score=None,
    predicted_away_score=None,
    use_double_card=False,
    use_insurance_card=False,
):
    """計算單張注單結算結果。

    Returns:
        (points_earned: int, exact_hit: bool)
    """
    actual, magnitude = _actual_outcome(stage, home_score, away_score, advancing_team)
    correct = predicted_result == actual

    base = magnitude * multiplier
    points = base if correct else -base

    # 保險卡：猜錯時扣分減半（向下取整，偏向玩家）
    if not correct and use_insurance_card:
        points = -(abs(points) // 2)

    # 翻倍卡：最終得分 ×2（與保險卡互斥）
    if use_double_card:
        points *= 2

    # 精準比分紅利（獨立加總，不受倍率 / 翻倍卡影響）
    exact_hit = (
        predicted_home_score is not None
        and predicted_away_score is not None
        and predicted_home_score == home_score
        and predicted_away_score == away_score
    )
    if exact_hit:
        points += EXACT_SCORE_BONUS

    return points, exact_hit

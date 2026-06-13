"""列舉與業務常數 — 不依賴 Flask，供 models 與 services 共用（可獨立單元測試）。"""
import enum


class MatchStatus(enum.Enum):
    """賽事狀態。"""
    SCHEDULED = "scheduled"   # 未開賽（可下注）
    LIVE = "live"             # 進行中（鎖盤）
    FINISHED = "finished"     # 已完賽（可結算）


class MatchStage(enum.Enum):
    """賽事階段 -> 對應積分倍率。"""
    GROUP = "group"           # 小組賽   x1
    R16 = "round_of_16"       # 16 強    x2
    QF = "quarter_final"      # 8 強     x2
    SF = "semi_final"         # 4 強     x5
    FINAL = "final"           # 決賽/季軍 x10


# 階段 -> 倍率（單一真實來源）
STAGE_MULTIPLIER = {
    MatchStage.GROUP: 1,
    MatchStage.R16: 2,
    MatchStage.QF: 2,
    MatchStage.SF: 5,
    MatchStage.FINAL: 10,
}


class BetChoice(enum.Enum):
    """下注選項（小組賽：勝平負；淘汰賽：以主/客代表晉級隊伍）。"""
    HOME = "home"   # 主勝 / 主隊晉級
    DRAW = "draw"   # 和局（僅小組賽）
    AWAY = "away"   # 客勝 / 客隊晉級


# 結算規則常數
EXACT_SCORE_BONUS = 50   # 精準比分紅利（不受倍率 / 翻倍卡影響）

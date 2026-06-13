"""結算引擎單元測試（純 Python，無需 DB / Flask）。

執行： cd backend && python -m pytest tests/test_scoring.py -v
或　   cd backend && python tests/test_scoring.py
"""
import os
import sys
import types

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

# 以 stub 註冊 'app' 套件，繞過 app/__init__.py（其相依 Flask/Redis），
# 讓純運算模組可在無相依環境下單獨測試。
if "app" not in sys.modules:
    _pkg = types.ModuleType("app")
    _pkg.__path__ = [os.path.join(BACKEND_DIR, "app")]
    sys.modules["app"] = _pkg

from app.constants import MatchStage, BetChoice  # noqa: E402
from app.services.scoring import calculate_settlement  # noqa: E402


def settle(**kw):
    defaults = dict(
        stage=MatchStage.GROUP, multiplier=1,
        home_score=0, away_score=0, advancing_team=None,
        predicted_result=BetChoice.HOME,
    )
    defaults.update(kw)
    return calculate_settlement(**defaults)


# --- 小組賽：基礎勝負 ------------------------------------------------------- #
def test_group_correct_home_win():
    # 主勝 3:1，猜主勝 → +勝隊(主)進球 3
    pts, exact = settle(home_score=3, away_score=1, predicted_result=BetChoice.HOME)
    assert pts == 3 and exact is False


def test_group_wrong_loses_winner_goals():
    # 實際客勝 1:2，猜主勝 → −勝隊(客)進球 2
    pts, _ = settle(home_score=1, away_score=2, predicted_result=BetChoice.HOME)
    assert pts == -2


def test_group_draw_correct():
    # 2:2 和局，猜和 → +(2+2)=4
    pts, _ = settle(home_score=2, away_score=2, predicted_result=BetChoice.DRAW)
    assert pts == 4


def test_group_draw_wrong():
    # 2:2 和局，猜主勝 → −(2+2)=4
    pts, _ = settle(home_score=2, away_score=2, predicted_result=BetChoice.HOME)
    assert pts == -4


# --- 倍率 ------------------------------------------------------------------- #
def test_semifinal_multiplier_x5():
    # 4 強 ×5，晉級主隊進球 2，猜對 → 2×5=10
    pts, _ = settle(
        stage=MatchStage.SF, multiplier=5, home_score=2, away_score=1,
        advancing_team=BetChoice.HOME, predicted_result=BetChoice.HOME,
    )
    assert pts == 10


def test_final_multiplier_x10_wrong():
    # 決賽 ×10，晉級客隊進球 1，猜主隊晉級 → −1×10
    pts, _ = settle(
        stage=MatchStage.FINAL, multiplier=10, home_score=1, away_score=1,
        advancing_team=BetChoice.AWAY, predicted_result=BetChoice.HOME,
    )
    assert pts == -10


# --- 淘汰賽：PK 不計入基礎積分 --------------------------------------------- #
def test_knockout_pk_uses_regulation_goals():
    # 常規＋延長 1:1，PK 後主隊晉級；猜主隊晉級 → 基準=主隊常規進球 1 ×倍率2
    pts, _ = settle(
        stage=MatchStage.R16, multiplier=2, home_score=1, away_score=1,
        advancing_team=BetChoice.HOME, predicted_result=BetChoice.HOME,
    )
    assert pts == 2


# --- 保險卡：扣分減半（向下取整）------------------------------------------ #
def test_insurance_halves_penalty():
    # 應扣 5，保險卡 → −(5//2)=−2
    pts, _ = settle(
        home_score=5, away_score=0, predicted_result=BetChoice.AWAY,
        use_insurance_card=True,
    )
    assert pts == -2


def test_insurance_no_effect_when_correct():
    # 猜對時保險卡不影響
    pts, _ = settle(
        home_score=3, away_score=1, predicted_result=BetChoice.HOME,
        use_insurance_card=True,
    )
    assert pts == 3


# --- 翻倍卡 ----------------------------------------------------------------- #
def test_double_card_doubles_gain():
    pts, _ = settle(home_score=3, away_score=1, predicted_result=BetChoice.HOME,
                    use_double_card=True)
    assert pts == 6


def test_double_card_doubles_loss():
    pts, _ = settle(home_score=1, away_score=2, predicted_result=BetChoice.HOME,
                    use_double_card=True)
    assert pts == -4


# --- 精準比分紅利 ----------------------------------------------------------- #
def test_exact_score_bonus_added_flat():
    # 猜對主勝(基礎3) + 精準命中 3:1 → 3 + 50
    pts, exact = settle(
        home_score=3, away_score=1, predicted_result=BetChoice.HOME,
        predicted_home_score=3, predicted_away_score=1,
    )
    assert pts == 53 and exact is True


def test_exact_bonus_not_multiplied_by_double():
    # 翻倍卡只翻基礎分(3→6)，+50 紅利不翻 → 6 + 50 = 56
    pts, exact = settle(
        home_score=3, away_score=1, predicted_result=BetChoice.HOME,
        predicted_home_score=3, predicted_away_score=1, use_double_card=True,
    )
    assert pts == 56 and exact is True


def test_exact_miss_no_bonus():
    pts, exact = settle(
        home_score=3, away_score=1, predicted_result=BetChoice.HOME,
        predicted_home_score=2, predicted_away_score=0,
    )
    assert pts == 3 and exact is False


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✅ {name}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌ {name}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

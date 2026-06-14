"""灌入真實 2026 世界盃「小組賽」賽程（方案 A）。

資料來源：維基百科各組頁面（2026-06-14 擷取）。
- 隊伍、對戰、開賽日期/時間皆為真實賽程。
- 已踢完的場次填入真實比分並標記為「已完賽」；未踢的留空（status=未開賽）。
- 淘汰賽不灌（隊伍待小組賽結束才確定），日後由後台「更新賽果」或 API 補上。

執行：cd backend && REDIS_URL="" DATABASE_URL="sqlite:///dev.db" python seed_worldcup.py
注意：此腳本會清除既有「賽事」與相關注單，但不動使用者/排行榜。
"""
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Match, Bet
from app.constants import MatchStatus, MatchStage
from app.services.wc_data import TEAM  # 英文隊名 -> (繁中, 國旗碼)，與爬蟲共用

# (組, 日期, 當地時間, 主隊, 客隊, 主隊進球, 客隊進球)；None = 尚未開賽
FIXTURES = [
    ("A", "2026-06-11", "13:00", "Mexico", "South Africa", 2, 0),
    ("A", "2026-06-11", "20:00", "South Korea", "Czech Republic", 2, 1),
    ("A", "2026-06-18", "12:00", "Czech Republic", "South Africa", None, None),
    ("A", "2026-06-18", "19:00", "Mexico", "South Korea", None, None),
    ("A", "2026-06-24", "19:00", "Czech Republic", "Mexico", None, None),
    ("A", "2026-06-24", "19:00", "South Africa", "South Korea", None, None),

    ("B", "2026-06-12", "15:00", "Canada", "Bosnia and Herzegovina", 1, 1),
    ("B", "2026-06-13", "12:00", "Qatar", "Switzerland", 1, 1),
    ("B", "2026-06-18", "12:00", "Switzerland", "Bosnia and Herzegovina", None, None),
    ("B", "2026-06-18", "15:00", "Canada", "Qatar", None, None),
    ("B", "2026-06-24", "12:00", "Switzerland", "Canada", None, None),
    ("B", "2026-06-24", "12:00", "Bosnia and Herzegovina", "Qatar", None, None),

    ("C", "2026-06-13", "18:00", "Brazil", "Morocco", 1, 1),
    ("C", "2026-06-13", "21:00", "Haiti", "Scotland", 0, 1),
    ("C", "2026-06-19", "18:00", "Scotland", "Morocco", None, None),
    ("C", "2026-06-19", "20:30", "Brazil", "Haiti", None, None),
    ("C", "2026-06-24", "18:00", "Scotland", "Brazil", None, None),
    ("C", "2026-06-24", "18:00", "Morocco", "Haiti", None, None),

    ("D", "2026-06-12", "18:00", "United States", "Paraguay", 4, 1),
    ("D", "2026-06-13", "21:00", "Australia", "Turkey", None, None),
    ("D", "2026-06-19", "12:00", "United States", "Australia", None, None),
    ("D", "2026-06-19", "20:00", "Turkey", "Paraguay", None, None),
    ("D", "2026-06-25", "19:00", "Turkey", "United States", None, None),
    ("D", "2026-06-25", "19:00", "Paraguay", "Australia", None, None),

    ("E", "2026-06-14", "12:00", "Germany", "Curaçao", None, None),
    ("E", "2026-06-14", "19:00", "Ivory Coast", "Ecuador", None, None),
    ("E", "2026-06-20", "16:00", "Germany", "Ivory Coast", None, None),
    ("E", "2026-06-20", "19:00", "Ecuador", "Curaçao", None, None),
    ("E", "2026-06-25", "16:00", "Curaçao", "Ivory Coast", None, None),
    ("E", "2026-06-25", "16:00", "Ecuador", "Germany", None, None),

    ("F", "2026-06-14", "15:00", "Netherlands", "Japan", None, None),
    ("F", "2026-06-14", "20:00", "Sweden", "Tunisia", None, None),
    ("F", "2026-06-20", "12:00", "Netherlands", "Sweden", None, None),
    ("F", "2026-06-20", "22:00", "Tunisia", "Japan", None, None),
    ("F", "2026-06-25", "18:00", "Japan", "Sweden", None, None),
    ("F", "2026-06-25", "18:00", "Tunisia", "Netherlands", None, None),

    ("G", "2026-06-15", "12:00", "Belgium", "Egypt", None, None),
    ("G", "2026-06-15", "18:00", "Iran", "New Zealand", None, None),
    ("G", "2026-06-21", "12:00", "Belgium", "Iran", None, None),
    ("G", "2026-06-21", "18:00", "New Zealand", "Egypt", None, None),
    ("G", "2026-06-26", "20:00", "Egypt", "Iran", None, None),
    ("G", "2026-06-26", "20:00", "New Zealand", "Belgium", None, None),

    ("H", "2026-06-15", "12:00", "Spain", "Cape Verde", None, None),
    ("H", "2026-06-15", "18:00", "Saudi Arabia", "Uruguay", None, None),
    ("H", "2026-06-21", "12:00", "Spain", "Saudi Arabia", None, None),
    ("H", "2026-06-21", "18:00", "Uruguay", "Cape Verde", None, None),
    ("H", "2026-06-26", "19:00", "Cape Verde", "Saudi Arabia", None, None),
    ("H", "2026-06-26", "18:00", "Uruguay", "Spain", None, None),

    ("I", "2026-06-16", "15:00", "France", "Senegal", None, None),
    ("I", "2026-06-16", "18:00", "Iraq", "Norway", None, None),
    ("I", "2026-06-22", "17:00", "France", "Iraq", None, None),
    ("I", "2026-06-22", "20:00", "Norway", "Senegal", None, None),
    ("I", "2026-06-26", "15:00", "Norway", "France", None, None),
    ("I", "2026-06-26", "15:00", "Senegal", "Iraq", None, None),

    ("J", "2026-06-16", "20:00", "Argentina", "Algeria", None, None),
    ("J", "2026-06-16", "21:00", "Austria", "Jordan", None, None),
    ("J", "2026-06-22", "12:00", "Argentina", "Austria", None, None),
    ("J", "2026-06-22", "20:00", "Jordan", "Algeria", None, None),
    ("J", "2026-06-27", "21:00", "Algeria", "Austria", None, None),
    ("J", "2026-06-27", "21:00", "Jordan", "Argentina", None, None),

    ("K", "2026-06-17", "12:00", "Portugal", "DR Congo", None, None),
    ("K", "2026-06-17", "20:00", "Uzbekistan", "Colombia", None, None),
    ("K", "2026-06-23", "12:00", "Portugal", "Uzbekistan", None, None),
    ("K", "2026-06-23", "20:00", "Colombia", "DR Congo", None, None),
    ("K", "2026-06-27", "19:30", "Colombia", "Portugal", None, None),
    ("K", "2026-06-27", "19:30", "DR Congo", "Uzbekistan", None, None),

    ("L", "2026-06-17", "15:00", "England", "Croatia", None, None),
    ("L", "2026-06-17", "19:00", "Ghana", "Panama", None, None),
    ("L", "2026-06-23", "16:00", "England", "Ghana", None, None),
    ("L", "2026-06-23", "19:00", "Panama", "Croatia", None, None),
    ("L", "2026-06-27", "17:00", "Panama", "England", None, None),
    ("L", "2026-06-27", "17:00", "Croatia", "Ghana", None, None),
]

# 當地時間多為美東/中部，統一以 UTC-4 近似換算成 UTC（測試用，分秒不影響邏輯）
_LOCAL_TO_UTC_HOURS = 4


def _kickoff_utc(date_str, time_str):
    local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return local + timedelta(hours=_LOCAL_TO_UTC_HOURS)


def run():
    app = create_app()
    with app.app_context():
        # 清除既有賽事與注單（不動使用者）
        db.session.query(Bet).delete()
        db.session.query(Match).delete()
        db.session.commit()

        played = 0
        for i, (grp, date, time, home, away, hs, as_) in enumerate(FIXTURES):
            home_zh, home_code = TEAM[home]
            away_zh, away_code = TEAM[away]
            finished = hs is not None and as_ is not None
            match = Match(
                home_team=home_zh, away_team=away_zh,
                home_team_code=home_code, away_team_code=away_code,
                kickoff_time=_kickoff_utc(date, time),
                stage=MatchStage.GROUP,
                external_ref=f"wc2026-{grp}-{i}",
            )
            if finished:
                match.home_score = hs
                match.away_score = as_
                match.status = MatchStatus.FINISHED
                played += 1
            db.session.add(match)
        db.session.commit()
        print(f"✅ Seeded {len(FIXTURES)} group-stage matches ({played} finished, "
              f"{len(FIXTURES) - played} upcoming)")


if __name__ == "__main__":
    run()

"""本地 demo 用：建立資料表並塞入範例資料（SQLite）。

用法：
  REDIS_URL="" DATABASE_URL="sqlite:///dev.db" python seed.py
"""
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import User, Match
from app.constants import MatchStage, MatchStatus, BetChoice
from app.services import leaderboard


def run():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # 使用者（不同積分供排行榜展示）
        users = [
            User(username="阿哲", total_points=980),
            User(username="小美", total_points=845),
            User(username="Kevin", total_points=712),
            User(username="阿肥", total_points=-30),
        ]
        db.session.add_all(users)

        now = datetime.utcnow()
        matches = [
            Match(home_team="巴西", away_team="阿根廷",
                  home_team_code="BRA", away_team_code="ARG",
                  kickoff_time=now + timedelta(hours=3), stage=MatchStage.GROUP,
                  ai_home_win_prob=0.46, ai_draw_prob=0.27, ai_away_win_prob=0.27,
                  ai_analysis="巴西主場火力旺盛，阿根廷中場控制力強。"),
            Match(home_team="法國", away_team="英格蘭",
                  home_team_code="FRA", away_team_code="ENG",
                  kickoff_time=now + timedelta(hours=6), stage=MatchStage.R16,
                  ai_home_win_prob=0.41, ai_draw_prob=0.31, ai_away_win_prob=0.28),
            Match(home_team="西班牙", away_team="德國",
                  home_team_code="ESP", away_team_code="GER",
                  kickoff_time=now - timedelta(hours=2), stage=MatchStage.GROUP,
                  status=MatchStatus.FINISHED, home_score=2, away_score=1,
                  ai_home_win_prob=0.5, ai_draw_prob=0.25, ai_away_win_prob=0.25),
        ]
        db.session.add_all(matches)
        db.session.commit()

        for u in users:
            leaderboard.sync_user(u)

        print(f"✅ Seeded {len(users)} users, {len(matches)} matches")


if __name__ == "__main__":
    run()

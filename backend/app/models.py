"""
PredictCup 2026 — SQLAlchemy Models
====================================
涵蓋 5 張核心資料表：
  - User          使用者（積分 / 道具）
  - Match         賽事（含 AI 勝率、網民風向預留欄位）
  - Bet           注單（下注 / 結算）
  - League        私房聯賽
  - LeagueMember  聯賽成員（User <-> League 多對多）

設計重點：
  * 使用 Enum 約束狀態欄位，避免髒資料。
  * 倍率（multiplier）由賽事階段（stage）決定，存成欄位方便結算與查詢。
  * AI 勝率 / 網民風向為「Flask 預留欄位」，初始為 NULL，由 Phase 3 微服務寫入。
  * 金額/積分一律用整數（分制），結算邏輯在 Phase 2 實作。
"""
import secrets
from datetime import datetime

from .extensions import db
from .constants import MatchStatus, MatchStage, BetChoice, STAGE_MULTIPLIER

__all__ = [
    "User", "Match", "Bet", "League", "LeagueMember",
    "MatchStatus", "MatchStage", "BetChoice", "STAGE_MULTIPLIER",
]


# --------------------------------------------------------------------------- #
# User
# --------------------------------------------------------------------------- #
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)  # SSO 預留

    # SSO 預留：provider(google/line) + 對應 sub id
    sso_provider = db.Column(db.String(20), nullable=True)
    sso_subject = db.Column(db.String(128), nullable=True)

    total_points = db.Column(db.Integer, nullable=False, default=100)
    double_cards = db.Column(db.Integer, nullable=False, default=3)      # 翻倍卡
    insurance_cards = db.Column(db.Integer, nullable=False, default=1)   # 保險卡

    is_admin = db.Column(db.Boolean, nullable=False, default=False)      # 管理者（可進後台）

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    bets = db.relationship("Bet", back_populates="user", cascade="all, delete-orphan")
    owned_leagues = db.relationship("League", back_populates="owner")
    memberships = db.relationship(
        "LeagueMember", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "total_points": self.total_points,
            "double_cards": self.double_cards,
            "insurance_cards": self.insurance_cards,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# --------------------------------------------------------------------------- #
# Match
# --------------------------------------------------------------------------- #
class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)

    home_team = db.Column(db.String(50), nullable=False)
    away_team = db.Column(db.String(50), nullable=False)
    # ISO 國家代碼，前端用來顯示國旗（如 'BRA', 'ARG'）
    home_team_code = db.Column(db.String(3), nullable=True)
    away_team_code = db.Column(db.String(3), nullable=True)

    kickoff_time = db.Column(db.DateTime, nullable=False, index=True)
    # 對應第三方賽事 API 的 fixture id（自動同步賽果用；手動建立可留空）
    external_ref = db.Column(db.String(40), nullable=True, unique=True)

    status = db.Column(
        db.Enum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED, index=True
    )
    stage = db.Column(db.Enum(MatchStage), nullable=False, default=MatchStage.GROUP)
    # 倍率：由 stage 決定，建立時自動填入（見 __init__）
    multiplier = db.Column(db.Integer, nullable=False, default=1)

    # 賽果（常規＋延長賽進球；PK 不計入基礎積分）
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    # 淘汰賽 PK 後實際晉級隊伍（結算晉級用，不影響基礎積分）
    advancing_team = db.Column(db.Enum(BetChoice), nullable=True)

    # --- Flask / AI 微服務預留欄位（Phase 3 寫入；初始 NULL）---
    ai_home_win_prob = db.Column(db.Float, nullable=True)   # AI 主勝機率 0~1
    ai_draw_prob = db.Column(db.Float, nullable=True)       # AI 和局機率 0~1
    ai_away_win_prob = db.Column(db.Float, nullable=True)   # AI 客勝機率 0~1
    ai_analysis = db.Column(db.Text, nullable=True)         # LLM 生成賽況摘要

    # 網民風向（外部爬蟲聲量比例 0~1）
    public_home_pct = db.Column(db.Float, nullable=True)
    public_draw_pct = db.Column(db.Float, nullable=True)
    public_away_pct = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    bets = db.relationship("Bet", back_populates="match", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 依階段自動套用倍率（除非呼叫端明確覆寫）
        if "multiplier" not in kwargs and self.stage is not None:
            self.multiplier = STAGE_MULTIPLIER.get(self.stage, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_code": self.home_team_code,
            "away_team_code": self.away_team_code,
            "kickoff_time": self.kickoff_time.isoformat() if self.kickoff_time else None,
            "status": self.status.value if self.status else None,
            "stage": self.stage.value if self.stage else None,
            "multiplier": self.multiplier,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "advancing_team": self.advancing_team.value if self.advancing_team else None,
            "ai_prediction": {
                "home": self.ai_home_win_prob,
                "draw": self.ai_draw_prob,
                "away": self.ai_away_win_prob,
                "analysis": self.ai_analysis,
            },
            "public_sentiment": {
                "home": self.public_home_pct,
                "draw": self.public_draw_pct,
                "away": self.public_away_pct,
            },
        }


# --------------------------------------------------------------------------- #
# Bet（注單）
# --------------------------------------------------------------------------- #
class Bet(db.Model):
    __tablename__ = "bets"
    # 一個使用者對同一場賽事只能有一張注單
    __table_args__ = (
        db.UniqueConstraint("user_id", "match_id", name="uq_user_match_bet"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False, index=True)

    predicted_result = db.Column(db.Enum(BetChoice), nullable=False)  # 主勝/平/客勝
    # 精準比分（選填）
    predicted_home_score = db.Column(db.Integer, nullable=True)
    predicted_away_score = db.Column(db.Integer, nullable=True)

    # 道具
    use_double_card = db.Column(db.Boolean, nullable=False, default=False)     # 翻倍卡
    use_insurance_card = db.Column(db.Boolean, nullable=False, default=False)  # 保險卡

    # 結算結果（Phase 2 寫入）
    is_settled = db.Column(db.Boolean, nullable=False, default=False)
    points_earned = db.Column(db.Integer, nullable=True)   # 結算後增減的積分（可負）
    exact_hit = db.Column(db.Boolean, nullable=False, default=False)  # 是否命中精準比分

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    settled_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="bets")
    match = db.relationship("Match", back_populates="bets")

    @property
    def has_exact_prediction(self):
        return self.predicted_home_score is not None and self.predicted_away_score is not None

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "match_id": self.match_id,
            "predicted_result": self.predicted_result.value if self.predicted_result else None,
            "predicted_home_score": self.predicted_home_score,
            "predicted_away_score": self.predicted_away_score,
            "use_double_card": self.use_double_card,
            "use_insurance_card": self.use_insurance_card,
            "is_settled": self.is_settled,
            "points_earned": self.points_earned,
            "exact_hit": self.exact_hit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# --------------------------------------------------------------------------- #
# League（私房聯賽） + LeagueMember
# --------------------------------------------------------------------------- #
class League(db.Model):
    __tablename__ = "leagues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)  # 例：KMC 知識管理中心部門大賽
    invite_code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner = db.relationship("User", back_populates="owned_leagues")
    members = db.relationship(
        "LeagueMember", back_populates="league", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.invite_code:
            self.invite_code = self.generate_invite_code()

    @staticmethod
    def generate_invite_code():
        """產生 8 碼大寫英數邀請碼。"""
        return secrets.token_hex(4).upper()

    def to_dict(self, include_members=False):
        data = {
            "id": self.id,
            "name": self.name,
            "invite_code": self.invite_code,
            "owner_id": self.owner_id,
            "member_count": len(self.members),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_members:
            data["members"] = [m.user_id for m in self.members]
        return data


class LeagueMember(db.Model):
    __tablename__ = "league_members"
    __table_args__ = (
        db.UniqueConstraint("league_id", "user_id", name="uq_league_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    league = db.relationship("League", back_populates="members")
    user = db.relationship("User", back_populates="memberships")

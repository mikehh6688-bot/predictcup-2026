"""應用設定。依環境變數載入，預留多環境（dev/prod）擴充空間。"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# 視為不安全的預設密鑰（正式環境啟動時拒絕使用）
INSECURE_SECRETS = {"dev-secret-key", "change-me", "change-me-in-production",
                    "change-me-too", "dev-secret"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # PostgreSQL（關聯式主資料）
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/predictcup"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis（每日排行榜 / 熱門賽事狀態快取）
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # CORS 允許來源（逗號分隔；dev 預設全開，正式環境須收斂）
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # 業務規則常數（集中管理，方便日後調整）
    DEFAULT_POINTS = 100          # 註冊初始積分
    DEFAULT_DOUBLE_CARDS = 3      # 翻倍卡
    DEFAULT_INSURANCE_CARDS = 1   # 保險卡
    EXACT_SCORE_BONUS = 50        # 精準比分紅利（不受倍率影響）
    BET_LOCK_MINUTES = 5          # 開賽前 N 分鐘鎖盤

    # --- Auth / SSO（Phase 5）---
    JWT_SECRET = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "72"))
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")  # 驗證 Google id_token 的 audience
    ALLOW_DEV_LOGIN = os.environ.get("ALLOW_DEV_LOGIN", "true").lower() == "true"

    # 管理者名單（登入時比對 email 或 username，命中即授予 is_admin）
    ADMIN_EMAILS = os.environ.get("ADMIN_EMAILS", "mike.hsieh72@gmail.com")
    ADMIN_USERNAMES = os.environ.get("ADMIN_USERNAMES", "Mike")

    # --- AI 微服務（Phase 5）---
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    AI_MODEL = os.environ.get("AI_MODEL", "claude-opus-4-8")

    # --- 第三方賽事 API（Phase 5）---
    SPORTS_API_KEY = os.environ.get("SPORTS_API_KEY")
    SPORTS_API_BASE = os.environ.get("SPORTS_API_BASE", "https://v3.football.api-sports.io")
    # API-Football：FIFA World Cup league id = 1；2026 賽季 season = 2026
    SPORTS_LEAGUE_ID = int(os.environ.get("SPORTS_LEAGUE_ID", "1"))
    SPORTS_SEASON = int(os.environ.get("SPORTS_SEASON", "2026"))

    # --- 排程器（Cron 自動結算 / 賽果同步）---
    SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "false").lower() == "true"
    SETTLE_INTERVAL_MINUTES = int(os.environ.get("SETTLE_INTERVAL_MINUTES", "5"))
    RESULT_SYNC_INTERVAL_MINUTES = int(os.environ.get("RESULT_SYNC_INTERVAL_MINUTES", "10"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # 正式環境預設「關閉」開發暱稱登入（避免任意人冒充管理者）
    ALLOW_DEV_LOGIN = os.environ.get("ALLOW_DEV_LOGIN", "false").lower() == "true"
    # CORS 正式環境須明確設定（空字串 → 啟動時驗證會擋下）
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

    @staticmethod
    def validate():
        """正式環境啟動前置檢查；任一不符即拒絕啟動（fail-fast）。"""
        problems = []
        if Config.SECRET_KEY in INSECURE_SECRETS:
            problems.append("SECRET_KEY 仍為預設值，請設定強隨機值")
        if Config.JWT_SECRET in INSECURE_SECRETS:
            problems.append("JWT_SECRET 仍為預設值，請設定強隨機值")
        if not Config.GOOGLE_CLIENT_ID:
            problems.append("GOOGLE_CLIENT_ID 未設定（正式環境僅允許 Google 登入）")
        origins = os.environ.get("CORS_ORIGINS", "")
        if not origins or origins == "*":
            problems.append("CORS_ORIGINS 未收斂（不可為空或 *），請設定前端網域")
        if problems:
            raise RuntimeError(
                "正式環境設定不安全，拒絕啟動：\n  - " + "\n  - ".join(problems)
            )


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

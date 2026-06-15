"""Application Factory。"""
import os

from flask import Flask
from flask_cors import CORS

from config import config_map, ProductionConfig
from . import extensions
from .extensions import db, migrate, limiter


def create_app(config_name=None, overrides=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map["default"]))
    if overrides:
        app.config.update(overrides)  # 測試用設定覆寫

    # 正式環境啟動前置檢查（密鑰 / Google / CORS）
    if config_name == "production":
        ProductionConfig.validate()

    # 錯誤追蹤（設定 SENTRY_DSN 才啟用）
    dsn = app.config.get("SENTRY_DSN")
    if dsn:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(dsn=dsn, integrations=[FlaskIntegration()],
                        traces_sample_rate=0.1, environment=config_name)

    # 擴充套件
    db.init_app(app)
    migrate.init_app(app, db)

    # 限流：storage 用 Redis（有則）否則記憶體；測試環境停用
    app.config.setdefault("RATELIMIT_STORAGE_URI", app.config.get("REDIS_URL") or "memory://")
    app.config["RATELIMIT_ENABLED"] = not app.config.get("TESTING", False)
    limiter.init_app(app)

    # CORS：依設定收斂來源（dev 預設 '*' 全開；正式須指定網域）
    origins = app.config.get("CORS_ORIGINS", "*")
    if origins and origins != "*":
        CORS(app, origins=[o.strip() for o in origins.split(",") if o.strip()])
    else:
        CORS(app)

    # Redis（排行榜快取）— 延後匯入；無 REDIS_URL（如測試）則停用，
    # leaderboard 服務會自動退回 DB 直查。
    if app.config.get("REDIS_URL"):
        import redis
        extensions.redis_client = redis.from_url(
            app.config["REDIS_URL"], decode_responses=True
        )
    else:
        extensions.redis_client = None

    # 確保 models 被載入（供 migrate 偵測）
    from . import models  # noqa: F401

    # 註冊 Blueprints
    from .api import register_blueprints
    register_blueprints(app)

    # 背景排程（Cron 自動結算 / 賽果同步）— 僅在 SCHEDULER_ENABLED 時啟動
    from .services.scheduler import init_scheduler
    init_scheduler(app)

    @app.get("/health")
    def health():
        """Liveness：行程存活即回 200。"""
        return {"status": "ok", "service": "predictcup-api"}

    @app.get("/ready")
    def ready():
        """Readiness：DB / Redis 可用才回 200，否則 503（供 LB / k8s 探針）。"""
        from sqlalchemy import text
        checks = {"db": False, "redis": True}
        try:
            db.session.execute(text("SELECT 1"))
            checks["db"] = True
        except Exception:
            db.session.rollback()
        if extensions.redis_client is not None:
            try:
                checks["redis"] = bool(extensions.redis_client.ping())
            except Exception:
                checks["redis"] = False
        ok_all = all(checks.values())
        return ({"status": "ready" if ok_all else "degraded", "checks": checks},
                200 if ok_all else 503)

    return app

"""Application Factory。"""
import os

from flask import Flask
from flask_cors import CORS

from config import config_map
from . import extensions
from .extensions import db, migrate


def create_app(config_name=None, overrides=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map["default"]))
    if overrides:
        app.config.update(overrides)  # 測試用設定覆寫

    # 擴充套件
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)  # 允許 Next.js 前端跨域呼叫

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
        return {"status": "ok", "service": "predictcup-api"}

    return app

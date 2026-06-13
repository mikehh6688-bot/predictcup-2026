"""API Blueprints 註冊中心。

Phase 1：僅定義路由、Request/Response 格式（回傳 501 佔位）。
Phase 2：填入結算等核心邏輯。
"""
from .auth import bp as auth_bp
from .users import bp as users_bp
from .matches import bp as matches_bp
from .bets import bp as bets_bp
from .leagues import bp as leagues_bp
from .leaderboard import bp as leaderboard_bp

API_PREFIX = "/api/v1"


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix=f"{API_PREFIX}/auth")
    app.register_blueprint(users_bp, url_prefix=f"{API_PREFIX}/users")
    app.register_blueprint(matches_bp, url_prefix=f"{API_PREFIX}/matches")
    app.register_blueprint(bets_bp, url_prefix=f"{API_PREFIX}/bets")
    app.register_blueprint(leagues_bp, url_prefix=f"{API_PREFIX}/leagues")
    app.register_blueprint(leaderboard_bp, url_prefix=f"{API_PREFIX}/leaderboard")

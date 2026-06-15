"""集中管理 Flask 擴充套件實例，避免循環匯入。"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)  # 預設依來源 IP 限流

# Redis client 於 app factory 內初始化（見 __init__.py），
# 此處僅宣告佔位，供其他模組匯入。
redis_client = None

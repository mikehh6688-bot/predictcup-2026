"""API 共用工具：統一錯誤格式、列舉解析、（開發版）取得登入者。"""
from functools import wraps

from flask import jsonify, request

from ..extensions import db
from ..models import User
from ..constants import BetChoice, MatchStage, MatchStatus


def error(code, message, status=400):
    return jsonify({"error": {"code": code, "message": message}}), status


def ok(data, status=200):
    return jsonify(data), status


def parse_enum(enum_cls, value, field):
    """字串 -> Enum，失敗則拋 ValueError（呼叫端轉 400）。"""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise ValueError(f"{field} 無效，可選：{allowed}")


def current_user():
    """從 Authorization: Bearer <jwt> 解析登入者。"""
    from ..services.auth import decode_token

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    user_id = decode_token(auth[7:])
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return error("UNAUTHORIZED", "請先登入", 401)
        return fn(user, *args, **kwargs)
    return wrapper

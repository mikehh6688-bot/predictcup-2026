"""帳號與權限 — SSO 登入（Google / dev），簽發本地 JWT。"""
from flask import Blueprint, request

from ..extensions import limiter
from ..services import auth as auth_service
from ._helpers import error, ok, current_user

bp = Blueprint("auth", __name__)


@bp.post("/sso")
@limiter.limit("10 per minute")
def sso_login():
    """SSO 登入，回傳本地 JWT。

    Request JSON:
      Google: { "provider": "google", "id_token": "<google id_token>" }
      Dev   : { "provider": "dev", "username": "mike" }   # ALLOW_DEV_LOGIN 時
    Response JSON: { "token": "<jwt>", "user": <User> }
    """
    data = request.get_json(silent=True) or {}
    try:
        user, token = auth_service.login_with_sso(
            provider=data.get("provider"),
            id_token=data.get("id_token"),
            username=(data.get("username") or "").strip() or None,
            email=data.get("email"),
        )
    except auth_service.AuthError as e:
        return error(e.code, e.message, e.status)
    return ok({"token": token, "user": user.to_dict()})


@bp.get("/me")
def me():
    """取得目前登入者（首頁積分／道具卡片）。"""
    user = current_user()
    if user is None:
        return error("UNAUTHORIZED", "請先登入", 401)
    return ok(user.to_dict())


@bp.post("/logout")
def logout():
    """登出（JWT 無狀態，由前端丟棄 token；此處回 204）。"""
    return "", 204

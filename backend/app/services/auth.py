"""身分驗證服務 — JWT 簽發/驗證 + SSO（Google / LINE）身分核對。

設計：
  * 後端簽發自有 JWT（HS256），前端帶 `Authorization: Bearer <jwt>`。
  * SSO：核對第三方 id_token 取得使用者身分，再對應/建立本地帳號。
    - Google：以 tokeninfo 端點驗證 id_token（正式環境建議改本地 JWK 驗簽）。
    - LINE / 其他：預留 verify_* 介面。
  * 開發模式（ALLOW_DEV_LOGIN）：允許用 username 直接登入，方便本地測試。
"""
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import User
from . import leaderboard


class AuthError(Exception):
    def __init__(self, code, message, status=401):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def issue_token(user):
    """簽發本地 JWT。"""
    import jwt  # 延後匯入，避免無相依環境載入失敗

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "iat": now,
        "exp": now + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token):
    """驗證並解碼 JWT，回傳 user_id（int）或 None。"""
    import jwt

    try:
        payload = jwt.decode(
            token, current_app.config["JWT_SECRET"], algorithms=["HS256"]
        )
        return int(payload["sub"])
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# SSO 身分核對
# --------------------------------------------------------------------------- #
def verify_google_id_token(id_token):
    """驗證 Google id_token，回傳 {sub, email, name}。

    使用 Google tokeninfo 端點（簡單可靠）；高流量正式環境建議改為本地
    JWK 快取驗簽（google-auth），避免每次往返。
    """
    import requests

    try:
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=5,
        )
    except requests.RequestException:
        raise AuthError("SSO_UNAVAILABLE", "無法連線 Google 驗證服務", 502)

    if resp.status_code != 200:
        raise AuthError("INVALID_ID_TOKEN", "Google id_token 無效")

    data = resp.json()
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if client_id and data.get("aud") != client_id:
        raise AuthError("AUD_MISMATCH", "id_token audience 不符")

    return {
        "sub": data.get("sub"),
        "email": data.get("email"),
        "name": data.get("name") or (data.get("email") or "").split("@")[0],
    }


def _is_admin(username, email):
    """依設定的管理者名單判定（email 或 username 命中即為管理者）。"""
    emails = {
        e.strip().lower()
        for e in (current_app.config.get("ADMIN_EMAILS") or "").split(",")
        if e.strip()
    }
    names = {
        n.strip()
        for n in (current_app.config.get("ADMIN_USERNAMES") or "").split(",")
        if n.strip()
    }
    return bool((email and email.lower() in emails) or (username and username in names))


def _get_or_create(provider, subject, username, email=None):
    """以 (provider, subject) 對應本地帳號；不存在則建立並配發初始道具。"""
    user = None
    if subject:
        user = User.query.filter_by(sso_provider=provider, sso_subject=subject).first()
    if user is None and email:
        user = User.query.filter_by(email=email).first()
    if user is None:
        # 避免 username 衝突
        base = username or "user"
        candidate, n = base, 1
        while User.query.filter_by(username=candidate).first():
            n += 1
            candidate = f"{base}{n}"
        user = User(
            username=candidate, email=email,
            sso_provider=provider, sso_subject=subject,
            is_admin=_is_admin(candidate, email),
        )  # 積分 / 道具走 model 預設值
        db.session.add(user)
        db.session.commit()
        leaderboard.sync_user(user)
    elif _is_admin(user.username, user.email) and not user.is_admin:
        # 既有帳號補授管理者（例如名單調整後）
        user.is_admin = True
        db.session.commit()
    return user


def login_with_sso(provider, id_token=None, username=None, email=None):
    """SSO 登入主流程，回傳 (user, jwt)。"""
    if provider == "google":
        if not id_token:
            raise AuthError("MISSING_ID_TOKEN", "缺少 id_token")
        info = verify_google_id_token(id_token)
        user = _get_or_create("google", info["sub"], info["name"], info["email"])
    elif provider == "dev" or provider is None:
        if not current_app.config.get("ALLOW_DEV_LOGIN"):
            raise AuthError("DEV_LOGIN_DISABLED", "開發登入已停用", 403)
        if not username:
            raise AuthError("MISSING_USERNAME", "缺少 username")
        user = _get_or_create("dev", f"dev:{username}", username, email)
    else:
        raise AuthError("UNSUPPORTED_PROVIDER", f"尚未支援的登入方式：{provider}", 400)

    return user, issue_token(user)

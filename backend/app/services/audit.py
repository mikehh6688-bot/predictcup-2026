"""管理者操作稽核 —— 記錄誰在何時做了什麼（更新賽果、自動同步等）。"""
from ..extensions import db
from ..models import AuditLog


def record(user, action, detail=None):
    """寫入一筆稽核紀錄（best-effort，不因記錄失敗中斷主流程）。"""
    try:
        db.session.add(AuditLog(
            user_id=getattr(user, "id", None),
            username=getattr(user, "username", None),
            action=action,
            detail=detail,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

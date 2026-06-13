"""使用者資料、道具背包、個人注單歷史。"""
from flask import Blueprint, request

from ..extensions import db
from ..models import User, Bet
from ._helpers import error, ok

bp = Blueprint("users", __name__)


@bp.get("/<int:user_id>")
def get_user(user_id):
    """取得指定使用者公開資料。"""
    user = db.session.get(User, user_id)
    if user is None:
        return error("NOT_FOUND", "使用者不存在", 404)
    return ok(user.to_dict())


@bp.get("/<int:user_id>/inventory")
def get_inventory(user_id):
    """道具背包（翻倍卡 / 保險卡數量）。"""
    user = db.session.get(User, user_id)
    if user is None:
        return error("NOT_FOUND", "使用者不存在", 404)
    return ok({
        "double_cards": user.double_cards,
        "insurance_cards": user.insurance_cards,
    })


@bp.get("/<int:user_id>/bets")
def get_user_bets(user_id):
    """個人注單歷史。Query: ?status=pending|settled"""
    user = db.session.get(User, user_id)
    if user is None:
        return error("NOT_FOUND", "使用者不存在", 404)

    q = Bet.query.filter_by(user_id=user_id)
    status = request.args.get("status")
    if status == "pending":
        q = q.filter_by(is_settled=False)
    elif status == "settled":
        q = q.filter_by(is_settled=True)

    bets = q.order_by(Bet.created_at.desc()).all()
    return ok({"bets": [b.to_dict() for b in bets]})

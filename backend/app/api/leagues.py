"""私房聯賽 — 建立 / 加入 / 成員排名。"""
from flask import Blueprint, request

from ..extensions import db
from ..models import League, LeagueMember, User
from ._helpers import error, ok, login_required

bp = Blueprint("leagues", __name__)


@bp.post("")
@login_required
def create_league(user):
    """建立聯賽（自動產生邀請碼，建立者自動入會）。"""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error("INVALID_INPUT", "name 為必填")

    league = League(name=name, owner_id=user.id)  # invite_code 自動產生
    db.session.add(league)
    db.session.flush()
    db.session.add(LeagueMember(league_id=league.id, user_id=user.id))
    db.session.commit()
    return ok(league.to_dict(), 201)


@bp.post("/join")
@login_required
def join_league(user):
    """以邀請碼加入聯賽。"""
    data = request.get_json(silent=True) or {}
    code = (data.get("invite_code") or "").strip().upper()
    league = League.query.filter_by(invite_code=code).first()
    if league is None:
        return error("NOT_FOUND", "邀請碼無效", 404)
    exists = LeagueMember.query.filter_by(league_id=league.id, user_id=user.id).first()
    if exists:
        return error("ALREADY_MEMBER", "已是聯賽成員", 409)
    db.session.add(LeagueMember(league_id=league.id, user_id=user.id))
    db.session.commit()
    return ok(league.to_dict())


@bp.get("")
@login_required
def list_my_leagues(user):
    """目前使用者參加的所有聯賽。"""
    leagues = (
        League.query.join(LeagueMember)
        .filter(LeagueMember.user_id == user.id)
        .all()
    )
    return ok({"leagues": [lg.to_dict() for lg in leagues]})


@bp.get("/<int:league_id>")
def get_league(league_id):
    """聯賽詳情（含成員清單）。"""
    league = db.session.get(League, league_id)
    if league is None:
        return error("NOT_FOUND", "聯賽不存在", 404)
    return ok(league.to_dict(include_members=True))


@bp.get("/<int:league_id>/leaderboard")
def league_leaderboard(league_id):
    """私房聯賽排名（依積分；前三名獎牌，最後一名「輸家請客」）。"""
    league = db.session.get(League, league_id)
    if league is None:
        return error("NOT_FOUND", "聯賽不存在", 404)

    members = (
        db.session.query(User)
        .join(LeagueMember, LeagueMember.user_id == User.id)
        .filter(LeagueMember.league_id == league_id)
        .order_by(User.total_points.desc())
        .all()
    )
    medals = {1: "gold", 2: "silver", 3: "bronze"}
    last_rank = len(members)
    ranking = []
    for rank, u in enumerate(members, start=1):
        ranking.append({
            "rank": rank,
            "user": u.to_dict(),
            "points": u.total_points,
            "medal": medals.get(rank),
            "is_loser": rank == last_rank and last_rank > 1,  # 輸家請客
        })
    return ok({"league": league.to_dict(), "ranking": ranking})

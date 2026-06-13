"""排行榜 — 全站百大 / 冥燈榜（Redis 快取，DB fallback）。"""
from flask import Blueprint, request

from ..services import leaderboard
from ._helpers import ok

bp = Blueprint("leaderboard", __name__)


@bp.get("/global")
def global_top():
    """全站百大（高→低，前三名金銀銅）。Query: ?limit=100"""
    limit = request.args.get("limit", default=100, type=int)
    return ok({"ranking": leaderboard.top(limit=min(limit, 200))})


@bp.get("/loser")
def loser_board():
    """冥燈榜（積分最低 N 名）。Query: ?limit=10"""
    limit = request.args.get("limit", default=10, type=int)
    return ok({"ranking": leaderboard.losers(limit=min(limit, 100))})


@bp.post("/rebuild")
def rebuild():
    """從 DB 全量重建排行榜快取（維運用）。"""
    leaderboard.rebuild_cache()
    return ok({"status": "rebuilt"})

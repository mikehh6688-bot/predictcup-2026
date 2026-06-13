"""排行榜服務 — 以 Redis ZSET 快取使用者積分，DB 為真實來源（fallback）。

ZSET key: leaderboard:global
  member = user_id, score = total_points
全站百大 = ZREVRANGE（高→低）；冥燈榜 = ZRANGE（低→高）。
"""
from .. import extensions
from ..models import User

GLOBAL_KEY = "leaderboard:global"

# 名次 -> 獎牌（前三名）
_MEDALS = {1: "gold", 2: "silver", 3: "bronze"}


def _redis():
    return extensions.redis_client


def sync_user(user):
    """單一使用者積分變動後即時更新快取。"""
    r = _redis()
    if r is not None:
        r.zadd(GLOBAL_KEY, {str(user.id): user.total_points})


def rebuild_cache():
    """從 DB 全量重建排行榜快取（每日結算後或快取遺失時呼叫）。"""
    r = _redis()
    if r is None:
        return
    pipe = r.pipeline()
    pipe.delete(GLOBAL_KEY)
    mapping = {str(u.id): u.total_points for u in User.query.all()}
    if mapping:
        pipe.zadd(GLOBAL_KEY, mapping)
    pipe.execute()


def _hydrate(entries):
    """[(user_id, score), ...] -> 依名次組裝、補上 User 資料。"""
    ids = [int(uid) for uid, _ in entries]
    users = {u.id: u for u in User.query.filter(User.id.in_(ids)).all()} if ids else {}
    ranking = []
    for rank, (uid, score) in enumerate(entries, start=1):
        user = users.get(int(uid))
        if user is None:
            continue
        ranking.append({
            "rank": rank,
            "user": user.to_dict(),
            "points": int(score),
            "medal": _MEDALS.get(rank),
        })
    return ranking


def top(limit=100):
    """全站百大（高→低）。Redis 優先，未命中則退回 DB。"""
    r = _redis()
    if r is not None and r.exists(GLOBAL_KEY):
        entries = r.zrevrange(GLOBAL_KEY, 0, limit - 1, withscores=True)
        return _hydrate(entries)
    # Fallback：DB 直查
    users = User.query.order_by(User.total_points.desc()).limit(limit).all()
    return _hydrate([(str(u.id), u.total_points) for u in users])


def losers(limit=10):
    """冥燈榜（低→高）。"""
    r = _redis()
    if r is not None and r.exists(GLOBAL_KEY):
        entries = r.zrange(GLOBAL_KEY, 0, limit - 1, withscores=True)
        return _hydrate(entries)
    users = User.query.order_by(User.total_points.asc()).limit(limit).all()
    return _hydrate([(str(u.id), u.total_points) for u in users])

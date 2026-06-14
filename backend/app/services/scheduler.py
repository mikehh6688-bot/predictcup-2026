"""排程器 — Cron 自動結算與賽果同步（APScheduler）。

於 SCHEDULER_ENABLED=true 時由 app factory 啟動。兩個週期性工作：
  1. auto_settle    ：結算「已填賽果但尚未結算」的賽事（賽果可能來自手動或同步）。
  2. sync_results   ：呼叫第三方賽事 API 抓取賽果並回寫（需 SPORTS_API_KEY）。

並發安全：以 Redis 分散式鎖（SET NX EX）確保「同一時間只有一個 worker/行程」
執行每個工作，避免多 worker 重複結算。無 Redis 時退回單機假設直接執行。
"""
import logging
import socket
import uuid

from ..extensions import db
from .. import extensions
from ..models import Match
from ..constants import MatchStatus
from . import settlement, sync_service

log = logging.getLogger(__name__)
_scheduler = None
_OWNER = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


def _with_lock(name, ttl_seconds, fn):
    """取得 Redis 鎖才執行 fn；取不到（他人持有）則略過。無 Redis 則直接執行。"""
    r = extensions.redis_client
    if r is None:
        return fn()
    key = f"lock:scheduler:{name}"
    if not r.set(key, _OWNER, nx=True, ex=ttl_seconds):
        log.debug("scheduler job %s 已由其他行程執行，略過", name)
        return None
    try:
        return fn()
    finally:
        # 僅在仍持有時釋放（避免誤刪他人的鎖）
        if r.get(key) == _OWNER:
            r.delete(key)


def auto_settle(app):
    """結算所有已填賽果（home/away_score 非空）但狀態尚未 finished 的賽事。"""
    with app.app_context():
        pending = (
            Match.query.filter(
                Match.status != MatchStatus.FINISHED,
                Match.home_score.isnot(None),
                Match.away_score.isnot(None),
            ).all()
        )
        done = 0
        for match in pending:
            try:
                settlement.settle_match(match)
                done += 1
            except settlement.SettlementError:
                db.session.rollback()  # 例如淘汰賽缺 advancing_team，留待補齊
        if done:
            log.info("auto_settle: 結算 %d 場賽事", done)


def sync_results(app):
    """自動同步最新賽果（API-Football 或維基爬蟲）。"""
    with app.app_context():
        try:
            stats = sync_service.auto_sync()
        except Exception as e:  # 外部來源不穩定，不讓排程崩潰
            log.warning("auto_sync 失敗：%s", e)
            return
        if stats.get("settled") or stats.get("updated"):
            log.info("auto_sync: %s", stats)


def init_scheduler(app):
    """依設定啟動背景排程。重複呼叫安全（僅啟動一次）。"""
    global _scheduler
    if not app.config.get("SCHEDULER_ENABLED") or _scheduler is not None:
        return

    from apscheduler.schedulers.background import BackgroundScheduler

    settle_min = app.config["SETTLE_INTERVAL_MINUTES"]
    sync_min = app.config["RESULT_SYNC_INTERVAL_MINUTES"]
    # 鎖存活時間略短於間隔，確保下次執行前釋放
    settle_ttl = max(30, settle_min * 60 - 10)
    sync_ttl = max(30, sync_min * 60 - 10)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        lambda: _with_lock("auto_settle", settle_ttl, lambda: auto_settle(app)),
        "interval", minutes=settle_min, id="auto_settle",
    )
    _scheduler.add_job(
        lambda: _with_lock("sync_results", sync_ttl, lambda: sync_results(app)),
        "interval", minutes=sync_min, id="sync_results",
    )
    _scheduler.start()
    log.info("排程器已啟動（結算每 %d 分、同步每 %d 分）",
             app.config["SETTLE_INTERVAL_MINUTES"],
             app.config["RESULT_SYNC_INTERVAL_MINUTES"])

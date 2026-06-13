"""排程器 — Cron 自動結算與賽果同步（APScheduler）。

於 SCHEDULER_ENABLED=true 時由 app factory 啟動。兩個週期性工作：
  1. auto_settle    ：結算「已填賽果但尚未結算」的賽事（賽果可能來自手動或同步）。
  2. sync_results   ：呼叫第三方賽事 API 抓取賽果並回寫（需 SPORTS_API_KEY）。

注意：以行程內 BackgroundScheduler 實作，適合單一 worker。多 worker 部署時
應改用獨立排程行程（如 APScheduler + Redis lock，或外部 cron 觸發 endpoint），
避免重複結算。
"""
import logging

from ..extensions import db
from ..models import Match
from ..constants import MatchStatus
from . import settlement, sports_api

log = logging.getLogger(__name__)
_scheduler = None


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
    """從第三方 API 同步當日賽果。"""
    with app.app_context():
        if not app.config.get("SPORTS_API_KEY"):
            return
        stats = sports_api.sync_results()
        if stats["synced"]:
            log.info("sync_results: %s", stats)


def init_scheduler(app):
    """依設定啟動背景排程。重複呼叫安全（僅啟動一次）。"""
    global _scheduler
    if not app.config.get("SCHEDULER_ENABLED") or _scheduler is not None:
        return

    from apscheduler.schedulers.background import BackgroundScheduler

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        lambda: auto_settle(app), "interval",
        minutes=app.config["SETTLE_INTERVAL_MINUTES"], id="auto_settle",
    )
    _scheduler.add_job(
        lambda: sync_results(app), "interval",
        minutes=app.config["RESULT_SYNC_INTERVAL_MINUTES"], id="sync_results",
    )
    _scheduler.start()
    log.info("排程器已啟動（結算每 %d 分、同步每 %d 分）",
             app.config["SETTLE_INTERVAL_MINUTES"],
             app.config["RESULT_SYNC_INTERVAL_MINUTES"])

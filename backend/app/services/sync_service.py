"""賽果自動同步協調器 —— 依設定選擇資料來源。

優先序：
  1. SPORTS_API_KEY 有設 → API-Football（結構化、含淘汰賽晉級，最穩）
  2. 否則 → 維基百科爬蟲（免金鑰，賽事期間即時，best-effort）

兩者都透過可重入的 settle_match 重新結算，因此可安全重複執行。
"""
from flask import current_app


def auto_sync():
    if current_app.config.get("SPORTS_API_KEY"):
        from . import sports_api
        return {"source": "api-football", **sports_api.import_fixtures()}
    from . import wiki_provider
    return {"source": "wikipedia", **wiki_provider.sync()}

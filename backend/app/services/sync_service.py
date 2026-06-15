"""賽果自動同步協調器 —— 依設定選擇資料來源。

優先序：
  1. SPORTS_API_KEY 有設 → API-Football（結構化、含淘汰賽晉級，最穩）
  2. 否則 → 維基百科爬蟲（免金鑰，賽事期間即時，best-effort）

兩者都透過可重入的 settle_match 重新結算，因此可安全重複執行。
"""
from flask import current_app


def auto_sync():
    from . import ai_predictor

    if current_app.config.get("SPORTS_API_KEY"):
        from . import sports_api
        result = {"source": "api-football", **sports_api.import_fixtures()}
    else:
        from . import wiki_provider
        result = {"source": "wikipedia", **wiki_provider.sync()}

    # 為新匯入 / 尚無預測的賽事自動補上 AI 勝率（只處理缺漏，可重複執行）
    result["ai_generated"] = ai_predictor.generate_missing()
    return result

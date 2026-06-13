"""AI 微服務 — 以 Claude 產生賽事勝率預測與賽況分析。

設計：
  * predict_match()：純預測，呼叫 Claude（claude-opus-4-8）以「結構化輸出」
    回傳 home/draw/away 勝率與一段中文賽況分析。無 ANTHROPIC_API_KEY 時
    退回確定性啟發式（heuristic），讓本地/CI 也能運作。
  * crowd_sentiment_from_bets()：以系統內實際下注比例作為「網民風向」近似值
    （未來可改接外部爬蟲聲量）。
  * generate_for_match()：組合上述兩者寫入 Match 的預留欄位並 commit。
"""
import hashlib
import json

from flask import current_app

from ..extensions import db
from ..models import Bet
from ..constants import BetChoice


# 結構化輸出 schema（structured outputs 不支援數值 min/max，故僅約束型別）
_SCHEMA = {
    "type": "object",
    "properties": {
        "home_win_prob": {"type": "number"},
        "draw_prob": {"type": "number"},
        "away_win_prob": {"type": "number"},
        "analysis": {"type": "string"},
    },
    "required": ["home_win_prob", "draw_prob", "away_win_prob", "analysis"],
    "additionalProperties": False,
}


def _normalize(h, d, a):
    """將三個機率正規化為總和 1。"""
    total = (h or 0) + (d or 0) + (a or 0)
    if total <= 0:
        return 0.4, 0.25, 0.35
    return round(h / total, 3), round(d / total, 3), round(a / total, 3)


def _heuristic(home_team, away_team, stage_label):
    """無 LLM 時的確定性後援：以隊名雜湊產生穩定但有差異的機率。"""
    seed = int(hashlib.md5(f"{home_team}|{away_team}".encode()).hexdigest(), 16)
    home_edge = 0.40 + (seed % 18) / 100          # 0.40 ~ 0.57（含主場優勢）
    draw = 0.22 + ((seed >> 8) % 10) / 100         # 0.22 ~ 0.31
    away = max(0.15, 1 - home_edge - draw)
    h, d, a = _normalize(home_edge, draw, away)
    analysis = (
        f"（離線估算）{home_team} 主場略佔優，預期與 {away_team} 在{stage_label}"
        f"形成拉鋸；勝負可能取決於臨場狀態與定位球。"
    )
    return {"home_win_prob": h, "draw_prob": d, "away_win_prob": a, "analysis": analysis}


def predict_match(home_team, away_team, stage_label):
    """回傳 {home_win_prob, draw_prob, away_win_prob, analysis}。"""
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _heuristic(home_team, away_team, stage_label)

    import anthropic  # 延後匯入

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        f"你是足球賽事分析師。請評估這場 2026 世界盃{stage_label}：\n"
        f"主隊：{home_team}\n客隊：{away_team}\n"
        f"請給出主勝 / 和局 / 客勝的機率（0~1，總和約等於 1），"
        f"並用繁體中文寫一段 60 字內、具體的賽況分析。"
    )
    try:
        resp = client.messages.create(
            model=current_app.config.get("AI_MODEL", "claude-opus-4-8"),
            max_tokens=1024,
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(b.text for b in resp.content if b.type == "text")
        data = json.loads(text)
    except Exception:
        # LLM 失敗時不阻斷流程，退回啟發式
        return _heuristic(home_team, away_team, stage_label)

    h, d, a = _normalize(
        data.get("home_win_prob"), data.get("draw_prob"), data.get("away_win_prob")
    )
    return {
        "home_win_prob": h, "draw_prob": d, "away_win_prob": a,
        "analysis": data.get("analysis", ""),
    }


def crowd_sentiment_from_bets(match_id):
    """以系統內下注比例近似「網民風向」。無下注時回傳 None。"""
    rows = (
        db.session.query(Bet.predicted_result, db.func.count(Bet.id))
        .filter_by(match_id=match_id)
        .group_by(Bet.predicted_result)
        .all()
    )
    counts = {c: 0 for c in BetChoice}
    for choice, n in rows:
        counts[choice] = n
    total = sum(counts.values())
    if total == 0:
        return None
    return {
        "home": round(counts[BetChoice.HOME] / total, 3),
        "draw": round(counts[BetChoice.DRAW] / total, 3),
        "away": round(counts[BetChoice.AWAY] / total, 3),
    }


def generate_for_match(match, stage_label):
    """產生 AI 預測 + 網民風向並寫入 match（呼叫端負責 commit 或交由此處）。"""
    pred = predict_match(match.home_team, match.away_team, stage_label)
    match.ai_home_win_prob = pred["home_win_prob"]
    match.ai_draw_prob = pred["draw_prob"]
    match.ai_away_win_prob = pred["away_win_prob"]
    match.ai_analysis = pred["analysis"]

    sentiment = crowd_sentiment_from_bets(match.id)
    if sentiment:
        match.public_home_pct = sentiment["home"]
        match.public_draw_pct = sentiment["draw"]
        match.public_away_pct = sentiment["away"]

    db.session.commit()
    return pred

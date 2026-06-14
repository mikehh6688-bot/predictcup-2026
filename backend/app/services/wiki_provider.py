"""維基百科賽果同步（免金鑰後援來源）。

從各組維基頁面解析「已踢完」的比分（football box：.fhome/.fscore/.faway），
對應本地賽事、更新比分並重新結算（可重入）。淘汰賽頁面結構相同，待頁面
建立後可沿用。屬 best-effort：解析失敗的賽事略過，不阻斷整體流程。
"""
import re

from ..extensions import db
from ..models import Match
from ..constants import MatchStatus, MatchStage
from .wc_data import WIKI_GROUP_PAGES, zh_name
from . import settlement

_WIKI_API = "https://en.wikipedia.org/w/api.php"
_SCORE_RE = re.compile(r"^(\d+)\s*[–-]\s*(\d+)$")  # "2–0"（en-dash 或 hyphen）


def _fetch_page_html(page):
    import requests

    resp = requests.get(
        _WIKI_API,
        params={"action": "parse", "page": page, "prop": "text", "format": "json"},
        headers={"User-Agent": "PredictCup2026/1.0 (sync)"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["text"]["*"]


def _parse_results(html):
    """回傳已踢完的 [(home_en, away_en, home_score, away_score), ...]。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    homes = soup.select(".fhome")
    scores = soup.select(".fscore")
    aways = soup.select(".faway")
    out = []
    for h, s, a in zip(homes, scores, aways):
        m = _SCORE_RE.match(s.get_text(strip=True))
        if not m:  # 未踢完者顯示 "Match NN"
            continue
        out.append((
            h.get_text(" ", strip=True),
            a.get_text(" ", strip=True),
            int(m.group(1)),
            int(m.group(2)),
        ))
    return out


def sync():
    """掃描各組頁面，更新已踢完賽事的比分並重新結算。"""
    updated = settled = 0
    for page in WIKI_GROUP_PAGES:
        try:
            results = _parse_results(_fetch_page_html(page))
        except Exception:
            continue  # 單頁失敗不影響其他組

        for home_en, away_en, hs, as_ in results:
            match = Match.query.filter_by(
                home_team=zh_name(home_en), away_team=zh_name(away_en),
                stage=MatchStage.GROUP,
            ).first()
            if match is None:
                continue
            # 已是相同賽果則略過，避免無謂重算
            if (match.status == MatchStatus.FINISHED
                    and match.home_score == hs and match.away_score == as_):
                continue
            match.home_score = hs
            match.away_score = as_
            updated += 1
            try:
                settlement.settle_match(match)  # 可重入，含 commit
                settled += 1
            except settlement.SettlementError:
                db.session.rollback()
    return {"updated": updated, "settled": settled}

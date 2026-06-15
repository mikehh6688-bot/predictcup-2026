"""端對端整合測試（SQLite in-memory、停用 Redis）。

驗證 Phase 2 核心流程：
  登入 → 建賽事 → 下注(扣道具) → 取消(退道具) → 重新下注 → 結算 → 積分更新 → 排行榜

需先安裝相依：
  cd backend && pip install -r requirements.txt
執行：
  cd backend && python -m pytest tests/test_api.py -v
"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402


@pytest.fixture
def client():
    app = create_app(overrides={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "REDIS_URL": None,            # 停用 Redis → 排行榜走 DB fallback
    })
    with app.app_context():
        db.create_all()
        with app.test_client() as c:
            yield c
        db.drop_all()


def _login(client, username):
    r = client.post("/api/v1/auth/sso", json={"provider": "dev", "username": username})
    body = r.get_json()
    return body["token"], body["user"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _admin(client):
    """以管理者（username 'Mike' 命中預設名單）登入，回傳 auth headers。"""
    token, _ = _login(client, "Mike")
    return _auth(token)


def _create_match(client, stage="group", kickoff_in_hours=24):
    kickoff = (datetime.utcnow() + timedelta(hours=kickoff_in_hours)).isoformat()
    r = client.post("/api/v1/matches", headers=_admin(client), json={
        "home_team": "Brazil", "away_team": "Argentina",
        "home_team_code": "BRA", "away_team_code": "ARG",
        "kickoff_time": kickoff, "stage": stage,
    })
    return r.get_json()


def test_new_user_defaults(client):
    _, user = _login(client, "mike")
    assert user["total_points"] == 100
    assert user["double_cards"] == 3
    assert user["insurance_cards"] == 1


def test_create_match_auto_multiplier(client):
    m = _create_match(client, stage="semi_final")
    assert m["multiplier"] == 5
    assert m["status"] == "scheduled"


def test_item_conflict_rejected(client):
    token, user = _login(client, "mike")
    m = _create_match(client)
    r = client.post("/api/v1/bets", headers=_auth(token), json={
        "match_id": m["id"], "predicted_result": "home",
        "use_double_card": True, "use_insurance_card": True,
    })
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "ITEM_CONFLICT"


def test_bet_deducts_and_cancel_refunds_item(client):
    token, user = _login(client, "mike")
    m = _create_match(client)
    # 下注用 1 張翻倍卡
    r = client.post("/api/v1/bets", headers=_auth(token), json={
        "match_id": m["id"], "predicted_result": "home", "use_double_card": True,
    })
    assert r.status_code == 201
    bet_id = r.get_json()["id"]
    inv = client.get(f"/api/v1/users/{user['id']}/inventory").get_json()
    assert inv["double_cards"] == 2          # 3 → 2（已扣）

    # 取消 → 退還
    r = client.delete(f"/api/v1/bets/{bet_id}", headers=_auth(token))
    assert r.status_code == 204
    inv = client.get(f"/api/v1/users/{user['id']}/inventory").get_json()
    assert inv["double_cards"] == 3          # 退回


def test_full_settlement_flow_updates_points(client):
    token, user = _login(client, "mike")
    m = _create_match(client, stage="group")
    # 猜主勝 + 精準 2:1
    client.post("/api/v1/bets", headers=_auth(token), json={
        "match_id": m["id"], "predicted_result": "home",
        "predicted_home_score": 2, "predicted_away_score": 1,
    })
    # 賽果 2:1 主勝 → 基礎 +2（勝隊進球）+ 精準 50 = 52
    r = client.patch(f"/api/v1/matches/{m['id']}/result", headers=_admin(client),
                     json={"home_score": 2, "away_score": 1})
    assert r.status_code == 200
    assert r.get_json()["settlement"]["settled"] == 1

    me = client.get("/api/v1/auth/me", headers=_auth(token)).get_json()
    assert me["total_points"] == 100 + 52


def test_duplicate_bet_rejected(client):
    token, _ = _login(client, "mike")
    m = _create_match(client)
    payload = {"match_id": m["id"], "predicted_result": "home"}
    client.post("/api/v1/bets", headers=_auth(token), json=payload)
    r = client.post("/api/v1/bets", headers=_auth(token), json=payload)
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "DUPLICATE_BET"


def test_league_create_join_and_leaderboard(client):
    t1, u1 = _login(client, "mike")
    t2, u2 = _login(client, "john")
    # mike 建聯賽
    lg = client.post("/api/v1/leagues", headers=_auth(t1),
                     json={"name": "KMC 大賽"}).get_json()
    # john 加入
    r = client.post("/api/v1/leagues/join", headers=_auth(t2),
                    json={"invite_code": lg["invite_code"]})
    assert r.status_code == 200

    board = client.get(f"/api/v1/leagues/{lg['id']}/leaderboard").get_json()
    assert len(board["ranking"]) == 2
    assert board["ranking"][-1]["is_loser"] is True   # 最後一名輸家請客


def test_global_leaderboard_fallback(client):
    _login(client, "mike")
    r = client.get("/api/v1/leaderboard/global")
    assert r.status_code == 200
    assert len(r.get_json()["ranking"]) >= 1


# --- Phase 5 ---------------------------------------------------------------- #
def test_jwt_login_grants_access(client):
    token, _ = _login(client, "mike")
    # 帶 JWT 可存取 /me
    me = client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    # 無 token 被擋
    assert client.get("/api/v1/auth/me").status_code == 401


def test_ai_generate_heuristic_fallback(client):
    # 無 ANTHROPIC_API_KEY → 走啟發式，機率總和約等於 1
    m = _create_match(client)
    r = client.post(f"/api/v1/matches/{m['id']}/ai-generate", headers=_admin(client))
    assert r.status_code == 200
    p = r.get_json()["prediction"]
    total = p["home_win_prob"] + p["draw_prob"] + p["away_win_prob"]
    assert abs(total - 1.0) < 0.02
    assert p["analysis"]


def test_resettle_reverses_and_reapplies(client):
    # 可重入結算：修正賽果後分數正確重算（先反轉舊分再套新分）
    token, _ = _login(client, "mike")
    m = _create_match(client, stage="group")
    client.post("/api/v1/bets", headers=_auth(token),
                json={"match_id": m["id"], "predicted_result": "home"})
    # 主勝 2:1 → 猜中得 +2 → 102
    client.patch(f"/api/v1/matches/{m['id']}/result", headers=_admin(client),
                 json={"home_score": 2, "away_score": 1})
    me = client.get("/api/v1/auth/me", headers=_auth(token)).get_json()
    assert me["total_points"] == 102

    # 修正為客勝 0:2 → 反轉 +2、改判猜錯扣 2 → 100 - 2 = 98
    r = client.patch(f"/api/v1/matches/{m['id']}/result", headers=_admin(client),
                     json={"home_score": 0, "away_score": 2})
    assert r.status_code == 200
    assert r.get_json()["settlement"]["resettled"] == 1
    me = client.get("/api/v1/auth/me", headers=_auth(token)).get_json()
    assert me["total_points"] == 98


def test_import_fixtures_no_key_is_safe(client):
    # 無 SPORTS_API_KEY → 安全回傳 0，不丟錯
    r = client.post("/api/v1/matches/import-fixtures", headers=_admin(client))
    assert r.status_code == 200
    body = r.get_json()
    assert body["imported"] == 0 and body["settled"] == 0


def test_mike_is_admin(client):
    # username 命中預設管理者名單 → is_admin
    _, mike = _login(client, "Mike")
    assert mike["is_admin"] is True
    _, john = _login(client, "john")
    assert john["is_admin"] is False


def test_admin_endpoints_reject_non_admin(client):
    token, _ = _login(client, "john")  # 非管理者
    # 未帶 token → 401
    assert client.post("/api/v1/matches/auto-sync").status_code == 401
    # 非管理者 → 403
    r = client.post("/api/v1/matches/auto-sync", headers=_auth(token))
    assert r.status_code == 403
    assert r.get_json()["error"]["code"] == "FORBIDDEN"


# --- 🟠 production batch ---------------------------------------------------- #
def test_r32_stage_multiplier(client):
    m = _create_match(client, stage="round_of_32")
    assert m["stage"] == "round_of_32"
    assert m["multiplier"] == 2


def test_readiness_probe(client):
    # 測試環境停用 Redis → 只檢查 DB，應 ready
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ready" and body["checks"]["db"] is True


def test_audit_log_records_admin_action(client):
    admin = _admin(client)
    m = _create_match(client)  # create_match 會寫一筆稽核
    client.patch(f"/api/v1/matches/{m['id']}/result", headers=admin,
                 json={"home_score": 1, "away_score": 0})
    r = client.get("/api/v1/matches/audit", headers=admin)
    assert r.status_code == 200
    actions = [log["action"] for log in r.get_json()["logs"]]
    assert "update_result" in actions and "create_match" in actions
    # 非管理者不可看稽核
    t, _ = _login(client, "john")
    assert client.get("/api/v1/matches/audit", headers=_auth(t)).status_code == 403

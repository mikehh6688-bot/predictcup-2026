# PredictCup 2026 — Backend (Flask)

世界盃賽事預測系統後端：核心運算、API、結算排程，並預留 LLM / AI Agent 整合空間。

## 技術棧
- **Flask 3** + Flask-SQLAlchemy + Flask-Migrate
- **PostgreSQL**（關聯式主資料）+ **Redis**（排行榜快取）
- Flask-CORS（供 Next.js 前端跨域）

## 專案結構
```
backend/
├── run.py                 # 進入點（python run.py → :5001）
├── config.py              # 多環境設定 + 業務常數
├── requirements.txt
├── .env.example           # 複製成 .env 後填值
├── API_DESIGN.md          # ⭐ RESTful 路由表 + 結算規則
└── app/
    ├── __init__.py        # Application Factory
    ├── extensions.py      # db / migrate / redis 實例
    ├── models.py          # ⭐ SQLAlchemy Models（5 張表）
    └── api/               # Blueprints（Phase 1 為骨架，回 501）
        ├── auth.py        # SSO 登入
        ├── users.py       # 使用者 / 道具
        ├── matches.py     # 賽事 / 戰情儀表板
        ├── bets.py        # 投注引擎
        ├── leagues.py     # 私房聯賽
        └── leaderboard.py # 全站 / 冥燈榜
```

## 資料表（models.py）
| Model | 說明 | 重點欄位 |
|-------|------|----------|
| `User` | 使用者 | `total_points`(100)、`double_cards`(3)、`insurance_cards`(1) |
| `Match` | 賽事 | `status`/`stage`/`multiplier`、`home/away_score`、AI 勝率 & 網民風向預留欄位 |
| `Bet` | 注單 | `predicted_result`、精準比分、`use_double/insurance_card`、結算結果 |
| `League` | 私房聯賽 | `invite_code`（自動產生） |
| `LeagueMember` | 聯賽成員 | `(league_id, user_id)` 唯一 |

## 本地啟動
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # 填入 DATABASE_URL / REDIS_URL

# 建立資料庫 schema
flask db init && flask db migrate -m "init" && flask db upgrade

python run.py                   # http://localhost:5001/health
```

## 測試
```bash
# 純結算邏輯（無需相依，可直接跑）
python tests/test_scoring.py

# 完整流程（需先 pip install）— SQLite in-memory + 停用 Redis
python -m pytest tests/ -v
```
涵蓋：道具互斥、下注扣除/取消退還、結算積分、精準紅利、聯賽輸家請客、排行榜 fallback。

## 服務分層
| 層 | 檔案 | 職責 |
|----|------|------|
| 純運算 | `services/scoring.py` | 單注結算計算（無副作用，可單測） |
| 副作用 | `services/settlement.py` | 套用結算至 DB＋更新積分＋刷新排行榜 |
| 投注 | `services/betting.py` | 下注/改注/取消＋道具扣退＋鎖盤驗證 |
| 快取 | `services/leaderboard.py` | Redis ZSET 排行榜（DB fallback） |
| 身分 | `services/auth.py` | JWT 簽發/驗證 + Google SSO 核對（dev 後援） |
| AI | `services/ai_predictor.py` | Claude 勝率預測（無 key 走啟發式）+ 網民風向 |
| 整合 | `services/sports_api.py` | 第三方賽果同步（API-Football） |
| 排程 | `services/scheduler.py` | APScheduler：自動結算 + 賽果同步 |

> **身分**：登入回傳 **JWT**，請求帶 `Authorization: Bearer <jwt>`。
> SSO 支援 `provider: "google"`（驗 id_token）與 `provider: "dev"`（暱稱登入，`ALLOW_DEV_LOGIN`）。

## 開發階段
- **Phase 1 ✅** 資料庫 Models + API 路由骨架
- **Phase 2 ✅** 結算核心邏輯（投注引擎、賽果結算、Redis 排行榜）
- **Phase 5 ✅** 真實 SSO/JWT、Claude AI 微服務、Cron 自動結算 + 賽事 API、Docker 部署
  - 部署見根目錄 [DEPLOY.md](../DEPLOY.md)；25 個測試全綠

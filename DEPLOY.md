# PredictCup 2026 — 部署指南

## 架構
```
                ┌────────────┐      ┌──────────────────────────┐
  瀏覽器 ──────▶│ Next.js    │────▶│ Flask API (/api/v1)       │
  (Mobile)      │ Vercel/    │ JWT │  ├ 結算引擎               │
                │ Docker     │     │  ├ AI 微服務 (Claude)     │
                └────────────┘     │  └ 排程 (自動結算/同步)    │
                                   └──────┬─────────────┬──────┘
                                          ▼             ▼
                                    PostgreSQL        Redis
```

## 一鍵本地 / 單機（Docker Compose）
```bash
# 於專案根目錄
cp .env.deploy.example .env          # 填入密鑰（選填 SSO/AI/賽事 key）
docker compose up --build
# 前端 http://localhost:3000 · 後端 http://localhost:5001/health
```
Compose 會起 Postgres + Redis + 後端（gunicorn，單 worker + 排程器）+ 前端。

> 初次啟動會自動 `db.create_all()` 建表（見 `backend/entrypoint.sh`）。
> 要灌入範例資料：`docker compose exec backend python seed.py`（注意 seed 會 drop_all）。

## 雲端部署（建議）
### 前端 → Vercel
1. 將 repo 連到 Vercel，Root Directory 設為 `frontend/`
2. 環境變數 `NEXT_PUBLIC_API_BASE = https://<your-api-domain>/api/v1`
3. Vercel 自動偵測 Next.js 並建置（全球 CDN + 自動擴展）

### 後端 → 任一容器平台（Railway / Render / Fly.io / Cloud Run）
- 用 `backend/Dockerfile`
- 掛載 Managed PostgreSQL 與 Redis，設定對應 `DATABASE_URL` / `REDIS_URL`
- 必填環境變數見下表

## 環境變數
| 變數 | 用途 | 正式環境 |
|------|------|------|
| `FLASK_ENV` | 設為 `production` 啟用前置安全檢查 | ✅ `production` |
| `DATABASE_URL` | **託管** PostgreSQL 連線（含備份） | ✅ |
| `REDIS_URL` | 排行榜快取 + 排程器分散式鎖 | ✅ |
| `SECRET_KEY` / `JWT_SECRET` | Flask / JWT 簽章密鑰 | ✅ 強隨機（用預設值會拒絕啟動）|
| `GOOGLE_CLIENT_ID` | Google 登入 audience（正式必填） | ✅ |
| `CORS_ORIGINS` | 允許來源（逗號分隔，**不可為 `*`**） | ✅ 前端網域 |
| `ALLOW_DEV_LOGIN` | 暱稱直登；正式預設 **false** | 保持 false |
| `ANTHROPIC_API_KEY` | Claude 勝率預測（缺省走啟發式）| AI 時 |
| `SPORTS_API_KEY` | API-Football 賽果同步 | 自動同步時 |
| `SCHEDULER_ENABLED` | 啟用 Cron 自動結算/同步 | 視部署 |
| `GUNICORN_WORKERS` | gunicorn worker 數 | 否 |

> **正式環境啟動前置檢查**：`FLASK_ENV=production` 時，若 `SECRET_KEY`/`JWT_SECRET`
> 仍為預設、未設 `GOOGLE_CLIENT_ID`、或 `CORS_ORIGINS` 為空/`*`，**應用會拒絕啟動**
> 並列出原因（見 `config.py` 的 `ProductionConfig.validate()`）。

## 資料庫 Migration
schema 由 Alembic / Flask-Migrate 管理；容器啟動時 `entrypoint.sh` 自動執行
`flask db upgrade`（冪等）。日後改 schema：
```bash
cd backend && FLASK_APP=run.py flask db migrate -m "描述"   # 產生 migration
# 檢視 migrations/versions/ 後，部署時自動 upgrade
```

## ⚠️ 多 worker 與排程器
排程器是行程內 `BackgroundScheduler`，但每個工作都以 **Redis 分散式鎖**
（`SET NX EX`）保護 → 即使多 worker 同時觸發，同一時間也只有一個會執行，
不會重複結算。仍建議：高負載時把排程獨立成單一行程，或關內建改用平台 cron
打 `POST /api/v1/matches/auto-sync`（需管理者 JWT）。

## 正式環境檢查清單（🔴 已內建強制）
- [x] `SECRET_KEY` / `JWT_SECRET` 強隨機 — 啟動檢查強制
- [x] `ALLOW_DEV_LOGIN=false` — 正式預設關閉
- [x] Google 登入強制驗 `iss` / `aud` / `email_verified`
- [x] CORS 收斂為前端網域 — 啟動檢查強制
- [x] migration（`flask db upgrade`）取代 `create_all`
- [x] 排程器以 Redis 鎖避免多 worker 重複結算
- [ ] 託管 PostgreSQL / Redis 並開啟自動備份（基礎設施層，依平台設定）

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
| 變數 | 用途 | 必填 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 連線 | ✅ |
| `REDIS_URL` | 排行榜快取 | ✅ |
| `SECRET_KEY` / `JWT_SECRET` | Flask / JWT 簽章密鑰 | ✅（正式務必更換）|
| `GOOGLE_CLIENT_ID` | 驗證 Google id_token audience | SSO 時 |
| `ALLOW_DEV_LOGIN` | 是否允許暱稱直接登入（預設 true）| 正式建議 `false` |
| `ANTHROPIC_API_KEY` | Claude 勝率預測（缺省走啟發式）| AI 時 |
| `AI_MODEL` | 預設 `claude-opus-4-8` | 否 |
| `SPORTS_API_KEY` | 第三方賽果同步（API-Football）| 自動同步時 |
| `SCHEDULER_ENABLED` | 啟用 Cron 自動結算/同步 | 否 |
| `GUNICORN_WORKERS` | gunicorn worker 數 | 否 |

## ⚠️ 多 worker 與排程器
排程器是**行程內** `BackgroundScheduler`，多個 gunicorn worker 會各自跑一份 →
重複結算風險。正式環境二擇一：
1. 跑 API 用多 worker、`SCHEDULER_ENABLED=false`，另起一個**單一**排程行程
   （同映像、`SCHEDULER_ENABLED=true`、不開 web）。
2. 關閉內建排程，改用平台 cron 定時打 `POST /api/v1/matches/sync-results`。

## 正式環境檢查清單
- [ ] 更換 `SECRET_KEY` / `JWT_SECRET` 為強隨機值
- [ ] `ALLOW_DEV_LOGIN=false`，改用真實 Google SSO
- [ ] CORS 收斂為前端網域（目前 `CORS(app)` 為全開，見 `app/__init__.py`）
- [ ] 以 migration（`flask db`）取代 `create_all`
- [ ] 排程器只在單一行程啟用

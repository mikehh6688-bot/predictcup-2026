# 🚀 PredictCup 2026 — 上線當天操作手冊

照順序執行即可。每步都附「怎麼做」與「怎麼驗證」。預估 1.5–2 小時。

> 設計上有**防呆**：正式環境若密鑰/Google/CORS 沒設好，後端會**拒絕啟動**並印出原因
> （見 `config.py` 的 `ProductionConfig.validate()`），所以「忘了設定就上線」會被擋下。

---

## 0. 前置帳號（先準備好）
- [ ] GitHub repo（已推上，含 `deploy.yml`）
- [ ] 容器平台帳號（擇一）：Railway / Render / Fly.io / Cloud Run
- [ ] Vercel 帳號（前端）
- [ ] Google Cloud 專案（OAuth）
- [ ] Sentry 帳號（錯誤追蹤，選用）
- [ ] 網域（前端 `app.例.com`、後端 `api.例.com`）

---

## 1. 託管資料庫 + Redis（開備份）
1. 在平台開 **Managed PostgreSQL 14+**，記下連線字串 → `DATABASE_URL`
   - ✅ **開啟自動每日備份 + PITR**（這步最容易被忘，務必確認）
2. 開 **Managed Redis**，記下 → `REDIS_URL`
3. 驗證：用 `psql "$DATABASE_URL" -c '\l'`、`redis-cli -u "$REDIS_URL" ping` 能通

> Schema 不用手動建 —— 後端容器啟動時 `entrypoint.sh` 會自動跑 `flask db upgrade`。

---

## 2. Google OAuth Client（取得 GOOGLE_CLIENT_ID）
1. Google Cloud Console → **APIs & Services → Credentials → Create OAuth client ID**
2. Application type：**Web application**
3. **Authorized JavaScript origins** 填前端網域：`https://app.例.com`（本機測試可加 `http://localhost:3000`）
4. 建立後複製 **Client ID**（形如 `xxxxx.apps.googleusercontent.com`）
   - 前後端要用**同一個** Client ID
   - 後端 → `GOOGLE_CLIENT_ID`（驗 id_token 的 `aud`）
   - 前端 → `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
5. OAuth consent screen 設為 External / 填基本資訊（測試期可 Testing 模式加白名單）

> Mike 用 `mike.hsieh72@gmail.com` 登入會**自動成為管理者**（`ADMIN_EMAILS` 預設值）。
> 要換管理者就設 `ADMIN_EMAILS=你的@gmail.com`（逗號分隔可多人）。

---

## 3. Sentry 專案（選用，取得 DSN）
1. Sentry → 建 Project（Python / Flask）→ 複製 **DSN** → `SENTRY_DSN`
2. 不設也能上線（不啟用錯誤追蹤）

---

## 4. 產生密鑰
```bash
openssl rand -hex 32   # → SECRET_KEY
openssl rand -hex 32   # → JWT_SECRET（用不同的）
```
存進平台的 **Secret Manager**（別寫進 repo / 明文）。

---

## 5. 部署後端（容器平台）
1. 指向 repo 的 `backend/Dockerfile`（或用 CI 推到 GHCR 的映像，見 Step 7）
2. 設定環境變數（**最小必填集**）：
   ```
   FLASK_ENV=production
   SECRET_KEY=<step4>
   JWT_SECRET=<step4>
   GOOGLE_CLIENT_ID=<step2>
   CORS_ORIGINS=https://app.例.com        # 不可為空或 *
   DATABASE_URL=<step1>
   REDIS_URL=<step1>
   # 選用
   SENTRY_DSN=<step3>
   ANTHROPIC_API_KEY=sk-ant-...           # 真 Claude 預測（缺則啟發式）
   SPORTS_API_KEY=...                     # API-Football（缺則維基爬蟲）
   SCHEDULER_ENABLED=true                 # 見 Step 10
   GUNICORN_WORKERS=2
   ```
3. 部署 → 容器啟動時自動 `flask db upgrade` 建表
4. **驗證**：
   ```bash
   curl https://api.例.com/health   # {"status":"ok"}
   curl https://api.例.com/ready    # {"status":"ready","checks":{"db":true,"redis":true}}
   ```
   - 若 `/ready` 回 503 → DB 或 Redis 連線有問題，看 `checks` 哪個 false
   - 若容器**啟動就掛**並印「正式環境設定不安全，拒絕啟動」→ 照訊息補齊那幾個變數

---

## 6. 部署前端（Vercel）
1. Import repo，**Root Directory = `frontend`**
2. 環境變數（**Build-time**，改了要 redeploy）：
   ```
   NEXT_PUBLIC_API_BASE=https://api.例.com/api/v1
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=<step2>
   ```
3. Deploy → 綁定網域 `app.例.com`
4. **驗證**：開 `https://app.例.com` → 首頁載入、底部導覽列正常

---

## 7. 接上 CI/CD（選用但建議）
`deploy.yml` 已就緒：推 `main` 或打 `v*` tag → 自動 build & push 映像到 **GHCR**。
1. repo → Settings → Actions → 確認 workflow 權限可寫 packages
2. 設 repo variable `NEXT_PUBLIC_API_BASE`（前端映像編譯期用）
3. 接平台部署：在 `deploy.yml` 最後的 `deploy` job 填平台 hook，例如
   ```yaml
   env:
     RENDER_DEPLOY_HOOK: ${{ secrets.RENDER_DEPLOY_HOOK }}
   run: curl -fsSL -X POST "$RENDER_DEPLOY_HOOK"
   ```
4. 映像 tag 用 commit SHA → 回滾時直接指定舊 SHA（見 Step 11）

---

## 8. 灌入賽事資料
擇一：
- **手動真實賽程**（推薦初次）：在後端容器執行
  ```bash
  # 平台的 exec/console
  python seed_worldcup.py    # 灌 72 場小組賽（含已踢比分）
  ```
- **自動同步**：以 Mike 登入後台 → 點「🔄 自動更新」（維基或 API-Football）

驗證：`curl https://api.例.com/api/v1/matches/featured` 有真實賽事。

---

## 9. 上線煙霧測試（Smoke Test）
```bash
API=https://api.例.com/api/v1
curl -s $API/../health                       # ok
curl -s $API/../ready                         # ready
curl -s "$API/matches?status=scheduled" | head # 有賽事
curl -s $API/leaderboard/global               # 200（可能空）
```
瀏覽器走一輪：
- [ ] `app.例.com` →「我的」→ **Google 登入**（用 `mike.hsieh72@gmail.com`）
- [ ] 個人中心出現「**後台 · 更新賽果**」入口（= Mike 是管理者 ✅）
- [ ] 進後台點「自動更新」→ 顯示「已更新 N 場」
- [ ] 一般帳號登入 → **看不到**後台、直接開 `/admin` 顯示「需要管理者權限」
- [ ] 對未開賽賽事下注 → 積分/道具有變化 → 排行榜更新

---

## 10. 排程器（自動結算/同步）
行程內排程已用 **Redis 鎖**防重複，但仍建議二擇一：
- **A（簡單）**：API 服務開 `SCHEDULER_ENABLED=true`、`GUNICORN_WORKERS=1`
- **B（多 worker）**：API 用多 worker + `SCHEDULER_ENABLED=false`，另跑**一個**單獨服務
  （同映像、`SCHEDULER_ENABLED=true`、不對外開 port）
- **C（平台 cron）**：關內建，改平台排程定時打
  `POST /api/v1/matches/auto-sync`（需帶管理者 JWT）

---

## 11. 回滾程序（Rollback）
1. **應用回滾**：平台選上一版映像，或重部署舊 commit SHA 的 GHCR 映像
   ```
   ghcr.io/<owner>/<repo>-backend:<舊SHA>
   ghcr.io/<owner>/<repo>-frontend:<舊SHA>
   ```
2. **Migration 回滾**（謹慎）：若新版含破壞性 migration
   ```bash
   FLASK_APP=run.py flask db downgrade -1
   ```
   - ⚠️ R32 的 enum 新增值在 PostgreSQL **無法移除**（downgrade 為 no-op），但不影響回滾
   - 破壞性變更前務必先確認備份（Step 1）
3. 回滾後重跑 Step 9 煙霧測試

---

## 12. 上線後監控檢查清單
- [ ] Sentry 有收到事件（故意觸發一個 404 確認接通）
- [ ] `/ready` 設為平台 health check / k8s readiness probe
- [ ] DB / Redis 監控告警（連線數、記憶體、磁碟）
- [ ] 排程器只在**單一**行程跑（看 log 不應重複結算同場）
- [ ] 限流生效（短時間狂打 `/auth/sso` 應回 429）
- [ ] 確認 `ALLOW_DEV_LOGIN` 未被設成 true（正式預設 false）

---

## 常見啟動失敗訊息對照
| 訊息 | 解法 |
|------|------|
| `SECRET_KEY/JWT_SECRET 仍為預設值` | 設 `openssl rand -hex 32` 的值 |
| `GOOGLE_CLIENT_ID 未設定` | 補 Step 2 的 Client ID |
| `CORS_ORIGINS 未收斂` | 設成前端網域，不可空或 `*` |
| `/ready` 503 `db:false` | 檢查 `DATABASE_URL` / DB 是否啟動 |
| `/ready` 503 `redis:false` | 檢查 `REDIS_URL` / Redis 是否啟動 |
| Google 登入失敗 | 確認前後端 Client ID 一致、origin 已授權、email 已驗證 |

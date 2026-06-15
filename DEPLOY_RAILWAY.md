# 🚂 Railway + Vercel 部署清單

後端三件套（Flask + PostgreSQL + Redis）放 Railway，前端 Next.js 放 Vercel。
照順序做，約 40–60 分鐘。先讀過 [GO_LIVE.md](GO_LIVE.md) 的「前置帳號」與「Google OAuth」。

---

## 1. 建 Railway 專案 + 資料庫
1. railway.app → **New Project** → 取名 `predictcup`
2. **+ New → Database → Add PostgreSQL**（自動產生 `DATABASE_URL`，內含每日備份）
3. **+ New → Database → Add Redis**（自動產生 `REDIS_URL`）

---

## 2. 部署後端服務
1. **+ New → GitHub Repo** → 選你的 repo
2. 服務 **Settings**：
   - **Root Directory** = `backend`（Railway 會自動偵測 `backend/Dockerfile`）
   - **Healthcheck Path** = `/health`
   - （Port 不用設 —— Railway 注入 `$PORT`，entrypoint 已綁 `$PORT`）
3. 服務 **Variables**（環境變數）：
   ```
   FLASK_ENV=production
   SECRET_KEY=<openssl rand -hex 32>
   JWT_SECRET=<openssl rand -hex 32>
   GOOGLE_CLIENT_ID=<你的 OAuth Client ID>
   CORS_ORIGINS=https://<之後的 Vercel 網域>     # 先填佔位，第 4 步回來補
   DATABASE_URL=${{Postgres.DATABASE_URL}}        # 引用 PG 服務
   REDIS_URL=${{Redis.REDIS_URL}}                 # 引用 Redis 服務
   GUNICORN_WORKERS=1
   SCHEDULER_ENABLED=true
   # 選填（之後想啟用再加、按 Redeploy 即生效）
   ANTHROPIC_API_KEY=
   SPORTS_API_KEY=
   SENTRY_DSN=
   ```
   > `${{Postgres.DATABASE_URL}}` / `${{Redis.REDIS_URL}}` 是 Railway 的服務引用語法，會自動帶入連線字串。
4. 部署後 → **Settings → Networking → Generate Domain** → 得 `https://predictcup-backend.up.railway.app`
5. **驗證**：開 `https://<後端網域>/health`（ok）、`/ready`（db/redis 都 true）
   - 若容器**起不來**並印「正式環境設定不安全，拒絕啟動」→ 照訊息補密鑰/CORS
   - 啟動時 `entrypoint.sh` 會自動跑 `flask db upgrade` 建表（看 Deploy Log）

---

## 3. 部署前端（Vercel）
1. vercel.com → **Import** 你的 repo → **Root Directory = `frontend`**
2. **Environment Variables**：
   ```
   NEXT_PUBLIC_API_BASE=https://<後端網域>/api/v1
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=<同後端的 Client ID>
   ```
3. **Deploy** → 得 `https://predictcup.vercel.app`（或綁自訂網域）

---

## 4. 接回 CORS 與 Google
1. 回 Railway 後端 → 把 `CORS_ORIGINS` 改成第 3 步的 Vercel 網域 → Redeploy
2. Google Cloud Console → OAuth Client → **Authorized JavaScript origins** 加入 Vercel 網域

---

## 5. 灌賽程資料
在**本機** repo 的 `backend/` 下（Railway CLI 會注入線上 DB 連線）：
```bash
npm i -g @railway/cli && railway login
railway link                              # 選 predictcup 專案 / 後端服務
railway run python seed_worldcup.py       # 對線上 PG 灌 72 場真實小組賽
```
或：以 Mike（管理者）登入 → 後台 →「自動更新」（維基）即可線上抓賽果。

---

## 6. 煙霧測試
- [ ] `https://<後端>/health` ok、`/ready` 兩者 true
- [ ] 前端開得起來、底部導覽列正常
- [ ] 用 `mike.hsieh72@gmail.com` Google 登入 → 出現「後台」入口（= 管理者）
- [ ] 後台「自動更新」→ 顯示更新/結算場數
- [ ] 朋友用自己的 Google 登入 → 能下注、看排行榜，但**看不到後台**

---

## 7. CI/CD（選一）
**A. Railway 原生自動部署（最省事）**
Railway 連上 GitHub 後，**push 到 main 自動 redeploy**，不需任何 workflow。
（這樣可以不理 `deploy.yml`。）

**B. 用 `.github/workflows/deploy.yml`（GH Actions 部署）**
1. Railway → Project Settings → **Tokens** → 建 token → repo Secret `RAILWAY_TOKEN`
2. repo Variable `RAILWAY_BACKEND_SERVICE` = 後端服務名稱
3. （選用）repo Secret `VERCEL_DEPLOY_HOOK` = Vercel 專案的 Deploy Hook
→ push main 時 workflow 會 `railway up` 後端、觸發 Vercel 部署

---

## 成本（低流量、朋友分享）
- Railway Hobby（後端 + PG + Redis）≈ **$5/月**
- Vercel 前端 **免費**

## 注意
- **排程器**：Railway 不休眠，`SCHEDULER_ENABLED=true` 直接可用（Redis 鎖防重複）。
- **API key**：只放 Railway Variables，**絕不**放任何 `NEXT_PUBLIC_*`（會曝光到瀏覽器）。
- 詳細環境變數說明見 [DEPLOY.md](DEPLOY.md)；通用上線流程見 [GO_LIVE.md](GO_LIVE.md)。

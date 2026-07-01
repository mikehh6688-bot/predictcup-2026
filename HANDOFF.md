# 🤝 HANDOFF — 給新維護者的第一步

歡迎接手 **PredictCup 2026**。照這份走一遍，30 分鐘內就能在本機把它跑起來並看懂全貌。

---

## 0. 先讀兩份文件（建立脈絡）
- **[CLAUDE.md](CLAUDE.md)** — 專案脈絡、架構地圖、專案規則、結算邏輯、已知 TODO
  （用 Claude Code 開資料夾會**自動載入**）
- **[CASE_STUDY.md](CASE_STUDY.md)** — 開發歷程與踩過的雷（了解「為什麼這樣設計」）

---

## 1. 取得程式碼
```bash
git clone https://github.com/mikehh6688-bot/predictcup-2026.git
cd predictcup-2026
```
（或解壓 `predictcup-2026-src.tar.gz`）

---

## 2. 本機跑起來（用 SQLite，免裝 Postgres/Redis）

**終端機 1 — 後端**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=run.py REDIS_URL="" DATABASE_URL="sqlite:///$PWD/dev.db"
rm -f dev.db*          # 若有舊 DB 先清（避免 migration 衝突）
flask db upgrade       # 用 migration 建表（勿用 create_all）
python seed_worldcup.py           # 灌 72 場真實 2026 小組賽
ALLOW_DEV_LOGIN=true python run.py  # → http://localhost:5001
```

**終端機 2 — 前端**
```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_API_BASE=http://localhost:5001/api/v1' > .env.local
npm run dev            # → http://localhost:3000
```

開 http://localhost:3000 →「我的」→ 用暱稱 **`Mike`** 登入（= 管理者）→ 可進「後台·更新賽果」。

---

## 3. 確認測試綠燈
```bash
cd backend && source .venv/bin/activate
python -m pytest tests/ -v        # 應 32 passed
cd ../frontend && npx tsc --noEmit  # 型別檢查（勿在 dev server 跑著時 next build）
```

---

## 4. 動手改之前，記住幾條規則（詳見 CLAUDE.md）
- **結算邏輯必須可重入**（`services/settlement.py`）——改賽果會反轉舊分再套新分
- **純運算（`scoring.py`）與寫 DB（`settlement.py`）分離**，計分改動先補單元測試
- **Schema 變更走 migration**：`flask db migrate -m "..."` → 檢視 → commit（不要 `create_all`）
- **金鑰只進環境變數**，永不進 repo / 前端 `NEXT_PUBLIC_*` / Docker 映像
- **新功能配測試、保持 pytest 全綠**

---

## 5. 要啟用進階功能（各自準備金鑰）
| 功能 | 需要 | 放哪 |
|------|------|------|
| 真 Claude 勝率預測 | `ANTHROPIC_API_KEY` | 後端環境變數（缺則走啟發式，仍可用）|
| Google 登入 | `GOOGLE_CLIENT_ID`（前後端同一個）| 後端 + 前端 `NEXT_PUBLIC_GOOGLE_CLIENT_ID` |
| 你要當管理者 | `ADMIN_EMAILS=你的@gmail.com` | 後端環境變數 |
| 第三方賽果 | `SPORTS_API_KEY` | 後端（缺則用維基爬蟲）|

範本見 `backend/.env.example`。

---

## 6. 要正式上線
照 **[DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md)**（Railway 後端 + Vercel 前端，約 40–60 分、~$5/月）；
通用流程見 [GO_LIVE.md](GO_LIVE.md)、環境變數總表見 [DEPLOY.md](DEPLOY.md)。

---

## 7. 可接手的 TODO（挑一個開始）
- 補**淘汰賽賽程**（2026 新制 R32；維基爬蟲目前只處理小組賽，需加淘汰賽頁與 PK 晉級解析）
- 前端加**稽核紀錄檢視頁**（後端已有 `GET /api/v1/matches/audit`）
- 接真 `ANTHROPIC_API_KEY` 讓 AI 分析從啟發式升級為 Claude
- JWT refresh token（目前 72h 過期需重登）

有問題就從 CLAUDE.md 的「架構地圖」找對應檔案。祝維護順利 🏆

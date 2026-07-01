# CLAUDE.md — PredictCup 2026 維護者脈絡

> 給接手維護的 Claude / 開發者：這是專案的「開場說明」。先讀本檔，
> 再視需要看 [CASE_STUDY.md](CASE_STUDY.md)（開發歷程）與各部署文件。

## 這是什麼
世界盃賽事預測 Web App：動態積分、策略道具（翻倍卡/保險卡，互斥）、私房聯賽、
AI 勝率預測、真實 2026 世界盃賽程、管理後台。前後端分離、已上線就緒。

## 技術棧
- **後端** `backend/`：Flask + SQLAlchemy + PostgreSQL + Redis + APScheduler，Application Factory 模式
- **前端** `frontend/`：Next.js 14 (App Router) + TypeScript + Tailwind + lucide-react
- **認證**：JWT + Google SSO（`ADMIN_EMAILS` 命中即管理者）

## 常用指令
```bash
# 後端（本機用 SQLite，免 Postgres/Redis）
cd backend
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
export FLASK_APP=run.py REDIS_URL="" DATABASE_URL="sqlite:///$PWD/dev.db"
rm -f dev.db*; flask db upgrade          # 建表（migration；勿用 create_all）
python seed_worldcup.py                    # 灌 72 場真實小組賽
ALLOW_DEV_LOGIN=true python run.py         # :5001；用暱稱「Mike」登入=管理者

python -m pytest tests/ -v                 # 32 tests，改動後務必保持全綠
python tests/test_scoring.py               # 純結算邏輯（免相依也能跑）

# 前端
cd frontend
npm install
echo 'NEXT_PUBLIC_API_BASE=http://localhost:5001/api/v1' > .env.local
npm run dev                                # :3000
npx tsc --noEmit                           # 型別檢查（勿在 dev server 跑時 next build）
```

## 架構地圖（關鍵檔案）
```
backend/app/
├── models.py            5+1 張表：User/Match/Bet/League/LeagueMember/AuditLog
├── constants.py         Enum（狀態/階段/選項）、倍率、階段標籤（無 Flask 依賴，可單測）
├── config.py            所有設定 + ProductionConfig.validate() 正式環境防呆
├── services/
│   ├── scoring.py       ⭐ 純運算結算引擎（無 DB，可單測）
│   ├── settlement.py    套用結算到 DB（可重入 idempotent）+ 鎖 match 列
│   ├── betting.py       下注/改注/取消 + 道具扣退 + 鎖 user 列
│   ├── leaderboard.py   Redis ZSET 排行榜（DB fallback）
│   ├── auth.py          JWT + Google id_token 驗證 + 管理者授予
│   ├── ai_predictor.py  Claude 勝率預測（無金鑰走啟發式）+ generate_missing
│   ├── sports_api.py    API-Football 賽程匯入
│   ├── wiki_provider.py 維基百科賽果爬蟲（免金鑰後援）
│   ├── sync_service.py  自動同步協調（API-Football 或維基 + 補 AI）
│   ├── scheduler.py     APScheduler 自動結算/同步（Redis 分散式鎖防重複）
│   └── audit.py         管理者操作稽核
└── api/                 auth/users/matches/bets/leagues/leaderboard blueprints
frontend/
├── app/                 page(首頁)/matches/leaderboard/profile/admin
├── components/          MatchCard/BettingModal/SessionProvider/GoogleSignIn...
└── lib/                 api.ts(型別化 client)/types.ts/constants.ts(flagEmoji)
```

## 專案規則（沿用，勿破壞）
- **純運算與副作用分離**：計分邏輯放 `scoring.py`（可單測），寫 DB 放 `settlement.py`。
- **結算必須可重入**：改賽果/重抓比分會反轉舊分再套新分（別改回「只結算未結算」）。
- **狀態用 Enum**；設定進 `config.py`/`constants.py`，別散落硬編碼。
- **權限用裝飾器**：`@admin_required` / `@login_required`（在 `api/_helpers.py`）。
- **Schema 變更走 migration**：`flask db migrate` → 檢視 → commit；**不要**用 `create_all`。
- **新功能配測試**，保持 `pytest` 全綠；含權限被拒、可重入等邊界。
- **金鑰只進環境變數**，永不進 repo / 前端 `NEXT_PUBLIC_*` / Docker 映像。
- **commit 訊息**：標題 + 分類條列 + `Co-Authored-By`；不 commit 產物/DB/金鑰。

## 結算規則（核心商業邏輯，改動要小心）
- 小組賽猜對勝隊：+勝隊進球 × 倍率；和局：+雙方進球和 × 倍率；猜錯扣同額
- 保險卡：猜錯扣分減半（向下取整）；翻倍卡：最終得分 ×2（兩卡互斥）
- 精準比分命中：額外 +50（不受倍率/翻倍卡影響）
- 淘汰賽：只判晉級隊，積分採常規+延長賽進球（PK 不計）
- 倍率：小組×1、32/16/8 強×2、4 強×5、決賽×10

## 已知限制 / 可接手的 TODO
- **淘汰賽賽程未灌**（2026 新制 R32；隊伍待小組賽定），維基爬蟲目前只處理小組賽 → 可補淘汰賽頁解析（含 PK 晉級）
- **AI 預測目前多為啟發式**（本機無 `ANTHROPIC_API_KEY`）→ 設金鑰即用真 Claude
- **賽果自動來源**：API-Football 免費版無 WC2026 → 主要靠維基爬蟲（會隨頁面改版脆化）
- **JWT 無 refresh**（72h 過期需重登）；logout 不撤銷 token
- **前端無稽核紀錄檢視頁**（後端已有 `GET /matches/audit`）→ 可加 UI
- 舊 commit 歷史仍含作者 email（前向已清程式碼硬編碼）

## 部署
- 一鍵本機：`docker compose up --build`
- 正式：見 [DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md)（Railway 後端 + Vercel 前端）、
  通用流程 [GO_LIVE.md](GO_LIVE.md)、環境變數總表 [DEPLOY.md](DEPLOY.md)
- 正式必填環境變數：`FLASK_ENV=production` `SECRET_KEY` `JWT_SECRET`
  `GOOGLE_CLIENT_ID` `CORS_ORIGINS` `DATABASE_URL` `REDIS_URL`（+ 管理者 `ADMIN_EMAILS`）

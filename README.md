# 🏆 PredictCup 2026

世界盃賽事預測系統 —— 動態零和積分、策略道具、私房聯賽，搭配 AI 勝率與網民風向戰情儀表板。
Mobile-first，採乾淨明亮的體育新聞風（ESPN / FIFA 官網）。

![CI](https://img.shields.io/badge/tests-25%20passing-success)
![license](https://img.shields.io/badge/license-MIT-blue)

## ✨ 核心亮點
- **動態零和積分盤**：以下注隊伍的「實際進球數」作為得分基準，每顆進球都牽動排行榜。
- **高倍率翻盤**：淘汰賽積分乘數（16/8 強 ×2、4 強 ×5、決賽 ×10）。
- **策略道具**：翻倍卡、保險卡（互斥），精準比分命中額外 +50。
- **AI 與社群風向**：Claude 勝率預測 vs. 系統內下注比例。
- **私房聯賽**：一鍵建房 + 邀請碼，含「冥燈榜」與「輸家請客」。

## 🧱 技術棧
| 層 | 技術 |
|----|------|
| 前端 | Next.js 14 (App Router) · React 18 · TypeScript · Tailwind · lucide-react |
| 後端 | Python Flask · SQLAlchemy · APScheduler |
| 資料 | PostgreSQL（主資料）· Redis（排行榜快取） |
| 認證 | JWT + Google SSO（id_token 驗證） |
| AI | Claude（`claude-opus-4-8`，官方 anthropic SDK） |
| 部署 | Docker / docker-compose · Vercel（前端） |

## 📂 結構
```
.
├── backend/        Flask API（見 backend/README.md · API_DESIGN.md）
├── frontend/       Next.js 前端（見 frontend/README.md）
├── docker-compose.yml
├── DEPLOY.md       部署指南
└── .github/workflows/ci.yml
```

## 🚀 快速開始
```bash
# 一鍵起整套（Postgres + Redis + 後端 + 前端）
cp .env.deploy.example .env
docker compose up --build
# 前端 http://localhost:3000 · 後端 http://localhost:5001/health
```
本機開發分別啟動，請見 [backend/README.md](backend/README.md) 與 [frontend/README.md](frontend/README.md)。

## 🧪 測試
```bash
cd backend && python -m pytest tests/ -v      # 25 passed
cd frontend && npm run build                  # 型別檢查 + 建置
```

## 📖 文件
- [後端 API 設計與結算規則](backend/API_DESIGN.md)
- [部署指南](DEPLOY.md)
- [🚀 上線當天操作手冊](GO_LIVE.md)
- [🚂 Railway + Vercel 部署清單](DEPLOY_RAILWAY.md)

## 📝 授權
[MIT](LICENSE) © 2026 Mike Hsieh

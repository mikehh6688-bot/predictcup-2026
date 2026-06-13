# PredictCup 2026 — Frontend (Next.js)

Mobile-first 世界盃預測 Web App。乾淨明亮體育新聞風（ESPN / FIFA 官網），底部固定導覽列。

## 技術棧
- **Next.js 14**（App Router）+ React 18 + TypeScript
- **Tailwind CSS** + `lucide-react` icons
- 設計：`bg-gray-50` 底、白卡 `shadow-sm`、CTA emerald-600 / blue-600

## 啟動
```bash
cd frontend
npm install
cp .env.local.example .env.local   # 設定 NEXT_PUBLIC_API_BASE（指向 Flask 後端）
npm run dev                        # http://localhost:3000
```

> 後端 demo：`cd backend && REDIS_URL="" DATABASE_URL="sqlite:///dev.db" python seed.py`
> 再 `... python run.py`（:5001），前端即可串接真實資料。

## 結構
```
frontend/
├── app/
│   ├── layout.tsx        # Root layout：置中容器 + BottomNav
│   ├── globals.css       # Tailwind + 主題
│   ├── page.tsx          # ⭐ Home Dashboard（積分卡 + 焦點賽事）
│   ├── matches/          # 賽事大廳（Phase 4）
│   ├── leaderboard/      # 排行榜（Phase 4）
│   └── profile/          # 個人中心（Phase 4）
├── components/
│   ├── BottomNav.tsx     # 底部固定導覽列（4 tabs）
│   ├── PointsCard.tsx    # 積分 + 道具背包卡片
│   ├── MatchCard.tsx     # 賽事卡（國旗 / 時間 / 倍率 / CTA）
│   ├── AiBar.tsx         # AI 勝率預測長條圖
│   └── ComingSoon.tsx    # 佔位頁
└── lib/
    ├── types.ts          # 與後端 to_dict() 對齊的型別
    ├── mock.ts           # Phase 3 Mock Data（Phase 4 換 API）
    └── format.ts         # 時間 / 百分比格式工具
```

## 階段
- **Phase 3 ✅** 基礎 Layout + Home Dashboard（Mock Data）
- **Phase 4 ✅** 串接 Flask API（`/api/v1`）：登入、賽事大廳三分頁、下注 Modal、排行榜三 Tabs、私房聯賽、個人中心
  - `lib/api.ts` 型別化 client · `components/SessionProvider.tsx` session（localStorage token）
  - 全流程已實機驗證：登入 → 下注扣道具 → 結算加分 → 排行榜

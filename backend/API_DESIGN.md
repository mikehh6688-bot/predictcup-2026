# PredictCup 2026 — RESTful API 設計（Phase 1）

Base URL：`/api/v1`　|　認證：`Authorization: Bearer <jwt>`（SSO 預留）

> Phase 1 僅定義路由與 Request/Response 格式，端點回傳 `501 Not Implemented`，核心邏輯於 Phase 2 實作。

## 通用回應格式
```jsonc
// 成功
{ "data": { ... } }            // 或直接回傳資源物件
// 錯誤
{ "error": { "code": "BET_LOCKED", "message": "..." } }
```

---

## 1. Auth（帳號 / SSO，回傳本地 JWT）
| Method | Endpoint            | 說明                         | Request                                        | Response          |
|--------|---------------------|------------------------------|------------------------------------------------|-------------------|
| POST   | `/auth/sso`         | SSO 登入，首登自動建號配道具 | Google:`{provider:"google", id_token}`<br>Dev:`{provider:"dev", username}` | `{token, user}` |
| GET    | `/auth/me`          | 取得目前登入者（首頁卡片）   | Header `Authorization: Bearer <jwt>`           | `<User>`          |
| POST   | `/auth/logout`      | 登出（前端丟棄 token）       | —                                              | `204`             |

## 2. Users（使用者 / 道具）
| Method | Endpoint                      | 說明           | Response                               |
|--------|-------------------------------|----------------|----------------------------------------|
| GET    | `/users/{id}`                 | 使用者公開資料 | `<User>`                               |
| GET    | `/users/{id}/inventory`       | 道具背包       | `{double_cards, insurance_cards}`      |
| GET    | `/users/{id}/bets?status=`    | 個人注單歷史   | `{bets: [<Bet>]}`                      |

## 3. Matches（賽事大廳 / 戰情儀表板）
| Method | Endpoint                          | 說明                       | Request / Query                                  |
|--------|-----------------------------------|----------------------------|--------------------------------------------------|
| GET    | `/matches?status=&stage=&date=`   | 賽事列表（三分頁籤）       | `status=scheduled\|live\|finished`               |
| GET    | `/matches/featured`               | 首頁焦點賽事（1~2 場）     | —                                                |
| GET    | `/matches/{id}`                   | 賽事詳情＋下注比例         | —                                                |
| POST   | `/matches`                        | 建立賽事（MVP 手動）       | `{home_team, away_team, kickoff_time, stage}`    |
| PATCH  | `/matches/{id}/result`            | 更新賽果並觸發結算         | `{home_score, away_score, advancing_team}`       |
| POST   | `/matches/{id}/ai-generate`       | 觸發 Claude 產生勝率+風向  | —（缺 ANTHROPIC_API_KEY 時走啟發式）             |
| PATCH  | `/matches/{id}/ai-prediction`     | 手動寫入勝率與風向（覆寫） | `{ai_*_prob, ai_analysis, public_*_pct}`         |
| POST   | `/matches/sync-results`           | 觸發第三方賽事 API 賽果同步 | Query `?date=YYYY-MM-DD`                          |

## 4. Bets（投注引擎）
| Method | Endpoint        | 說明                 | Request                                                              |
|--------|-----------------|----------------------|---------------------------------------------------------------------|
| POST   | `/bets`         | 下注（Modal 送出）   | `{user_id, match_id, predicted_result, predicted_home_score?, predicted_away_score?, use_double_card, use_insurance_card}` |
| GET    | `/bets/{id}`    | 注單詳情（含結算）   | —                                                                   |
| PATCH  | `/bets/{id}`    | 改注（鎖盤前）       | 同 POST 可選欄位                                                    |
| DELETE | `/bets/{id}`    | 取消注單（鎖盤前）   | —                                                                   |

**下注驗證規則**：賽事須 `scheduled` 且距開賽 > 5 分鐘；道具數量足夠；`(user_id, match_id)` 唯一。

## 5. Leagues（私房聯賽）
| Method | Endpoint                        | 說明                 | Request                       |
|--------|---------------------------------|----------------------|-------------------------------|
| POST   | `/leagues`                      | 建立聯賽（產邀請碼） | `{name, owner_id}`            |
| POST   | `/leagues/join`                 | 以邀請碼加入         | `{invite_code, user_id}`      |
| GET    | `/leagues?user_id=`             | 我參加的聯賽         | —                             |
| GET    | `/leagues/{id}`                 | 聯賽詳情             | —                             |
| GET    | `/leagues/{id}/leaderboard`     | 聯賽排名（輸家請客） | —                             |

## 6. Leaderboard（排行榜，Redis 快取）
| Method | Endpoint                 | 說明                       | Response                                      |
|--------|--------------------------|----------------------------|-----------------------------------------------|
| GET    | `/leaderboard/global?limit=` | 全站百大（金銀銅）     | `{ranking: [{rank, user, points, medal}]}`    |
| GET    | `/leaderboard/loser?limit=`  | 冥燈榜（積分最低）     | `{ranking: [{rank, user, points}]}`           |

---

## 結算邏輯（Phase 2 實作，先記錄規則）
| 情境                 | 得分 / 扣分                                              |
|----------------------|---------------------------------------------------------|
| 小組賽猜對勝隊       | `+ 勝隊進球數 × 倍率`                                    |
| 小組賽猜錯勝隊       | `- 勝隊進球數 × 倍率`（保險卡：扣分減半）                |
| 小組賽猜中和局       | `+ (主+客進球) × 倍率`；猜錯和局則同額扣分               |
| 淘汰賽               | 僅判定晉級隊伍；積分採常規＋延長賽進球，**PK 不計入**    |
| 精準比分命中         | 額外 `+50`（不受倍率影響）                               |
| 翻倍卡               | 該注最終得分 `× 2`（含正負）                            |
| 倍率                 | 小組 ×1、16/8 強 ×2、4 強 ×5、決賽/季軍 ×10              |

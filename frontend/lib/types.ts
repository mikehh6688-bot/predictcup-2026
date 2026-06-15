// 與後端 to_dict() 對齊的型別定義（Phase 4 串接 API 時沿用）

export type MatchStatus = "scheduled" | "live" | "finished";
export type MatchStage =
  | "group"
  | "round_of_32"
  | "round_of_16"
  | "quarter_final"
  | "semi_final"
  | "final";
export type BetChoice = "home" | "draw" | "away";

export interface User {
  id: number;
  username: string;
  email: string | null;
  total_points: number;
  double_cards: number; // 翻倍卡
  insurance_cards: number; // 保險卡
  is_admin: boolean; // 管理者（可進後台）
  created_at: string;
}

export interface AiPrediction {
  home: number | null;
  draw: number | null;
  away: number | null;
  analysis: string | null;
}

export interface PublicSentiment {
  home: number | null;
  draw: number | null;
  away: number | null;
}

export interface Match {
  id: number;
  home_team: string;
  away_team: string;
  home_team_code: string | null;
  away_team_code: string | null;
  kickoff_time: string; // ISO
  status: MatchStatus;
  stage: MatchStage;
  multiplier: number;
  home_score: number | null;
  away_score: number | null;
  advancing_team: BetChoice | null;
  ai_prediction: AiPrediction;
  public_sentiment: PublicSentiment;
}

export interface LeaderboardEntry {
  rank: number;
  user: User;
  points: number;
  medal: "gold" | "silver" | "bronze" | null;
  is_loser?: boolean;
}

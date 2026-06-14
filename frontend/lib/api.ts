// 與 Flask 後端 (/api/v1) 串接的型別化 client。
import type {
  User,
  Match,
  LeaderboardEntry,
  BetChoice,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5001/api/v1";

/** 後端統一錯誤格式 { error: { code, message } } 的對應例外 */
export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string | null;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new ApiError("NETWORK_ERROR", "無法連線伺服器，請確認後端是否啟動", 0);
  }

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error;
    throw new ApiError(
      err?.code ?? "ERROR",
      err?.message ?? `請求失敗 (${res.status})`,
      res.status
    );
  }
  return data as T;
}

// ---- Endpoints ------------------------------------------------------------ //

export interface Ranking {
  ranking: LeaderboardEntry[];
}
export interface MatchDetail extends Match {
  user_bet_distribution: Record<BetChoice, number>;
  total_bets: number;
}
export interface Bet {
  id: number;
  user_id: number;
  match_id: number;
  predicted_result: BetChoice;
  predicted_home_score: number | null;
  predicted_away_score: number | null;
  use_double_card: boolean;
  use_insurance_card: boolean;
  is_settled: boolean;
  points_earned: number | null;
  exact_hit: boolean;
  created_at: string;
}
export interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
  member_count: number;
  created_at: string;
}

export interface PlaceBetInput {
  match_id: number;
  predicted_result: BetChoice;
  predicted_home_score?: number | null;
  predicted_away_score?: number | null;
  use_double_card: boolean;
  use_insurance_card: boolean;
}

export const api = {
  auth: {
    // Dev 登入（暱稱）
    devLogin: (username: string) =>
      request<{ token: string; user: User }>("/auth/sso", {
        method: "POST",
        body: { provider: "dev", username },
      }),
    // Google SSO（前端取得 id_token 後交換本地 JWT）
    googleLogin: (idToken: string) =>
      request<{ token: string; user: User }>("/auth/sso", {
        method: "POST",
        body: { provider: "google", id_token: idToken },
      }),
    me: (token: string) => request<User>("/auth/me", { token }),
  },

  users: {
    inventory: (userId: number) =>
      request<{ double_cards: number; insurance_cards: number }>(
        `/users/${userId}/inventory`
      ),
    bets: (userId: number, status?: "pending" | "settled") =>
      request<{ bets: Bet[] }>(
        `/users/${userId}/bets${status ? `?status=${status}` : ""}`
      ),
  },

  matches: {
    list: (status?: string) =>
      request<{ matches: Match[] }>(`/matches${status ? `?status=${status}` : ""}`),
    featured: () => request<{ matches: Match[] }>("/matches/featured"),
    get: (id: number) => request<MatchDetail>(`/matches/${id}`),
    // 後台：更新賽果並觸發結算
    updateResult: (
      id: number,
      body: { home_score: number; away_score: number; advancing_team?: "home" | "away" | null }
    ) =>
      request<{ match: Match; settlement: { settled: number; affected_users: number } }>(
        `/matches/${id}/result`,
        { method: "PATCH", body }
      ),
    // 後台：自動上網收集最新賽果並重新結算
    autoSync: () =>
      request<{ source: string; updated: number; settled: number }>(
        "/matches/auto-sync",
        { method: "POST" }
      ),
  },

  bets: {
    place: (input: PlaceBetInput, token: string) =>
      request<Bet>("/bets", { method: "POST", body: input, token }),
    cancel: (id: number, token: string) =>
      request<void>(`/bets/${id}`, { method: "DELETE", token }),
  },

  leaderboard: {
    global: (limit = 100) => request<Ranking>(`/leaderboard/global?limit=${limit}`),
    losers: (limit = 10) => request<Ranking>(`/leaderboard/loser?limit=${limit}`),
  },

  leagues: {
    mine: (token: string) =>
      request<{ leagues: League[] }>("/leagues", { token }),
    create: (name: string, token: string) =>
      request<League>("/leagues", { method: "POST", body: { name }, token }),
    join: (invite_code: string, token: string) =>
      request<League>("/leagues/join", {
        method: "POST",
        body: { invite_code },
        token,
      }),
    leaderboard: (id: number) =>
      request<{ league: League; ranking: LeaderboardEntry[] }>(
        `/leagues/${id}/leaderboard`
      ),
  },
};

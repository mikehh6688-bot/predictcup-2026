"use client";

import { useEffect, useState } from "react";
import { LogOut, Zap, ShieldCheck, Ticket, Settings, ChevronRight } from "lucide-react";
import { Spinner } from "@/components/states";
import { useSession } from "@/components/SessionProvider";
import GoogleSignIn from "@/components/GoogleSignIn";
import { api, ApiError, type Bet } from "@/lib/api";
import type { BetChoice } from "@/lib/types";

const CHOICE_LABEL: Record<BetChoice, string> = {
  home: "主勝/主晉級",
  draw: "和局",
  away: "客勝/客晉級",
};

export default function ProfilePage() {
  const { user, loading, login, loginWithGoogle, logout } = useSession();

  if (loading) return <Spinner />;
  if (!user) return <LoginForm onLogin={login} onGoogle={loginWithGoogle} />;

  return (
    <main className="px-4 pt-5">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-bold text-gray-900">個人中心</h1>
        <button
          onClick={logout}
          className="flex items-center gap-1 text-sm font-medium text-gray-400"
        >
          <LogOut size={16} />
          登出
        </button>
      </header>

      {/* 使用者卡 */}
      <div className="rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-500 p-5 text-white shadow-sm">
        <p className="text-sm text-emerald-50/90">{user.username}</p>
        <div className="mt-1 flex items-end gap-1.5">
          <span className="text-3xl font-bold">{user.total_points}</span>
          <span className="mb-0.5 text-sm text-emerald-50/80">分</span>
        </div>
        <div className="mt-3 flex gap-3 text-sm">
          <span className="flex items-center gap-1">
            <Zap size={14} className="text-amber-300" />翻倍卡 ×{user.double_cards}
          </span>
          <span className="flex items-center gap-1">
            <ShieldCheck size={14} className="text-sky-200" />保險卡 ×{user.insurance_cards}
          </span>
        </div>
      </div>

      {/* 後台入口 */}
      <a
        href="/admin"
        className="mt-3 flex items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3 text-sm shadow-sm"
      >
        <span className="flex items-center gap-2 font-medium text-gray-700">
          <Settings size={16} className="text-emerald-600" />
          後台 · 更新賽果
        </span>
        <ChevronRight size={16} className="text-gray-300" />
      </a>

      <BetHistory userId={user.id} />
    </main>
  );
}

function LoginForm({
  onLogin,
  onGoogle,
}: {
  onLogin: (u: string) => Promise<void>;
  onGoogle: (idToken: string) => Promise<void>;
}) {
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "登入失敗，請確認後端已啟動");
    } finally {
      setBusy(false);
    }
  }

  const hasGoogle = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

  return (
    <main className="flex min-h-[70vh] flex-col justify-center px-6">
      <h1 className="text-center text-xl font-bold text-gray-900">登入 PredictCup</h1>
      <p className="mt-1 text-center text-sm text-gray-400">
        {hasGoogle ? "使用 Google 快速登入，或以暱稱進入" : "輸入暱稱即可進入（開發模式）"}
      </p>

      {/* Google SSO（設定 NEXT_PUBLIC_GOOGLE_CLIENT_ID 後顯示）*/}
      {hasGoogle && (
        <>
          <div className="mt-6 flex justify-center">
            <GoogleSignIn onCredential={(idToken) => run(() => onGoogle(idToken))} />
          </div>
          <div className="my-5 flex items-center gap-3 text-xs text-gray-300">
            <span className="h-px flex-1 bg-gray-200" />
            或
            <span className="h-px flex-1 bg-gray-200" />
          </div>
        </>
      )}

      <div className={`space-y-3 ${hasGoogle ? "" : "mt-6"}`}>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && username.trim() && run(() => onLogin(username.trim()))}
          placeholder="你的暱稱"
          className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-emerald-500"
        />
        {error && <p className="text-xs font-medium text-red-500">{error}</p>}
        <button
          onClick={() => run(() => onLogin(username.trim()))}
          disabled={busy || !username.trim()}
          className="w-full rounded-xl bg-emerald-600 py-3 text-sm font-bold text-white disabled:opacity-50"
        >
          {busy ? "登入中…" : "以暱稱登入"}
        </button>
      </div>
    </main>
  );
}

function BetHistory({ userId }: { userId: number }) {
  const [bets, setBets] = useState<Bet[] | null>(null);

  useEffect(() => {
    api.users
      .bets(userId)
      .then((r) => setBets(r.bets))
      .catch(() => setBets([]));
  }, [userId]);

  return (
    <section className="mt-6">
      <h2 className="mb-3 flex items-center gap-1.5 text-base font-bold text-gray-900">
        <Ticket size={18} className="text-emerald-600" />
        我的注單
      </h2>
      {!bets ? (
        <Spinner />
      ) : bets.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">還沒有任何注單</p>
      ) : (
        <ul className="space-y-2">
          {bets.map((b) => (
            <li
              key={b.id}
              className="flex items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm"
            >
              <div>
                <p className="text-sm font-semibold text-gray-800">
                  賽事 #{b.match_id} · {CHOICE_LABEL[b.predicted_result]}
                </p>
                <p className="text-xs text-gray-400">
                  {b.predicted_home_score != null
                    ? `精準 ${b.predicted_home_score}:${b.predicted_away_score}`
                    : "未填精準比分"}
                  {b.use_double_card && " · 翻倍卡"}
                  {b.use_insurance_card && " · 保險卡"}
                </p>
              </div>
              {b.is_settled ? (
                <span
                  className={`text-sm font-bold tabular-nums ${
                    (b.points_earned ?? 0) < 0 ? "text-red-500" : "text-emerald-600"
                  }`}
                >
                  {(b.points_earned ?? 0) > 0 ? "+" : ""}
                  {b.points_earned}
                </span>
              ) : (
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                  待結算
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import { Trophy, Flame } from "lucide-react";
import PointsCard from "@/components/PointsCard";
import MatchCard from "@/components/MatchCard";
import BettingModal from "@/components/BettingModal";
import { Spinner, ErrorState, LoginPrompt } from "@/components/states";
import { useSession } from "@/components/SessionProvider";
import { api } from "@/lib/api";
import type { Match } from "@/lib/types";

export default function HomePage() {
  const { user, token, loading: sessionLoading, refresh } = useSession();
  const [matches, setMatches] = useState<Match[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [betting, setBetting] = useState<Match | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.matches
      .featured()
      .then((r) => setMatches(r.matches))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => load(), [load]);

  async function handlePlaced() {
    setBetting(null);
    await refresh(); // 更新積分 / 道具
    load();
  }

  return (
    <main className="px-4 pt-5">
      <header className="mb-4 flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white">
          <Trophy size={20} />
        </div>
        <div>
          <h1 className="text-lg font-bold leading-tight text-gray-900">
            PredictCup <span className="text-emerald-600">2026</span>
          </h1>
          <p className="text-[11px] text-gray-400">世界盃預測 · 私房聯賽</p>
        </div>
      </header>

      {/* 積分 / 道具 或 登入提示 */}
      {sessionLoading ? (
        <div className="h-36 animate-pulse rounded-2xl bg-gray-100" />
      ) : user ? (
        <PointsCard user={user} />
      ) : (
        <LoginPrompt note="登入後即可下注、累積積分與道具" />
      )}

      <section className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-base font-bold text-gray-900">
            <Flame size={18} className="text-orange-500" />
            焦點賽事
          </h2>
          <a href="/matches" className="text-xs font-medium text-emerald-600">
            查看全部
          </a>
        </div>

        {error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !matches ? (
          <Spinner />
        ) : matches.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400">目前沒有即將開打的賽事</p>
        ) : (
          <div className="space-y-3">
            {matches.map((m) => (
              <MatchCard
                key={m.id}
                match={m}
                onBet={user && token ? setBetting : undefined}
              />
            ))}
          </div>
        )}
      </section>

      {betting && user && token && (
        <BettingModal
          match={betting}
          user={user}
          token={token}
          onClose={() => setBetting(null)}
          onPlaced={handlePlaced}
        />
      )}
    </main>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import { ListChecks } from "lucide-react";
import MatchCard from "@/components/MatchCard";
import BettingModal from "@/components/BettingModal";
import { Spinner, ErrorState } from "@/components/states";
import { useSession } from "@/components/SessionProvider";
import { api } from "@/lib/api";
import type { Match, MatchStatus } from "@/lib/types";

const TABS: { key: MatchStatus; label: string }[] = [
  { key: "scheduled", label: "未開賽" },
  { key: "live", label: "進行中" },
  { key: "finished", label: "已完賽" },
];

export default function MatchesPage() {
  const { user, token, refresh } = useSession();
  const [tab, setTab] = useState<MatchStatus>("scheduled");
  const [matches, setMatches] = useState<Match[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [betting, setBetting] = useState<Match | null>(null);

  const load = useCallback(() => {
    setMatches(null);
    setError(null);
    api.matches
      .list(tab)
      .then((r) => setMatches(r.matches))
      .catch((e) => setError(e.message));
  }, [tab]);

  useEffect(() => load(), [load]);

  async function handlePlaced() {
    setBetting(null);
    await refresh();
    load();
  }

  return (
    <main className="px-4 pt-5">
      <header className="mb-4 flex items-center gap-2">
        <ListChecks size={22} className="text-emerald-600" />
        <h1 className="text-lg font-bold text-gray-900">賽事大廳</h1>
      </header>

      {/* 分頁籤 */}
      <div className="mb-4 flex rounded-xl bg-gray-100 p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-lg py-1.5 text-sm font-medium transition ${
              tab === t.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !matches ? (
        <Spinner />
      ) : matches.length === 0 ? (
        <p className="py-12 text-center text-sm text-gray-400">此分類目前沒有賽事</p>
      ) : (
        <div className="space-y-3">
          {matches.map((m) => (
            <MatchCard
              key={m.id}
              match={m}
              onBet={tab === "scheduled" && user && token ? setBetting : undefined}
            />
          ))}
        </div>
      )}

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

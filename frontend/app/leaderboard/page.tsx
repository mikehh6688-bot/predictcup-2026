"use client";

import { useEffect, useState, useCallback } from "react";
import { Trophy } from "lucide-react";
import RankList from "@/components/RankList";
import { Spinner, ErrorState } from "@/components/states";
import { api } from "@/lib/api";
import type { LeaderboardEntry } from "@/lib/types";
import LeaguesPanel from "@/components/LeaguesPanel";

type Tab = "global" | "loser" | "leagues";

const TABS: { key: Tab; label: string }[] = [
  { key: "global", label: "全站百大" },
  { key: "loser", label: "冥燈榜" },
  { key: "leagues", label: "私房聯賽" },
];

export default function LeaderboardPage() {
  const [tab, setTab] = useState<Tab>("global");

  return (
    <main className="px-4 pt-5">
      <header className="mb-4 flex items-center gap-2">
        <Trophy size={22} className="text-emerald-600" />
        <h1 className="text-lg font-bold text-gray-900">排行榜</h1>
      </header>

      <div className="mb-4 flex rounded-xl bg-gray-100 p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-lg py-1.5 text-sm font-medium transition ${
              tab === t.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "leagues" ? (
        <LeaguesPanel />
      ) : (
        <GlobalBoard tab={tab} />
      )}
    </main>
  );
}

function GlobalBoard({ tab }: { tab: "global" | "loser" }) {
  const [entries, setEntries] = useState<LeaderboardEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setEntries(null);
    setError(null);
    const req = tab === "global" ? api.leaderboard.global() : api.leaderboard.losers();
    req.then((r) => setEntries(r.ranking)).catch((e) => setError(e.message));
  }, [tab]);

  useEffect(() => load(), [load]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!entries) return <Spinner />;
  return <RankList entries={entries} />;
}

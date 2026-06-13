"use client";

import { useEffect, useState, useCallback } from "react";
import { Plus, LogIn, Users, ChevronLeft, Copy, Check } from "lucide-react";
import RankList from "@/components/RankList";
import { Spinner, ErrorState, LoginPrompt } from "@/components/states";
import { useSession } from "@/components/SessionProvider";
import { api, ApiError, type League } from "@/lib/api";
import type { LeaderboardEntry } from "@/lib/types";

export default function LeaguesPanel() {
  const { token } = useSession();
  const [leagues, setLeagues] = useState<League[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<League | null>(null);
  const [mode, setMode] = useState<"none" | "create" | "join">("none");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLeagues(null);
    setError(null);
    api.leagues
      .mine(token)
      .then((r) => setLeagues(r.leagues))
      .catch((e) => setError(e.message));
  }, [token]);

  useEffect(() => load(), [load]);

  async function submitAction() {
    if (!token || !input.trim()) return;
    setBusy(true);
    setActionError(null);
    try {
      if (mode === "create") await api.leagues.create(input.trim(), token);
      else await api.leagues.join(input.trim(), token);
      setInput("");
      setMode("none");
      load();
    } catch (e) {
      setActionError(e instanceof ApiError ? e.message : "操作失敗");
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <LoginPrompt note="登入後即可建立 / 加入私房聯賽" />;
  if (selected) return <LeagueDetail league={selected} onBack={() => setSelected(null)} />;

  return (
    <div>
      {/* 建立 / 加入 */}
      <div className="mb-4 grid grid-cols-2 gap-2">
        <ActionButton
          active={mode === "create"}
          onClick={() => setMode(mode === "create" ? "none" : "create")}
          icon={<Plus size={16} />}
          label="建立聯賽"
        />
        <ActionButton
          active={mode === "join"}
          onClick={() => setMode(mode === "join" ? "none" : "join")}
          icon={<LogIn size={16} />}
          label="輸入邀請碼"
        />
      </div>

      {mode !== "none" && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={mode === "create" ? "聯賽名稱（例：KMC 部門大賽）" : "邀請碼"}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          />
          {actionError && (
            <p className="mt-2 text-xs font-medium text-red-500">{actionError}</p>
          )}
          <button
            onClick={submitAction}
            disabled={busy || !input.trim()}
            className="mt-2 w-full rounded-lg bg-emerald-600 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "處理中…" : mode === "create" ? "建立" : "加入"}
          </button>
        </div>
      )}

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !leagues ? (
        <Spinner />
      ) : leagues.length === 0 ? (
        <p className="py-10 text-center text-sm text-gray-400">
          還沒有加入任何聯賽，建立一個揪同事一起玩吧！
        </p>
      ) : (
        <ul className="space-y-2">
          {leagues.map((lg) => (
            <li key={lg.id}>
              <button
                onClick={() => setSelected(lg)}
                className="flex w-full items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3 text-left shadow-sm"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-800">{lg.name}</p>
                  <p className="text-xs text-gray-400">邀請碼 {lg.invite_code}</p>
                </div>
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Users size={14} />
                  {lg.member_count}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ActionButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center justify-center gap-1.5 rounded-xl border py-2.5 text-sm font-semibold transition ${
        active
          ? "border-emerald-600 bg-emerald-50 text-emerald-700"
          : "border-gray-200 bg-white text-gray-600"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function LeagueDetail({ league, onBack }: { league: League; onBack: () => void }) {
  const [ranking, setRanking] = useState<LeaderboardEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    setRanking(null);
    setError(null);
    api.leagues
      .leaderboard(league.id)
      .then((r) => setRanking(r.ranking))
      .catch((e) => setError(e.message));
  }, [league.id]);

  useEffect(() => load(), [load]);

  function copyCode() {
    navigator.clipboard?.writeText(league.invite_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div>
      <button
        onClick={onBack}
        className="mb-3 flex items-center gap-1 text-sm font-medium text-gray-500"
      >
        <ChevronLeft size={16} />
        返回聯賽列表
      </button>

      <div className="mb-4 rounded-xl bg-white p-4 shadow-sm">
        <h2 className="text-base font-bold text-gray-900">{league.name}</h2>
        <button
          onClick={copyCode}
          className="mt-1 flex items-center gap-1 text-xs text-gray-400"
        >
          邀請碼 <span className="font-mono font-semibold">{league.invite_code}</span>
          {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
        </button>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !ranking ? (
        <Spinner />
      ) : (
        <RankList entries={ranking} />
      )}
    </div>
  );
}

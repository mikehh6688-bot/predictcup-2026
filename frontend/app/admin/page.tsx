"use client";

import { useCallback, useEffect, useState } from "react";
import { Settings, RefreshCw, Check, Lock, Sparkles } from "lucide-react";
import { Spinner, ErrorState } from "@/components/states";
import { useSession } from "@/components/SessionProvider";
import { flagEmoji, STAGE_LABEL } from "@/lib/constants";
import { api, ApiError } from "@/lib/api";
import type { Match } from "@/lib/types";
import { formatKickoff } from "@/lib/format";

/**
 * 後台：更新賽果。
 * - 「自動更新」按鈕：上網收集最新比分（API-Football 或維基）並重新結算。
 * - 每場可手動輸入比分；結算為可重入，已結算者可修正後重算。
 * 注意：此頁無權限控管，僅供本機 / 信任環境維運使用。
 */
export default function AdminPage() {
  const { user, token, loading } = useSession();
  const [matches, setMatches] = useState<Match[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.matches
      .list()
      .then((r) =>
        setMatches(
          [...r.matches].sort((a, b) => a.kickoff_time.localeCompare(b.kickoff_time))
        )
      )
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => load(), [load]);

  async function autoSync() {
    if (!token) return;
    setSyncing(true);
    setSyncMsg(null);
    try {
      const r = await api.matches.autoSync(token);
      const src = r.source === "wikipedia" ? "維基百科" : "API-Football";
      setSyncMsg(
        `已從${src}更新 ${r.updated} 場、結算 ${r.settled} 場、AI 生成 ${r.ai_generated} 場`
      );
      load();
    } catch (e) {
      setSyncMsg(e instanceof ApiError ? e.message : "自動更新失敗");
    } finally {
      setSyncing(false);
    }
  }

  async function aiGenerate() {
    if (!token) return;
    setAiBusy(true);
    setSyncMsg(null);
    try {
      const r = await api.matches.aiGenerateAll(token);
      setSyncMsg(
        r.generated > 0
          ? `已生成 ${r.generated} 場 AI 勝率預測`
          : "所有賽事都已有 AI 預測"
      );
      load();
    } catch (e) {
      setSyncMsg(e instanceof ApiError ? e.message : "AI 生成失敗");
    } finally {
      setAiBusy(false);
    }
  }

  // 權限把關：僅限管理者
  if (loading) return <Spinner />;
  if (!user || !user.is_admin) return <NoPermission />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!matches) return <Spinner />;

  const pending = matches.filter((m) => m.status !== "finished");
  const finished = matches.filter((m) => m.status === "finished");

  return (
    <main className="px-4 pt-5">
      <header className="mb-1 flex items-center justify-between">
        <span className="flex items-center gap-2">
          <Settings size={22} className="text-emerald-600" />
          <h1 className="text-lg font-bold text-gray-900">後台 · 更新賽果</h1>
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={aiGenerate}
            disabled={aiBusy}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
          >
            <Sparkles size={14} className={aiBusy ? "animate-pulse" : ""} />
            {aiBusy ? "生成中…" : "AI 預測"}
          </button>
          <button
            onClick={autoSync}
            disabled={syncing}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
          >
            <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
            {syncing ? "更新中…" : "自動更新"}
          </button>
        </div>
      </header>
      <p className="mb-3 text-xs text-gray-400">
        「自動更新」上網抓最新比分並結算；也可手動輸入。已結算者可修正後重算。
      </p>
      {syncMsg && (
        <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700">
          {syncMsg}
        </p>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-bold text-gray-500">待更新 ({pending.length})</h2>
        {pending.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-400">沒有待更新的賽事</p>
        ) : (
          pending.map((m) => (
            <ResultRow key={m.id} match={m} token={token!} onDone={load} />
          ))
        )}
      </section>

      {finished.length > 0 && (
        <section className="mt-6 space-y-3">
          <h2 className="text-sm font-bold text-gray-500">已結算 ({finished.length})</h2>
          {finished.map((m) => (
            <ResultRow key={m.id} match={m} token={token!} onDone={load} finished />
          ))}
        </section>
      )}
    </main>
  );
}

function NoPermission() {
  return (
    <main className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-100 text-gray-400">
        <Lock size={28} />
      </div>
      <h1 className="mt-4 text-lg font-bold text-gray-800">需要管理者權限</h1>
      <p className="mt-1 max-w-xs text-sm text-gray-400">
        此頁僅供管理者使用。請以管理者帳號登入。
      </p>
    </main>
  );
}

function ResultRow({
  match,
  token,
  onDone,
  finished = false,
}: {
  match: Match;
  token: string;
  onDone: () => void;
  finished?: boolean;
}) {
  const isKnockout = match.stage !== "group";
  const [home, setHome] = useState(match.home_score?.toString() ?? "");
  const [away, setAway] = useState(match.away_score?.toString() ?? "");
  const [adv, setAdv] = useState<"home" | "away" | "">(
    match.advancing_team === "home" || match.advancing_team === "away"
      ? match.advancing_team
      : ""
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (home === "" || away === "") return setErr("請輸入雙方比分");
    if (isKnockout && !adv) return setErr("淘汰賽請選擇晉級隊伍");
    setBusy(true);
    setErr(null);
    try {
      await api.matches.updateResult(
        match.id,
        {
          home_score: Number(home),
          away_score: Number(away),
          advancing_team: isKnockout && adv !== "" ? adv : null,
        },
        token
      );
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "更新失敗");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            {STAGE_LABEL[match.stage]}
          </span>
          {finished && (
            <span className="flex items-center gap-0.5 rounded-md bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-600">
              <Check size={11} />已結算
            </span>
          )}
        </span>
        <span className="text-xs text-gray-400">{formatKickoff(match.kickoff_time)}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="flex-1 text-right text-sm font-semibold">
          {flagEmoji(match.home_team_code)} {match.home_team}
        </span>
        <input
          type="number"
          min={0}
          value={home}
          onChange={(e) => setHome(e.target.value)}
          className="w-12 rounded-lg border border-gray-200 py-1.5 text-center text-sm outline-none focus:border-emerald-500"
        />
        <span className="text-gray-300">:</span>
        <input
          type="number"
          min={0}
          value={away}
          onChange={(e) => setAway(e.target.value)}
          className="w-12 rounded-lg border border-gray-200 py-1.5 text-center text-sm outline-none focus:border-emerald-500"
        />
        <span className="flex-1 text-sm font-semibold">
          {match.away_team} {flagEmoji(match.away_team_code)}
        </span>
      </div>

      {isKnockout && (
        <div className="mt-2 flex gap-2">
          {(["home", "away"] as const).map((side) => (
            <button
              key={side}
              onClick={() => setAdv(side)}
              className={`flex-1 rounded-lg py-1 text-xs font-medium transition ${
                adv === side ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-500"
              }`}
            >
              {side === "home" ? match.home_team : match.away_team} 晉級
            </button>
          ))}
        </div>
      )}

      {err && <p className="mt-2 text-xs font-medium text-red-500">{err}</p>}

      <button
        onClick={submit}
        disabled={busy}
        className={`mt-2 w-full rounded-lg py-2 text-sm font-bold text-white disabled:opacity-50 ${
          finished ? "bg-gray-500" : "bg-emerald-600"
        }`}
      >
        {busy ? "處理中…" : finished ? "修正並重新結算" : "結算"}
      </button>
    </div>
  );
}

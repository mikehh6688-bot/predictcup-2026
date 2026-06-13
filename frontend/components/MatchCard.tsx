"use client";

import { Clock, Flame } from "lucide-react";
import type { Match } from "@/lib/types";
import { FLAG, STAGE_LABEL } from "@/lib/constants";
import { formatKickoff } from "@/lib/format";
import AiBar from "./AiBar";

export default function MatchCard({
  match,
  onBet,
}: {
  match: Match;
  onBet?: (match: Match) => void;
}) {
  const isFinished = match.status === "finished";
  const isLive = match.status === "live";

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
      {/* 頂列：階段標籤 + 倍率 + 狀態 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            {STAGE_LABEL[match.stage]}
          </span>
          {match.multiplier > 1 && (
            <span className="flex items-center gap-0.5 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-600">
              <Flame size={12} />×{match.multiplier}
            </span>
          )}
        </div>
        <StatusPill status={match.status} kickoff={match.kickoff_time} />
      </div>

      {/* 對戰 */}
      <div className="flex items-center justify-between gap-2">
        <TeamSide
          name={match.home_team}
          code={match.home_team_code}
          align="left"
        />
        <div className="flex shrink-0 flex-col items-center px-1">
          {isFinished ? (
            <span className="text-xl font-bold tabular-nums text-gray-900">
              {match.home_score} <span className="text-gray-300">:</span>{" "}
              {match.away_score}
            </span>
          ) : (
            <span className="text-sm font-bold text-gray-300">VS</span>
          )}
        </div>
        <TeamSide
          name={match.away_team}
          code={match.away_team_code}
          align="right"
        />
      </div>

      {/* AI 勝率長條圖 */}
      <div className="mt-4">
        <AiBar prediction={match.ai_prediction} showDraw={match.stage === "group"} />
      </div>

      {/* CTA */}
      {!isFinished && (
        <button
          onClick={() => onBet?.(match)}
          className="mt-4 w-full rounded-xl bg-emerald-600 py-2.5 text-sm font-semibold text-white shadow-sm transition active:scale-[0.99] disabled:opacity-50"
          disabled={isLive || !onBet}
        >
          {isLive ? "已鎖盤" : "立即下注"}
        </button>
      )}
    </div>
  );
}

function TeamSide({
  name,
  code,
  align,
}: {
  name: string;
  code: string | null;
  align: "left" | "right";
}) {
  return (
    <div
      className={`flex flex-1 items-center gap-2 ${
        align === "right" ? "flex-row-reverse text-right" : ""
      }`}
    >
      <span className="text-3xl leading-none">{code ? FLAG[code] ?? "🏳️" : "🏳️"}</span>
      <span className="text-sm font-semibold text-gray-800">{name}</span>
    </div>
  );
}

function StatusPill({ status, kickoff }: { status: Match["status"]; kickoff: string }) {
  if (status === "live") {
    return (
      <span className="flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-600">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        進行中
      </span>
    );
  }
  if (status === "finished") {
    return (
      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
        已完賽
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-gray-500">
      <Clock size={12} />
      {formatKickoff(kickoff)}
    </span>
  );
}

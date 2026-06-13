"use client";

import { useState } from "react";
import { X, Zap, ShieldCheck, Flame } from "lucide-react";
import type { Match, BetChoice, User } from "@/lib/types";
import { FLAG, STAGE_LABEL } from "@/lib/constants";
import { api, ApiError } from "@/lib/api";

export default function BettingModal({
  match,
  user,
  token,
  onClose,
  onPlaced,
}: {
  match: Match;
  user: User;
  token: string;
  onClose: () => void;
  onPlaced: () => void;
}) {
  const isKnockout = match.stage !== "group";
  const [choice, setChoice] = useState<BetChoice | null>(null);
  const [homeScore, setHomeScore] = useState("");
  const [awayScore, setAwayScore] = useState("");
  const [useDouble, setUseDouble] = useState(false);
  const [useInsurance, setUseInsurance] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 道具互斥：開一個自動關另一個
  const toggleDouble = () => {
    setUseDouble((v) => {
      if (!v) setUseInsurance(false);
      return !v;
    });
  };
  const toggleInsurance = () => {
    setUseInsurance((v) => {
      if (!v) setUseDouble(false);
      return !v;
    });
  };

  const choices: { key: BetChoice; label: string }[] = isKnockout
    ? [
        { key: "home", label: `${match.home_team} 晉級` },
        { key: "away", label: `${match.away_team} 晉級` },
      ]
    : [
        { key: "home", label: "主勝" },
        { key: "draw", label: "和局" },
        { key: "away", label: "客勝" },
      ];

  const hasExact = homeScore !== "" && awayScore !== "";

  async function submit() {
    if (!choice) {
      setError("請先選擇預測結果");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.bets.place(
        {
          match_id: match.id,
          predicted_result: choice,
          predicted_home_score: hasExact ? Number(homeScore) : null,
          predicted_away_score: hasExact ? Number(awayScore) : null,
          use_double_card: useDouble,
          use_insurance_card: useInsurance,
        },
        token
      );
      onPlaced();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "下注失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40">
      <div className="w-full max-w-app rounded-t-2xl bg-white p-5 pb-7 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
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
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={22} />
          </button>
        </div>

        {/* 對戰 */}
        <div className="mb-5 flex items-center justify-center gap-3 text-base font-bold">
          <span>
            {match.home_team_code ? FLAG[match.home_team_code] : "🏳️"} {match.home_team}
          </span>
          <span className="text-gray-300">VS</span>
          <span>
            {match.away_team} {match.away_team_code ? FLAG[match.away_team_code] : "🏳️"}
          </span>
        </div>

        {/* 勝平負選項 */}
        <p className="mb-2 text-sm font-semibold text-gray-700">預測結果</p>
        <div className={`mb-5 grid gap-2 ${isKnockout ? "grid-cols-2" : "grid-cols-3"}`}>
          {choices.map((c) => (
            <button
              key={c.key}
              onClick={() => setChoice(c.key)}
              className={`rounded-xl border py-3 text-sm font-semibold transition ${
                choice === c.key
                  ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                  : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* 精準比分（選填） */}
        <p className="mb-2 text-sm font-semibold text-gray-700">
          精準比分 <span className="font-normal text-gray-400">選填 · 命中 +50</span>
        </p>
        <div className="mb-5 flex items-center justify-center gap-3">
          <ScoreInput value={homeScore} onChange={setHomeScore} label={match.home_team} />
          <span className="text-xl font-bold text-gray-300">:</span>
          <ScoreInput value={awayScore} onChange={setAwayScore} label={match.away_team} />
        </div>

        {/* 道具（互斥） */}
        <p className="mb-2 text-sm font-semibold text-gray-700">
          道具 <span className="font-normal text-gray-400">兩者擇一</span>
        </p>
        <div className="mb-5 grid grid-cols-2 gap-2">
          <ItemToggle
            active={useDouble}
            disabled={user.double_cards < 1 && !useDouble}
            onClick={toggleDouble}
            icon={<Zap size={16} />}
            label="翻倍卡"
            count={user.double_cards}
            color="amber"
          />
          <ItemToggle
            active={useInsurance}
            disabled={user.insurance_cards < 1 && !useInsurance}
            onClick={toggleInsurance}
            icon={<ShieldCheck size={16} />}
            label="保險卡"
            count={user.insurance_cards}
            color="sky"
          />
        </div>

        {error && (
          <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-600">
            {error}
          </p>
        )}

        <button
          onClick={submit}
          disabled={submitting || !choice}
          className="w-full rounded-xl bg-emerald-600 py-3 text-sm font-bold text-white shadow-sm transition active:scale-[0.99] disabled:opacity-50"
        >
          {submitting ? "下注中…" : "確認下注"}
        </button>
      </div>
    </div>
  );
}

function ScoreInput({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <input
        type="number"
        min={0}
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="-"
        className="h-14 w-16 rounded-xl border border-gray-200 text-center text-2xl font-bold text-gray-800 outline-none focus:border-emerald-500"
      />
      <span className="max-w-16 truncate text-[11px] text-gray-400">{label}</span>
    </div>
  );
}

function ItemToggle({
  active,
  disabled,
  onClick,
  icon,
  label,
  count,
  color,
}: {
  active: boolean;
  disabled: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count: number;
  color: "amber" | "sky";
}) {
  const activeCls =
    color === "amber"
      ? "border-amber-500 bg-amber-50 text-amber-700"
      : "border-sky-500 bg-sky-50 text-sky-700";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-between rounded-xl border px-3 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
        active ? activeCls : "border-gray-200 bg-white text-gray-600"
      }`}
    >
      <span className="flex items-center gap-1.5">
        {icon}
        {label}
      </span>
      <span className="text-xs text-gray-400">×{count}</span>
    </button>
  );
}

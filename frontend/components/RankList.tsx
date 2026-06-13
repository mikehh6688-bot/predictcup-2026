import { Medal } from "lucide-react";
import type { LeaderboardEntry } from "@/lib/types";

const MEDAL_COLOR: Record<string, string> = {
  gold: "text-yellow-500",
  silver: "text-gray-400",
  bronze: "text-amber-700",
};

export default function RankList({ entries }: { entries: LeaderboardEntry[] }) {
  if (entries.length === 0) {
    return <p className="py-12 text-center text-sm text-gray-400">尚無排名資料</p>;
  }
  return (
    <ul className="space-y-2">
      {entries.map((e) => (
        <li
          key={e.user.id}
          className={`flex items-center gap-3 rounded-xl border bg-white px-4 py-3 shadow-sm ${
            e.is_loser ? "border-red-200" : "border-gray-100"
          }`}
        >
          {/* 名次 / 獎牌 */}
          <div className="flex w-8 shrink-0 justify-center">
            {e.medal ? (
              <Medal size={22} className={MEDAL_COLOR[e.medal]} />
            ) : (
              <span className="text-sm font-bold text-gray-400">{e.rank}</span>
            )}
          </div>

          {/* 使用者 */}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-gray-800">
              {e.user.username}
            </p>
            {e.is_loser && (
              <span className="mt-0.5 inline-block rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-bold text-red-500">
                🍗 輸家請客
              </span>
            )}
          </div>

          {/* 積分 */}
          <span
            className={`shrink-0 text-base font-bold tabular-nums ${
              e.points < 0 ? "text-red-500" : "text-gray-900"
            }`}
          >
            {e.points}
          </span>
        </li>
      ))}
    </ul>
  );
}

import { Zap, ShieldCheck, TrendingUp } from "lucide-react";
import type { User } from "@/lib/types";

export default function PointsCard({ user }: { user: User }) {
  return (
    <div className="rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-500 p-5 text-white shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-emerald-50/90">Hi, {user.username} 👋</p>
          <p className="mt-1 text-xs text-emerald-50/70">目前總積分</p>
          <div className="mt-0.5 flex items-end gap-1.5">
            <span className="text-4xl font-bold leading-none tracking-tight">
              {user.total_points}
            </span>
            <span className="mb-1 text-sm text-emerald-50/80">分</span>
          </div>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/15">
          <TrendingUp size={26} />
        </div>
      </div>

      {/* 道具背包 */}
      <div className="mt-4 grid grid-cols-2 gap-2">
        <ItemChip
          icon={<Zap size={16} className="text-amber-300" />}
          label="翻倍卡"
          count={user.double_cards}
        />
        <ItemChip
          icon={<ShieldCheck size={16} className="text-sky-200" />}
          label="保險卡"
          count={user.insurance_cards}
        />
      </div>
    </div>
  );
}

function ItemChip({
  icon,
  label,
  count,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-white/15 px-3 py-2">
      <span className="flex items-center gap-1.5 text-sm">
        {icon}
        {label}
      </span>
      <span className="text-base font-bold">×{count}</span>
    </div>
  );
}

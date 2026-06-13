import { Sparkles } from "lucide-react";
import type { AiPrediction } from "@/lib/types";
import { pct } from "@/lib/format";

/** AI 勝率預測長條圖（主勝 / 和 / 客勝 堆疊條） */
export default function AiBar({
  prediction,
  showDraw = true,
}: {
  prediction: AiPrediction;
  showDraw?: boolean;
}) {
  const home = pct(prediction.home);
  const draw = pct(prediction.draw);
  const away = pct(prediction.away);

  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1 text-xs font-medium text-gray-500">
        <Sparkles size={13} className="text-violet-500" />
        AI 勝率預測
      </div>

      <div className="flex h-2.5 overflow-hidden rounded-full bg-gray-100">
        <div className="bg-emerald-500" style={{ width: `${home}%` }} />
        {showDraw && <div className="bg-gray-300" style={{ width: `${draw}%` }} />}
        <div className="bg-blue-500" style={{ width: `${away}%` }} />
      </div>

      <div className="mt-1.5 flex justify-between text-[11px] font-medium">
        <span className="text-emerald-600">主勝 {home}%</span>
        {showDraw && <span className="text-gray-400">和 {draw}%</span>}
        <span className="text-blue-600">客勝 {away}%</span>
      </div>
    </div>
  );
}

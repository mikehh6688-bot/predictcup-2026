// 顯示格式工具

const WEEK = ["日", "一", "二", "三", "四", "五", "六"];

/** ISO 時間 -> "6/14 (日) 19:00" */
export function formatKickoff(iso: string): string {
  const d = new Date(iso);
  const mm = d.getMonth() + 1;
  const dd = d.getDate();
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${mm}/${dd} (${WEEK[d.getDay()]}) ${hh}:${min}`;
}

/** 距開賽倒數，例如 "3 小時後" / "已開賽" */
export function countdown(iso: string, now: Date = new Date()): string {
  const diff = new Date(iso).getTime() - now.getTime();
  if (diff <= 0) return "已開賽";
  const hours = Math.floor(diff / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  if (hours >= 24) return `${Math.floor(hours / 24)} 天後`;
  if (hours >= 1) return `${hours} 小時後`;
  return `${mins} 分鐘後`;
}

/** 0~1 機率 -> 百分比整數字串 */
export function pct(v: number | null): number {
  return v == null ? 0 : Math.round(v * 100);
}

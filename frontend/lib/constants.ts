// 顯示用常數（國旗、階段中文）。Phase 4 後賽事資料改由 API 取得，
// 這裡僅保留前端呈現用的對照表。

// 次國家（無 ISO2 區域指示符）以標籤序列 emoji 表示
const SUBDIVISION: Record<string, string> = {
  ENG: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  SCT: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  WAL: "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
  NIR: "🇬🇧",
};

// 舊版 3 碼對照（向後相容）
const LEGACY3: Record<string, string> = {
  BRA: "🇧🇷", ARG: "🇦🇷", FRA: "🇫🇷", ESP: "🇪🇸", GER: "🇩🇪",
  POR: "🇵🇹", NED: "🇳🇱", JPN: "🇯🇵", USA: "🇺🇸", MEX: "🇲🇽", CAN: "🇨🇦",
};

/** 由國碼取得國旗 emoji：支援次國家碼、ISO2（區域指示符）、舊版 3 碼。 */
export function flagEmoji(code?: string | null): string {
  if (!code) return "🏳️";
  if (SUBDIVISION[code]) return SUBDIVISION[code];
  if (code.length === 2) {
    // ISO2 → 兩個區域指示符（A=0x1F1E6）
    return code
      .toUpperCase()
      .replace(/[A-Z]/g, (c) => String.fromCodePoint(0x1f1e6 + c.charCodeAt(0) - 65));
  }
  return LEGACY3[code] ?? "🏳️";
}

export const STAGE_LABEL: Record<string, string> = {
  group: "小組賽",
  round_of_32: "32 強",
  round_of_16: "16 強",
  quarter_final: "8 強",
  semi_final: "4 強",
  final: "決賽",
};

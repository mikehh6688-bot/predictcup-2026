// 顯示用常數（國旗、階段中文）。Phase 4 後賽事資料改由 API 取得，
// 這裡僅保留前端呈現用的對照表。

/** 國旗 emoji 對照（ISO 國碼） */
export const FLAG: Record<string, string> = {
  BRA: "🇧🇷",
  ARG: "🇦🇷",
  FRA: "🇫🇷",
  ENG: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  ESP: "🇪🇸",
  GER: "🇩🇪",
  POR: "🇵🇹",
  NED: "🇳🇱",
  JPN: "🇯🇵",
  USA: "🇺🇸",
  MEX: "🇲🇽",
  CAN: "🇨🇦",
};

export const STAGE_LABEL: Record<string, string> = {
  group: "小組賽",
  round_of_16: "16 強",
  quarter_final: "8 強",
  semi_final: "4 強",
  final: "決賽",
};

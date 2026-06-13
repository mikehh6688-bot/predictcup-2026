"use client";

import { Loader2, WifiOff, LogIn } from "lucide-react";

export function Spinner({ label = "載入中…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-gray-400">
      <Loader2 className="animate-spin" size={26} />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <WifiOff size={26} className="text-gray-300" />
      <p className="max-w-xs text-sm text-gray-500">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-600"
        >
          重試
        </button>
      )}
    </div>
  );
}

export function LoginPrompt({ note }: { note?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-gray-200 bg-white py-10 text-center">
      <LogIn size={24} className="text-emerald-500" />
      <p className="text-sm text-gray-500">{note ?? "請先登入以使用此功能"}</p>
      <a
        href="/profile"
        className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white"
      >
        前往登入
      </a>
    </div>
  );
}

import type { Metadata, Viewport } from "next";
import "./globals.css";
import BottomNav from "@/components/BottomNav";
import { SessionProvider } from "@/components/SessionProvider";

export const metadata: Metadata = {
  title: "PredictCup 2026",
  description: "世界盃賽事預測 · 動態積分 · 私房聯賽",
};

export const viewport: Viewport = {
  themeColor: "#059669",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-Hant">
      <body>
        <SessionProvider>
          {/* Mobile-first：置中容器 + 底部留白給導覽列 */}
          <div className="mx-auto min-h-screen max-w-app bg-gray-50 pb-20 shadow-sm">
            {children}
          </div>
          <BottomNav />
        </SessionProvider>
      </body>
    </html>
  );
}

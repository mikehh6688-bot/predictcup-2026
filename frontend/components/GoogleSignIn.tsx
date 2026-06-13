"use client";

import { useEffect, useRef } from "react";

// Google Identity Services 全域物件（由外部 script 注入）
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (cfg: {
            client_id: string;
            callback: (resp: { credential: string }) => void;
          }) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
        };
      };
    };
  }
}

const GIS_SRC = "https://accounts.google.com/gsi/client";

/**
 * 只有設定了 NEXT_PUBLIC_GOOGLE_CLIENT_ID 時才渲染 Google 登入按鈕；
 * 取得 id_token 後交給 onCredential（→ 後端 /auth/sso 換本地 JWT）。
 */
export default function GoogleSignIn({
  onCredential,
}: {
  onCredential: (idToken: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || !ref.current) return;

    function init() {
      if (!window.google || !ref.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId!,
        callback: (resp) => onCredential(resp.credential),
      });
      window.google.accounts.id.renderButton(ref.current, {
        theme: "outline",
        size: "large",
        width: 280,
        text: "signin_with",
      });
    }

    if (window.google) {
      init();
      return;
    }
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.onload = init;
    document.head.appendChild(script);
  }, [clientId, onCredential]);

  if (!clientId) return null;
  return <div ref={ref} className="flex justify-center" />;
}

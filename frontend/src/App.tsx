import { useEffect, useState } from "react";
import { Analysis } from "./analysis";
import { Chat } from "./chat";

function SourceBanner() {
  const [source, setSource] = useState<string | null>(null);
  useEffect(() => {
    fetch("/api/quote/AAPL")
      .then((r) => r.json())
      .then((q) => setSource(q.source))
      .catch(() => {});
  }, []);
  if (source !== "yfinance") return null;
  return (
    <div style={{ padding: "8px 20px", background: "#3d2b00", color: "#f0d68a", fontSize: 13 }}>
      Fiyat verisi Yahoo'dan kazınıyor (resmî değil, kırılgan). Ücretsiz{" "}
      <a href="https://alpaca.markets" target="_blank" rel="noreferrer" style={{ color: "#f0d68a" }}>
        Alpaca
      </a>{" "}
      key'i ile resmî veriye geç — <code>SONAR_ALPACA_KEY</code>.
    </div>
  );
}

function IngestBanner() {
  const [state, setState] = useState<{ status: string; progress: number; quarter: string } | null>(null);
  useEffect(() => {
    const poll = () =>
      fetch("/api/ingest/status")
        .then((r) => r.json())
        .then(setState)
        .catch(() => {});
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);
  if (!state || state.status === "ready" || state.status === "idle") return null;
  const text =
    state.status === "error"
      ? "13F verisi indirilemedi — büyük oyuncular bölümü şu an yok."
      : `13F verisi indiriliyor${state.quarter ? ` (${state.quarter})` : ""} — %${Math.round(state.progress * 100)}`;
  return (
    <div style={{ padding: "6px 20px", background: "#12261f", color: "#7ee787", fontSize: 13 }}>{text}</div>
  );
}

export function App() {
  const [tab, setTab] = useState<"analysis" | "chat">("analysis");
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0d1117", color: "#e6edf3" }}>
      <header style={{ display: "flex", gap: 16, alignItems: "center", padding: "12px 20px", borderBottom: "1px solid #21262d" }}>
        <b>Sonar</b>
        {(["analysis", "chat"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: "none", border: 0, cursor: "pointer", padding: "4px 8px",
              color: tab === t ? "#e6edf3" : "#7d8590",
              borderBottom: tab === t ? "2px solid #1f6feb" : "2px solid transparent",
            }}
          >
            {t === "analysis" ? "Derin Analiz" : "Sohbet"}
          </button>
        ))}
      </header>
      <SourceBanner />
      <IngestBanner />
      <div style={{ flex: 1, overflowY: "auto" }}>{tab === "analysis" ? <Analysis /> : <Chat />}</div>
    </div>
  );
}

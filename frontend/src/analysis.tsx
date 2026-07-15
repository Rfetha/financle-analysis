import { useState } from "react";
import { MessagePart, type Part } from "./parts";
import { streamSSE } from "./chat";

export function Analysis() {
  const [ticker, setTicker] = useState("");
  const [parts, setParts] = useState<Part[]>([]);
  const [busy, setBusy] = useState(false);

  async function run() {
    const t = ticker.trim().toUpperCase();
    if (!t || busy) return;
    setParts([]);
    setBusy(true);
    try {
      await streamSSE("/api/analyze", { ticker: t }, (type, data) => {
        setParts((prev) => {
          if (type === "text-delta") {
            const last = prev[prev.length - 1];
            if (last?.kind === "text") {
              return [...prev.slice(0, -1), { kind: "text", text: last.text + data.delta }];
            }
            return [...prev, { kind: "text", text: data.delta }];
          }
          if (type === "analysis-step")
            return [...prev, { kind: "analysis_step", section: data.section, ok: data.ok }];
          if (type === "chart")
            return [...prev, { kind: "chart", ticker: data.ticker, range: data.range, interval: data.interval }];
          if (type === "error") return [...prev, { kind: "error", message: data.message }];
          return prev;
        });
      });
    } catch (e) {
      setParts((p) => [...p, { kind: "error", message: String(e) }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Sembol — ör. NVDA"
          style={{ flex: 1, padding: "10px 12px", borderRadius: 8, border: "1px solid #30363d", background: "#0d1117", color: "#e6edf3" }}
        />
        <button
          onClick={run}
          disabled={busy}
          style={{ padding: "10px 18px", borderRadius: 8, border: 0, background: "#1f6feb", color: "#fff", cursor: "pointer" }}
        >
          {busy ? "Analiz ediliyor…" : "Derin analiz"}
        </button>
      </div>
      <div style={{ marginTop: 16 }}>
        {parts.map((p, i) => (
          <MessagePart key={i} part={p} />
        ))}
      </div>
    </div>
  );
}

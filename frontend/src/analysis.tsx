import { useState } from "react";
import { Chart } from "./chart";
import { streamSSE } from "./chat";

// Faz A bölümleri (Faz B'de big_players eklenir). Baştan hepsi "toplanıyor" gösterilir ki
// kullanıcı — özellikle peers'ın ~20 sn'sinde — donuk ekrana bakmasın (akış hissi).
const SECTIONS = [
  { key: "macro", label: "Makro ortam" },
  { key: "fundamentals", label: "Şirket temeli" },
  { key: "technicals", label: "Teknik" },
  { key: "news", label: "Haber" },
  { key: "peers", label: "Rakipler" },
  { key: "big_players", label: "Büyük oyuncular" },
];

type SecStatus = "pending" | "done" | "failed";

function StepChip({ label, status }: { label: string; status: SecStatus }) {
  const glyph = status === "done" ? "✓" : status === "failed" ? "⚠" : null;
  const color = status === "done" ? "#3fb950" : status === "failed" ? "#d29922" : "#7d8590";
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "5px 10px", borderRadius: 999, fontSize: 12.5,
        border: `1px solid ${status === "pending" ? "#30363d" : color + "55"}`,
        background: status === "pending" ? "#161b22" : color + "14",
        color: status === "pending" ? "#8b949e" : "#e6edf3",
      }}
    >
      {status === "pending" ? (
        <span className="sonar-pulse" style={{ width: 7, height: 7, borderRadius: 999, background: "#58a6ff" }} />
      ) : (
        <span style={{ color }}>{glyph}</span>
      )}
      {label}
      {status === "failed" && <span style={{ color: "#d29922", opacity: 0.8 }}>· veri yok</span>}
    </div>
  );
}

export function Analysis() {
  const [ticker, setTicker] = useState("");
  const [busy, setBusy] = useState(false);
  const [sections, setSections] = useState<Record<string, SecStatus>>({});
  const [chart, setChart] = useState<{ ticker: string; range: string; interval: string } | null>(null);
  const [writing, setWriting] = useState(false);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");

  const started = busy || report || error || chart;

  async function run() {
    const t = ticker.trim().toUpperCase();
    if (!t || busy) return;
    setBusy(true);
    setSections(Object.fromEntries(SECTIONS.map((s) => [s.key, "pending"])) as Record<string, SecStatus>);
    setChart(null);
    setWriting(false);
    setReport("");
    setError("");
    try {
      await streamSSE("/api/analyze", { ticker: t }, (type, data) => {
        if (type === "analysis-step") {
          setSections((s) => ({ ...s, [data.section]: data.ok ? "done" : "failed" }));
        } else if (type === "chart") {
          setChart({ ticker: data.ticker, range: data.range, interval: data.interval });
          setWriting(true); // grafik geldi; artık model sentezini bekliyoruz
        } else if (type === "text-delta") {
          setWriting(false);
          setReport((r) => r + data.delta);
        } else if (type === "error") {
          setWriting(false);
          setError(data.message);
        }
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
      setWriting(false);
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: "0 auto", width: "100%" }}>
      <style>{`
        @keyframes sonarPulse { 0%,100% { opacity: 1 } 50% { opacity: 0.25 } }
        .sonar-pulse { animation: sonarPulse 1s ease-in-out infinite; display: inline-block; }
        @keyframes sonarBlink { 0%,100% { opacity: 1 } 50% { opacity: 0 } }
        .sonar-cursor { animation: sonarBlink 1s step-start infinite; }
      `}</style>

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
          style={{ padding: "10px 18px", borderRadius: 8, border: 0, background: busy ? "#1f6feb99" : "#1f6feb", color: "#fff", cursor: busy ? "default" : "pointer" }}
        >
          {busy ? "Analiz ediliyor…" : "Derin analiz"}
        </button>
      </div>

      {started && (
        <div style={{ marginTop: 16 }}>
          {/* İlerleme rayı — baştan tüm bölümler görünür, biri tamamlanınca ✓/⚠ olur */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {SECTIONS.map((s) => (
              <StepChip key={s.key} label={s.label} status={sections[s.key] ?? "pending"} />
            ))}
          </div>

          {chart && (
            <div style={{ marginTop: 14 }}>
              <Chart ticker={chart.ticker} range={chart.range} interval={chart.interval} />
            </div>
          )}

          {writing && (
            <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 8, color: "#8b949e", fontSize: 14 }}>
              <span className="sonar-pulse" style={{ width: 8, height: 8, borderRadius: 999, background: "#a371f7" }} />
              Sonar raporu yazıyor…
            </div>
          )}

          {report && (
            <div style={{ marginTop: 14, whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: 14.5 }}>
              {report}
              {busy && <span className="sonar-cursor" style={{ color: "#a371f7" }}>▍</span>}
            </div>
          )}

          {error && (
            <div style={{ marginTop: 14, padding: "10px 12px", borderRadius: 8, background: "#3d1418", border: "1px solid #f8514966", color: "#ff7b72", fontSize: 13.5, whiteSpace: "pre-wrap" }}>
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

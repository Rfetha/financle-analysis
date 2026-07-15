import type { CSSProperties } from "react";
import { Chart } from "./chart";

export type Part =
  | { kind: "text"; text: string }
  | { kind: "tool_call"; name: string; input: unknown; status: "running" | "done" }
  | { kind: "tool_result"; name: string; output: string }
  | { kind: "chart"; ticker: string; range: string; interval: string }
  | { kind: "analysis_step"; section: string; ok: boolean }
  | { kind: "error"; message: string };

const card: CSSProperties = {
  margin: "6px 0", padding: "6px 10px", borderRadius: 8,
  background: "#0d1117", border: "1px solid #21262d", fontSize: 13,
};
const codeStyle: CSSProperties = {
  display: "block", marginTop: 4, color: "#7ee787", fontSize: 12, wordBreak: "break-all",
};

const SECTION_LABEL: Record<string, string> = {
  macro: "Makro", fundamentals: "Temel", technicals: "Teknik",
  news: "Haber", peers: "Rakipler", big_players: "Büyük oyuncular",
};

export const REGISTRY: Record<Part["kind"], (p: Part) => JSX.Element> = {
  text: (p) => <span style={{ whiteSpace: "pre-wrap" }}>{(p as any).text}</span>,
  tool_call: (p) => {
    const t = p as Extract<Part, { kind: "tool_call" }>;
    return (
      <div style={card}>
        <span style={{ opacity: 0.7 }}>{t.status === "running" ? "⏳" : "✓"} tool</span>{" "}
        <b>{t.name}</b>
        <code style={codeStyle}>{JSON.stringify(t.input)}</code>
      </div>
    );
  },
  tool_result: (p) => {
    const t = p as Extract<Part, { kind: "tool_result" }>;
    return (
      <div style={card}>
        <span style={{ opacity: 0.7 }}>↳ {t.name}</span>
        <code style={codeStyle}>{t.output}</code>
      </div>
    );
  },
  chart: (p) => {
    const c = p as Extract<Part, { kind: "chart" }>;
    return <Chart ticker={c.ticker} range={c.range} interval={c.interval} />;
  },
  analysis_step: (p) => {
    const s = p as Extract<Part, { kind: "analysis_step" }>;
    return (
      <div style={{ ...card, opacity: s.ok ? 0.85 : 0.6 }}>
        {s.ok ? "✓" : "⚠"} {SECTION_LABEL[s.section] ?? s.section}
        {!s.ok && <span style={{ color: "#f0883e" }}> — veri yok</span>}
      </div>
    );
  },
  error: (p) => <span style={{ color: "#f87171" }}>{(p as any).message}</span>,
};

export function MessagePart({ part }: { part: Part }) {
  return REGISTRY[part.kind](part);
}

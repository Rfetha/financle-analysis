import { useRef, useState } from "react";
import type { CSSProperties } from "react";

// Asistan turu = tipli "part" listesi (ADR-0008). M1: text · tool_call · tool_result · error.
// M2'de quote-tick/chart part'ları buraya EKLENİR (yeniden yazma değil).
type Part =
  | { kind: "text"; text: string }
  | { kind: "tool_call"; name: string; input: unknown; status: "running" | "done" }
  | { kind: "tool_result"; name: string; output: string }
  | { kind: "error"; message: string };

type Message = { role: "user" | "assistant"; parts: Part[] };

// part-type -> React component registry. AG-UI geçişinde (v2) yalnız yeni tipler eklenir.
const REGISTRY: Record<Part["kind"], (p: Part) => JSX.Element> = {
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
  error: (p) => <span style={{ color: "#f87171" }}>{(p as any).message}</span>,
};

function MessagePart({ part }: { part: Part }) {
  return REGISTRY[part.kind](part);
}

// Sonar SSE stream'ini part-güncellemelerine çevirir (fetch + ReadableStream, ADR-0008:
// EventSource değil — abort/header kontrolü; yarım üretimi sessiz resume etmez).
async function streamChat(message: string, onEvent: (type: string, data: any) => void) {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!resp.ok || !resp.body) throw new Error(`chat hata: ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i);
      buf = buf.slice(i + 2);
      let type = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) type = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onEvent(type, JSON.parse(data));
    }
  }
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Son asistan mesajının part'larını güvenli güncelle (functional update).
  const patchLast = (fn: (parts: Part[]) => Part[]) =>
    setMessages((ms) => {
      const copy = ms.slice();
      const last = copy[copy.length - 1];
      copy[copy.length - 1] = { ...last, parts: fn(last.parts) };
      return copy;
    });

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput("");
    setBusy(true);
    setMessages((ms) => [...ms, { role: "user", parts: [{ kind: "text", text: msg }] }, { role: "assistant", parts: [] }]);
    try {
      await streamChat(msg, (type, data) => {
        if (type === "text-delta") {
          patchLast((parts) => {
            const last = parts[parts.length - 1];
            if (last?.kind === "text") {
              return [...parts.slice(0, -1), { kind: "text", text: last.text + data.delta }];
            }
            return [...parts, { kind: "text", text: data.delta }];
          });
        } else if (type === "tool-call") {
          patchLast((parts) => [...parts, { kind: "tool_call", name: data.name, input: data.input, status: "running" }]);
        } else if (type === "tool-result") {
          patchLast((parts) => {
            const marked = parts.map((p) =>
              p.kind === "tool_call" && p.status === "running" ? { ...p, status: "done" as const } : p,
            );
            return [...marked, { kind: "tool_result", name: data.name, output: data.output }];
          });
        } else if (type === "error") {
          patchLast((parts) => [...parts, { kind: "error", message: data.message }]);
        }
      });
    } catch (e) {
      patchLast((parts) => [...parts, { kind: "error", message: String(e) }]);
    } finally {
      setBusy(false);
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0d1117", color: "#e6edf3" }}>
      <header style={{ padding: "12px 20px", borderBottom: "1px solid #21262d", fontWeight: 600 }}>Sonar</header>
      <div style={{ flex: 1, overflowY: "auto", padding: 20, maxWidth: 760, width: "100%", margin: "0 auto" }}>
        {messages.length === 0 && <p style={{ opacity: 0.5 }}>Bir hisse sor — ör. "AAPL fiyatı ne?"</p>}
        {messages.map((m, i) => (
          <div key={i} style={{ margin: "12px 0", textAlign: m.role === "user" ? "right" : "left" }}>
            <div
              style={{
                display: "inline-block",
                maxWidth: "85%",
                textAlign: "left",
                padding: "8px 12px",
                borderRadius: 10,
                background: m.role === "user" ? "#1f6feb" : "#161b22",
              }}
            >
              {m.parts.map((p, j) => (
                <MessagePart key={j} part={p} />
              ))}
              {m.role === "assistant" && m.parts.length === 0 && <span style={{ opacity: 0.5 }}>…</span>}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div style={{ display: "flex", gap: 8, padding: 16, borderTop: "1px solid #21262d", maxWidth: 760, width: "100%", margin: "0 auto", boxSizing: "border-box" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Sonar'a sor…"
          style={{ flex: 1, padding: "10px 12px", borderRadius: 8, border: "1px solid #30363d", background: "#0d1117", color: "#e6edf3" }}
        />
        <button onClick={send} disabled={busy} style={{ padding: "10px 18px", borderRadius: 8, border: 0, background: "#238636", color: "#fff", cursor: "pointer" }}>
          {busy ? "…" : "Gönder"}
        </button>
      </div>
    </div>
  );
}

const card: CSSProperties = { margin: "6px 0", padding: "6px 10px", borderRadius: 8, background: "#0d1117", border: "1px solid #21262d", fontSize: 13 };
const codeStyle: CSSProperties = { display: "block", marginTop: 4, color: "#7ee787", fontSize: 12, wordBreak: "break-all" };

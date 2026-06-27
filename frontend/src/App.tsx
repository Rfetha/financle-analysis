import { useState } from "react";

type Quote = { ticker: string; price: string; currency: string; change_pct: number; source: string };

export function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function lookup() {
    setError(null);
    setQuote(null);
    try {
      const resp = await fetch(`/api/quote/${encodeURIComponent(ticker)}`);
      if (!resp.ok) { setError(`hata: ${resp.status}`); return; }
      setQuote(await resp.json());
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 480, margin: "40px auto" }}>
      <h1>Sonar</h1>
      <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="AAPL" />
      <button onClick={lookup}>Fiyat</button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {quote && (
        <p>
          <b>{quote.ticker}</b>: {quote.price} {quote.currency}{" "}
          <span style={{ color: quote.change_pct >= 0 ? "green" : "crimson" }}>
            ({quote.change_pct >= 0 ? "+" : ""}{quote.change_pct}%)
          </span>{" "}
          <small>· {quote.source}</small>
        </p>
      )}
    </div>
  );
}

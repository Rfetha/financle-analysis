"""Teknik göstergeler — elle yazılır (ADR-0006: TA-Lib/pandas-ta yok).

Saf: I/O yok, market bilmez. Her market için aynı matematik → çekirdekte, plugin'de değil.
"""

import numpy as np

from sonar.domain.candle import Candle


def _need(values: list[float], n: int) -> None:
    if len(values) < n:
        raise ValueError(f"yetersiz veri: {len(values)} < {n}")


def rsi(closes: list[float], period: int = 14) -> float:
    """Wilder RSI. İlk ortalama = basit ortalama, sonrası Wilder yumuşatması."""
    _need(closes, period + 1)
    deltas = np.diff(np.asarray(closes, dtype=float))
    gains = np.clip(deltas, 0, None)
    losses = -np.clip(deltas, None, 0)
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    for g, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def ema(values: list[float], period: int) -> float:
    """Son EMA değeri. Tohum = ilk `period` değerin SMA'sı."""
    _need(values, period)
    k = 2 / (period + 1)
    out = float(np.mean(values[:period]))
    for v in values[period:]:
        out = v * k + out * (1 - k)
    return out


def _ema_series(values: list[float], period: int) -> list[float]:
    _need(values, period)
    k = 2 / (period + 1)
    out = [float(np.mean(values[:period]))]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    _need(closes, slow + signal)
    fast_s = _ema_series(closes, fast)
    slow_s = _ema_series(closes, slow)
    # Why: iki seri farklı uzunlukta başlar (fast daha erken tohumlanır) → kuyruktan hizala.
    n = min(len(fast_s), len(slow_s))
    line = [f - s for f, s in zip(fast_s[-n:], slow_s[-n:])]
    signal_line = _ema_series(line, signal)
    return {
        "macd": round(line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(line[-1] - signal_line[-1], 4),
    }


def bollinger(closes: list[float], period: int = 20, k: float = 2.0) -> dict:
    _need(closes, period)
    window = np.asarray(closes[-period:], dtype=float)
    mid = float(window.mean())
    sd = float(window.std())  # nüfus std (ddof=0) — Bollinger'ın orijinal tanımı
    return {
        "mid": round(mid, 4),
        "upper": round(mid + k * sd, 4),
        "lower": round(mid - k * sd, 4),
    }


def support_resistance(candles: list[Candle], lookback: int = 60) -> dict:
    """En basit ve dürüst tanım: pencere içindeki uç noktalar.
    ponytail: pivot/fractal algoritmasına ancak bu yetersiz kalırsa geçilir."""
    if not candles:
        raise ValueError("yetersiz veri: 0 mum")
    window = candles[-lookback:]
    return {
        "support": round(min(c.low for c in window), 4),
        "resistance": round(max(c.high for c in window), 4),
    }


def obv(candles: list[Candle]) -> float:
    """On-Balance Volume: kapanış yükseldiyse hacim eklenir, düştüyse çıkarılır."""
    _need(candles, 2)
    total = 0.0
    for prev, cur in zip(candles, candles[1:]):
        if cur.close > prev.close:
            total += cur.volume
        elif cur.close < prev.close:
            total -= cur.volume
    return total


def volume_anomaly(candles: list[Candle], window: int = 20) -> float:
    """Son barın hacmi / önceki `window` barın ortalaması. 1.0 = normal, 2.5 = 2.5 katı."""
    _need(candles, window + 1)
    baseline = float(np.mean([c.volume for c in candles[-window - 1 : -1]]))
    if baseline == 0:
        return 0.0
    return round(candles[-1].volume / baseline, 2)


def days_to_cover(shares_short: int, avg_daily_volume: float) -> float | None:
    """Açık short / ortalama günlük hacim — squeeze riskinin standart ölçüsü."""
    if not avg_daily_volume:
        return None
    return round(shares_short / avg_daily_volume, 2)

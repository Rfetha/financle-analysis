import pytest
from sonar.analytics.indicators import (
    bollinger, ema, macd, obv, rsi, support_resistance, volume_anomaly,
)
from sonar.domain.candle import Candle

# Wilder'ın orijinal RSI örneği (New Concepts in Technical Trading Systems, 1978).
# StockCharts'ın yayımladığı standart Wilder veri seti. Bu 15 kapanış için ilk RSI (basit
# 14-ortalama, henüz smoothing yok) = 70.46 (elle doğrulandı: avg_gain=3.34/14, avg_loss=1.40/14).
WILDER = [
    44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
    45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
]


def test_rsi_matches_wilder_reference():
    assert rsi(WILDER, period=14) == pytest.approx(70.46, abs=0.05)


def test_rsi_all_gains_is_100():
    assert rsi([float(i) for i in range(1, 20)], period=14) == pytest.approx(100.0)


def test_rsi_needs_enough_data():
    with pytest.raises(ValueError, match="yetersiz veri"):
        rsi([1.0, 2.0], period=14)


def test_ema_matches_hand_calculation():
    # EMA(3): ilk değer = SMA(3) = 2.0; k = 2/(3+1) = 0.5
    # 4 → 2.0 + 0.5*(4-2.0) = 3.0 ; 5 → 3.0 + 0.5*(5-3.0) = 4.0
    assert ema([1.0, 2.0, 3.0, 4.0, 5.0], period=3) == pytest.approx(4.0)


def test_bollinger_matches_hand_calculation():
    # 5 eşit değer → std = 0 → üç bant da aynı
    out = bollinger([10.0] * 20, period=20, k=2)
    assert out["mid"] == pytest.approx(10.0)
    assert out["upper"] == pytest.approx(10.0)
    assert out["lower"] == pytest.approx(10.0)


def test_bollinger_two_sigma():
    values = [8.0, 12.0] * 10  # ortalama 10, nüfus std = 2
    out = bollinger(values, period=20, k=2)
    assert out["mid"] == pytest.approx(10.0)
    assert out["upper"] == pytest.approx(14.0)
    assert out["lower"] == pytest.approx(6.0)


def test_macd_zero_when_flat():
    out = macd([10.0] * 40)
    assert out["macd"] == pytest.approx(0.0, abs=1e-9)
    assert out["histogram"] == pytest.approx(0.0, abs=1e-9)


def _c(close: float, volume: int = 100) -> Candle:
    return Candle(ts=0, open=close, high=close + 1, low=close - 1, close=close, volume=volume)


def test_support_resistance_uses_window_extremes():
    candles = [_c(10.0), _c(20.0), _c(15.0)]
    out = support_resistance(candles, lookback=3)
    assert out["support"] == pytest.approx(9.0)     # en düşük low
    assert out["resistance"] == pytest.approx(21.0)  # en yüksek high


def test_obv_accumulates_on_up_days():
    # 10 → 11 (yukarı, +200) → 10 (aşağı, -300)
    candles = [_c(10.0, 100), _c(11.0, 200), _c(10.0, 300)]
    assert obv(candles) == pytest.approx(-100.0)


def test_volume_anomaly_ratio():
    candles = [_c(10.0, 100)] * 20 + [_c(10.0, 250)]
    assert volume_anomaly(candles, window=20) == pytest.approx(2.5)

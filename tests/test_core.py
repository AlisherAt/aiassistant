import pandas as pd
import pytest

from app.ai.arbiter import AIArbiter
from app.backtest.engine import BacktestEngine
from app.risk.manager import RiskManager, PositionSizer
from app.trade.lifecycle import TradeLifecycle
from app.notify.telegram_bot import TelegramBot
from app.regime.market_regime import classify_market_regime
from app.strategies.correlation import analyze as analyze_correlation
from app.strategies.ict_smc import _mss_bullish, _fvg_zone, _retest_confirmed


def test_ict_smc_mss_uses_post_sweep_bars():
    df = pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105, 106, 107, 109, 111, 110, 112, 114],
            "high": [100.8, 101.8, 102.8, 103.8, 104.8, 105.8, 106.8, 107.8, 110.0, 112.0, 111.0, 113.0, 115.0],
            "low": [99.2, 100.2, 101.2, 102.2, 103.2, 104.2, 105.2, 98.0, 108.0, 110.0, 109.0, 111.0, 113.0],
            "close": [100.4, 101.4, 102.4, 103.4, 104.4, 105.4, 106.4, 99.0, 109.8, 111.6, 110.2, 112.5, 114.4],
        }
    )

    assert _mss_bullish(df, 7) is True


def test_ict_smc_fvg_is_anchored_to_mss_event():
    df = pd.DataFrame(
        {
            "open": [100, 101, 99, 104, 103, 108],
            "high": [101, 102, 100, 105, 104, 109],
            "low": [99, 100, 98, 103, 102, 107],
            "close": [100.5, 101.5, 99.5, 104.5, 103.5, 108.5],
        }
    )

    zone = _fvg_zone(df, anchor_index=2, direction="bullish")
    assert zone == (102.0, 103.0)


def test_ict_smc_retest_requires_directional_follow_through_after_touch():
    valid = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="5min"),
            "open": [44.6, 44.8, 44.7, 44.9, 45.2],
            "high": [45.0, 45.1, 45.2, 45.5, 45.8],
            "low": [44.4, 44.5, 44.6, 44.8, 45.0],
            "close": [44.5, 44.9, 45.0, 45.3, 45.7],
        }
    )
    invalid = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="5min"),
            "open": [44.6, 44.8, 44.2, 43.9, 43.5],
            "high": [45.0, 45.1, 44.3, 44.1, 43.9],
            "low": [44.4, 44.5, 43.7, 43.4, 42.9],
            "close": [44.5, 44.2, 43.9, 43.6, 43.1],
        }
    )

    assert _retest_confirmed(valid, 44.5, 45.0, "bullish") is True
    assert _retest_confirmed(invalid, 44.5, 45.0, "bullish") is False
    assert _retest_confirmed(valid, 44.5, 45.0, "bearish") is False


def test_market_regime_trending():
    df = pd.DataFrame(
        {
            "close": [100, 101, 102, 103, 104, 105, 106, 108, 110, 112],
            "high": [101, 102, 103, 104, 105, 106, 107, 109, 111, 113],
            "low": [99, 100, 101, 102, 103, 104, 105, 107, 109, 111],
        }
    )
    result = classify_market_regime(df)
    assert result["regime"] == "trending"
    assert isinstance(result["weights"], dict)
    assert result["weights"]["trend_following"] >= 0.3


def test_market_regime_does_not_default_to_news_window():
    df = pd.DataFrame(
        {
            "close": [100, 99, 98, 97, 96, 95, 94, 93, 92, 91],
            "high": [101, 100, 99, 98, 97, 96, 95, 94, 93, 92],
            "low": [99, 98, 97, 96, 95, 94, 93, 92, 91, 90],
        }
    )
    result = classify_market_regime(df)
    assert result["regime"] == "trending"
    assert result["trend_direction"] in {"bearish", "bullish"}
    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-6)


def test_correlation_uses_all_available_sources():
    df = pd.DataFrame({"close": [100, 101, 102, 101, 103]})
    result = analyze_correlation(df, dxy=101.0, real_yield=1.2)
    assert result["direction"] == "buy"
    assert result["strength"] > 0.0


def test_ai_arbiter_builds_strong_buy_decision():
    signals = [
        {"strategy": "trend_following", "direction": "buy", "strength": 0.9, "reason": "uptrend"},
        {"strategy": "mean_reversion", "direction": "neutral", "strength": 0.2, "reason": "mid-range"},
        {"strategy": "correlation", "direction": "buy", "strength": 0.8, "reason": "DXY weak"},
        {"strategy": "ict_smc", "direction": "buy", "strength": 0.7, "reason": "bullish structure"},
    ]
    context = AIArbiter.build_context(signals, regime={"regime": "trending", "weights": {"trend_following": 0.4, "mean_reversion": 0.2, "correlation": 0.25, "ict_smc": 0.15}})
    decision = AIArbiter.decide(context)
    assert decision["direction"] == "buy"
    assert decision["confidence"] >= 0.6
    assert decision["reasoning"]


def test_ai_arbiter_waits_in_news_window_and_uses_russian_reasoning():
    signals = [
        {"strategy": "trend_following", "direction": "sell", "strength": 0.6, "reason": "downtrend"},
        {"strategy": "mean_reversion", "direction": "neutral", "strength": 0.2, "reason": "range"},
        {"strategy": "correlation", "direction": "buy", "strength": 0.65, "reason": "DXY weak"},
        {"strategy": "ict_smc", "direction": "buy", "strength": 0.5, "reason": "structural bullish"},
    ]
    context = AIArbiter.build_context(signals, regime={"regime": "news_window", "weights": {"trend_following": 0.25, "mean_reversion": 0.25, "correlation": 0.25, "ict_smc": 0.25}})
    decision = AIArbiter.decide(context)
    assert decision["direction"] == "wait"
    assert "рус" in decision["reasoning_russian"].lower() or "слаб" in decision["reasoning_russian"].lower() or "жд" in decision["reasoning_russian"].lower()


def test_ai_arbiter_allows_modest_but_clear_consensus():
    signals = [
        {"strategy": "trend_following", "direction": "buy", "strength": 0.55, "reason": "uptrend"},
        {"strategy": "mean_reversion", "direction": "buy", "strength": 0.5, "reason": "oversold"},
        {"strategy": "correlation", "direction": "neutral", "strength": 0.2, "reason": "mixed"},
        {"strategy": "ict_smc", "direction": "buy", "strength": 0.5, "reason": "bullish structure"},
    ]
    context = AIArbiter.build_context(signals, regime={"regime": "trending", "weights": {"trend_following": 0.4, "mean_reversion": 0.2, "correlation": 0.25, "ict_smc": 0.15}})
    decision = AIArbiter.decide(context)
    assert decision["direction"] == "buy"
    assert decision["confidence"] >= 0.5


def test_ai_arbiter_accepts_strong_single_signal():
    signals = [
        {"strategy": "trend_following", "direction": "buy", "strength": 0.92, "reason": "strong impulse"},
        {"strategy": "mean_reversion", "direction": "neutral", "strength": 0.1, "reason": "flat"},
        {"strategy": "correlation", "direction": "neutral", "strength": 0.2, "reason": "mixed"},
        {"strategy": "ict_smc", "direction": "sell", "strength": 0.35, "reason": "minor bearish"},
    ]
    context = AIArbiter.build_context(signals, regime={"regime": "ranging", "weights": {"trend_following": 0.35, "mean_reversion": 0.25, "correlation": 0.25, "ict_smc": 0.15}})
    decision = AIArbiter.decide(context)
    assert decision["direction"] == "buy"
    assert decision["confidence"] >= 0.7


def test_ai_arbiter_accepts_strong_macro_signal_even_without_consensus():
    signals = [
        {"strategy": "trend_following", "direction": "neutral", "strength": 0.1, "reason": "no trend"},
        {"strategy": "mean_reversion", "direction": "neutral", "strength": 0.15, "reason": "flat"},
        {"strategy": "correlation", "direction": "buy", "strength": 0.68, "reason": "macro backdrop supports gold"},
        {"strategy": "ict_smc", "direction": "neutral", "strength": 0.2, "reason": "inactive"},
    ]
    context = AIArbiter.build_context(signals, regime={"regime": "ranging", "weights": {"trend_following": 0.35, "mean_reversion": 0.25, "correlation": 0.25, "ict_smc": 0.15}})
    decision = AIArbiter.decide(context)
    assert decision["direction"] == "buy"
    assert decision["confidence"] >= 0.62


def test_backtest_exposes_detailed_performance_metrics():
    df = pd.DataFrame(
        {
            "close": [100, 101, 102, 103, 104, 105, 106, 108, 109, 111, 113, 114],
            "high": [101, 102, 103, 104, 105, 106, 107, 109, 110, 112, 114, 115],
            "low": [99, 100, 101, 102, 103, 104, 105, 107, 108, 110, 112, 113],
        }
    )
    result = BacktestEngine().run(df, buy_threshold=0.5, sell_threshold=0.5, timeframe="5m")
    assert "trades_detail" in result
    assert "expectancy" in result
    assert "profit_factor" in result
    assert "max_drawdown" in result


def test_telegram_message_formatting():
    bot = TelegramBot(token="abc", chat_id="123")
    formatted = bot.format_signal_message({
        "direction": "buy",
        "confidence": 0.82,
        "regime": "trending",
        "reasoning": "Bullish consensus",
        "data_source": "mt5",
    })
    assert "BUY" in formatted
    assert "0.82" in formatted
    assert "trending" in formatted.lower()


def test_risk_manager_positions_and_exit_flow():
    risk = RiskManager(account_balance=10000, risk_per_trade=0.01, max_daily_loss=0.03)
    size = PositionSizer(risk=risk, entry_price=2000, stop_loss=1960, lot_size=0.01)
    trade = TradeLifecycle(entry_price=2000, stop_loss=1960, take_profit=2100, size=1.0)

    assert size.position_size() > 0
    assert trade.exit_trade("tp_hit", price=2105)["status"] == "closed"
    assert trade.exit_trade("sl_hit", price=1958)["exit_reason"] in {"sl_hit", "tp_hit"}


def test_backtest_exits_on_bar_high_low_not_close_only():
    engine = BacktestEngine()
    position = {"side": "buy", "entry": 100.0, "stop": 99.5, "take_profit": 101.5, "size": 1.0}
    bar = pd.Series({"high": 101.8, "low": 99.4, "close": 100.2})

    pnl, exit_reason = engine._resolve_exit_from_bar(position, bar)

    assert exit_reason == "sl_hit"
    assert pnl == pytest.approx(-0.5)


def test_backtest_returns_summary_stats():
    df = pd.DataFrame(
        {
            "close": [100, 101, 102, 103, 104, 105, 106, 108, 109, 111, 113, 114],
            "high": [101, 102, 103, 104, 105, 106, 107, 109, 110, 112, 114, 115],
            "low": [99, 100, 101, 102, 103, 104, 105, 107, 108, 110, 112, 113],
        }
    )
    result = BacktestEngine().run(df, buy_threshold=0.5, sell_threshold=0.5)
    assert "total_return" in result
    assert "win_rate" in result
    assert "trades" in result
    assert result["trades"] >= 0


def test_news_filter_blocks_high_impact_event():
    df = pd.DataFrame({"close": [100, 101, 102, 101, 103], "high": [101, 102, 103, 102, 104], "low": [99, 100, 101, 100, 102]})
    regime = classify_market_regime(df, {"is_high_impact": True, "impact": "high"})
    assert regime["regime"] == "news_window"

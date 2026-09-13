from __future__ import annotations

import json
from typing import Any

from app.ai.arbiter import AIArbiter
from app.ai.claude_client import ClaudeClient
from app.config import settings
from app.regime.market_regime import classify_market_regime
from app.storage.db import SignalStore
from app.strategies.correlation import analyze as analyze_correlation
from app.strategies.ict_smc import analyze as analyze_ict_smc
from app.strategies.trend_following import analyze as analyze_trend_following


class TradingOrchestrator:
    def __init__(self):
        self.store = SignalStore(settings.db_path)
        self.claude = ClaudeClient(settings.anthropic_api_key)

    @staticmethod
    def _russian_explanation(decision: dict[str, Any], regime: dict[str, Any]) -> str:
        direction = str(decision.get("direction", "wait")).lower()
        confidence = float(decision.get("confidence", 0.0))
        regime_name = regime.get("regime", "unknown")
        if direction == "buy":
            return (
                f"Режим рынка: {regime_name}. Есть бычий консенсус по стратегиям, "
                f"поэтому логика рекомендует покупать при уверенности {confidence:.2f}."
            )
        if direction == "sell":
            return (
                f"Режим рынка: {regime_name}. Преобладает медвежий консенсус, "
                f"поэтому лучше избегать покупки и рассматривать продажу при уверенности {confidence:.2f}."
            )
        return (
            f"Режим рынка: {regime_name}. Консенсус недостаточно сильный, поэтому логика рекомендует ждать "
            f"и не открывать позицию при уверенности {confidence:.2f}."
        )

    def analyze_market(self, df, dxy=None, real_yield=None, economic_event=None):
        regime = classify_market_regime(df, economic_event)

        df_5m = df
        df_15m = df.copy() if df is not None else None
        df_1h = df.copy() if df is not None else None

        if df is not None and len(df) >= 20:
            df_15m = df.iloc[-max(20, len(df)):] if len(df) >= 20 else df
            df_1h = df.iloc[-max(40, len(df)):] if len(df) >= 40 else df

        signals = [
            analyze_trend_following(df_1h, df_15m, df_5m),
            analyze_ict_smc(df_15m, df_5m),
            analyze_correlation(df_5m, dxy=dxy, real_yield=real_yield),
        ]

        context = AIArbiter.build_context(signals, regime=regime)
        decision = AIArbiter.decide(context)
        decision["russian_explanation"] = self._russian_explanation(decision, regime)

        payload = {
            "market_regime": regime,
            "signals": signals,
            "ai_decision": decision,
        }

        if settings.ai_provider == "claude" and settings.anthropic_api_key:
            prompt = self._build_prompt(payload)
            onchain = self.claude.generate(prompt)
            payload["ai_decision"] = {
                **decision,
                **onchain,
                "source": "claude",
                "russian_explanation": self._russian_explanation({**decision, **onchain}, regime),
            }

        self.store.add_signal(
            payload["ai_decision"].get("direction", "wait"),
            float(payload["ai_decision"].get("confidence", 0.0)),
            regime["regime"],
            payload["ai_decision"].get("reasoning", "No reasoning"),
        )

        return payload

    def _build_prompt(self, payload: dict[str, Any]) -> str:
        return f"""
Ты — риск-менеджер и финальный арбитр для торговли золотом.
Твоя задача: определить, следует ли открывать позицию или ждать.

Контекст:
- режим рынка: {payload['market_regime']['regime']}
- веса: {json.dumps(payload['market_regime']['weights'], ensure_ascii=False)}
- сигналы: {json.dumps(payload['signals'], ensure_ascii=False)}

Правила:
1. Если режим рынка = news_window, снижай уверенность и избегай сильных заявлений.
2. Не открывай позицию без согласования минимум двух стратегий.
3. Верни только JSON вида:
{{"direction": "buy|sell|wait", "confidence": 0.0-1.0, "reasoning": "краткое объяснение"}}
"""

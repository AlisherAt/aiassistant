"""AI arbiter that converts strategy outputs into a final trading decision."""


class AIArbiter:
    @staticmethod
    def build_context(signals, regime=None):
        return {
            "signals": signals,
            "regime": regime or {"regime": "trending", "weights": {"trend_following": 0.4, "mean_reversion": 0.2, "correlation": 0.25, "ict_smc": 0.15}},
            "rules": {
                "consensus_threshold": 0.6,
                "news_window_guard": 0.75,
                "veto_rule": "If regime is news_window, only allow entries when the consensus is very strong and the direction is aligned across 2+ core strategies.",
                "priority": ["trend_following", "correlation", "ict_smc"],
            },
        }

    @staticmethod
    def _russian_reasoning(direction, regime_name, buy_score, sell_score, confidence):
        if direction == "buy":
            return (
                f"Режим рынка: {regime_name}. Бычий консенсус сильный: "
                f"суммарный сигнал buy={round(buy_score, 3)}, sell={round(sell_score, 3)}. "
                f"Логика оправдывает покупку, так как несколько ключевых стратегий совпали по направлению при уверенности {round(confidence, 2)}."
            )
        if direction == "sell":
            return (
                f"Режим рынка: {regime_name}. Медвежий консенсус сильный: "
                f"суммарный сигнал sell={round(sell_score, 3)}, buy={round(buy_score, 3)}. "
                f"Логика оправдывает продажу, потому что направление подтверждено несколькими сигналами при уверенности {round(confidence, 2)}."
            )
        return (
            f"Режим рынка: {regime_name}. Консенсус слабый или рынок в новостном окне, поэтому лучше ждать. "
            f"Сигналы buy={round(buy_score, 3)} и sell={round(sell_score, 3)} не дают достаточной силы для входа."
        )

    @staticmethod
    def decide(context):
        weighted_scores = {"buy": 0.0, "sell": 0.0}
        direction_counts = {"buy": 0, "sell": 0, "neutral": 0}
        strong_signals = {"buy": 0.0, "sell": 0.0}
        signals = context.get("signals", [])
        regime = context.get("regime", {})
        regime_name = regime.get("regime", "unknown")
        weights = regime.get("weights", {})

        for signal in signals:
            name = signal.get("strategy", "unknown")
            direction = signal.get("direction", "neutral")
            strength = float(signal.get("strength", 0.0))
            weight = weights.get(name, 0.25)
            if direction == "buy":
                weighted_scores["buy"] += strength * weight
                direction_counts["buy"] += 1
                strong_signals["buy"] = max(strong_signals["buy"], strength)
            elif direction == "sell":
                weighted_scores["sell"] += strength * weight
                direction_counts["sell"] += 1
                strong_signals["sell"] = max(strong_signals["sell"], strength)
            else:
                direction_counts["neutral"] += 1

        buy_score = weighted_scores["buy"]
        sell_score = weighted_scores["sell"]
        total = buy_score + sell_score
        score_gap = abs(buy_score - sell_score)
        buy_count = direction_counts["buy"]
        sell_count = direction_counts["sell"]
        buy_strong = strong_signals["buy"]
        sell_strong = strong_signals["sell"]

        single_signal_threshold = 0.62
        if regime_name == "news_window":
            threshold = 0.68
            if buy_score >= threshold and buy_score >= sell_score * 1.18 and buy_count >= 2:
                direction = "buy"
                confidence = min(0.96, max(0.56, buy_score / max(total + 0.2, 0.2)))
            elif sell_score >= threshold and sell_score >= buy_score * 1.18 and sell_count >= 2:
                direction = "sell"
                confidence = min(0.96, max(0.56, sell_score / max(total + 0.2, 0.2)))
            else:
                direction = "wait"
                confidence = 0.28
        else:
            strong_single_buy = buy_strong >= single_signal_threshold and buy_score >= 0.14
            strong_single_sell = sell_strong >= single_signal_threshold and sell_score >= 0.14
            if strong_single_buy or (
                buy_score >= 0.24 and buy_score >= sell_score and (score_gap >= 0.02 or buy_count >= 2)
            ):
                direction = "buy"
                confidence = min(0.96, max(0.52, buy_score / max(total + 0.25, 0.25)))
                if strong_single_buy:
                    confidence = max(confidence, 0.7)
            elif strong_single_sell or (
                sell_score >= 0.24 and sell_score >= buy_score and (score_gap >= 0.02 or sell_count >= 2)
            ):
                direction = "sell"
                confidence = min(0.96, max(0.52, sell_score / max(total + 0.25, 0.25)))
                if strong_single_sell:
                    confidence = max(confidence, 0.7)
            else:
                direction = "wait"
                confidence = 0.35

        reasoning = (
            f"Regime: {regime_name}. "
            f"Consensus leans {direction}. "
            f"Weighted buy={round(buy_score, 3)}, sell={round(sell_score, 3)}. "
            f"This is a structured final decision from the strategy stack."
        )
        reasoning_russian = AIArbiter._russian_reasoning(direction, regime_name, buy_score, sell_score, confidence)

        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "reasoning": reasoning,
            "reasoning_russian": reasoning_russian,
        }

from __future__ import annotations

import json
import os

import requests


class ClaudeClient:
    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    def generate(self, prompt: str) -> dict:
        if not self.api_key:
            return {
                "direction": "wait",
                "confidence": 0.3,
                "reasoning": "AI provider key is missing; local fallback used.",
            }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]
            return json.loads(content)
        except Exception:
            return {
                "direction": "wait",
                "confidence": 0.3,
                "reasoning": "AI request failed; local fallback used.",
            }

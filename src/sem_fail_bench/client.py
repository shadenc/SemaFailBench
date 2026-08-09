"""OpenAI-compatible client for a vLLM (or any /v1/chat/completions) server."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


class ServingClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("SFB_BASE_URL") or "http://127.0.0.1:8000/v1").rstrip(
            "/"
        )
        self.api_key = api_key or os.getenv("SFB_API_KEY") or "EMPTY"
        self.model = model or os.getenv("SFB_MODEL") or "Qwen/Qwen2.5-7B-Instruct"
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        url = f"{root}/health"
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            return {
                "ok": response.status_code == 200,
                "status_code": response.status_code,
                "text": response.text[:500],
            }

    def chat(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        top_p: float | None = None,
        max_tokens: int = 256,
        seed: int | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if seed is not None:
            payload["seed"] = seed
        headers = {"Authorization": f"Bearer {self.api_key}"}
        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
        latency_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return {
            "response": message.get("content") or "",
            "http_status": response.status_code,
            "latency_ms": latency_ms,
            "finish_reason": choice.get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "raw": data,
        }

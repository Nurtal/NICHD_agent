"""Minimal Ollama chat client (stdlib only)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

DEFAULT_MODEL = "qwen3.8:latest"
DEFAULT_URL = "http://localhost:11434"


class LLMError(RuntimeError):
    pass


@dataclass
class ChatResult:
    content: str
    meta: dict[str, Any] = field(default_factory=dict)


class ChatClient(Protocol):
    model: str

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        seed: int | None = None,
        think: bool | str = False,
        format: dict | None = None,
    ) -> ChatResult: ...


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_URL, keep_alive: str = "30m", timeout: float = 120,
                 num_predict: int | None = None, stop: list[str] | None = None):
        self.model = model
        self.num_predict = num_predict
        self.stop = stop
        self.base_url = base_url.rstrip("/")
        self.keep_alive = keep_alive
        self.timeout = timeout

    def chat(self, messages, *, temperature, seed=None, think=False, format=None) -> ChatResult:
        options: dict[str, Any] = {"temperature": temperature}
        if seed is not None:
            options["seed"] = seed
        if self.num_predict is not None:
            options["num_predict"] = self.num_predict
        if self.stop:
            options["stop"] = self.stop
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": think,
            "keep_alive": self.keep_alive,
            "options": options,
        }
        if format is not None:
            body["format"] = format
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError) as e:
            raise LLMError(f"Ollama injoignable ({self.base_url}) : {e}") from e
        elapsed = time.perf_counter() - t0
        return ChatResult(
            content=data.get("message", {}).get("content", "").strip(),
            meta={
                "model": self.model,
                "temperature": temperature,
                "seed": seed,
                "think": think,
                "latency_s": round(elapsed, 3),
                "eval_count": data.get("eval_count"),
            },
        )

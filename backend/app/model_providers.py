from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable
from urllib.request import Request, urlopen


class ModelProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalDemoModelProvider:
    name: str = "local_demo:browser-extraction-v0"

    def complete(self, prompt: str, tools: list[str] | None = None) -> str:
        if "Conversation rules:" in prompt and "Conversation history:" in prompt:
            raise ModelProviderError("local_demo cannot generate contextual supplier replies; use MODEL_PROVIDER=ollama")
        return json.dumps(self.complete_json(prompt), ensure_ascii=False)

    def complete_json(self, prompt: str) -> dict[str, Any]:
        return {"queries": [prompt.strip()]}


@dataclass(frozen=True)
class OllamaModelProvider:
    base_url: str
    model_name: str
    timeout_seconds: int = 120
    http_post: Callable[[str, dict[str, Any], int], tuple[int, str]] | None = None

    @property
    def name(self) -> str:
        return f"ollama:{self.model_name}"

    def complete(self, prompt: str, tools: list[str] | None = None) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        status, body = (self.http_post or self._urllib_post)(
            f"{self.base_url.rstrip('/')}/api/generate",
            payload,
            self.timeout_seconds,
        )
        if status >= 400:
            raise ModelProviderError(f"Ollama returned HTTP {status}")
        try:
            data = json.loads(body or "{}")
        except json.JSONDecodeError as exc:
            raise ModelProviderError("Ollama returned invalid JSON envelope") from exc
        response = data.get("response")
        if not isinstance(response, str):
            raise ModelProviderError("Ollama response is missing text")
        return response

    def complete_json(self, prompt: str) -> dict[str, Any]:
        return parse_model_json(self.complete(prompt))

    @staticmethod
    def _urllib_post(endpoint_url: str, payload: dict[str, Any], timeout_seconds: int) -> tuple[int, str]:
        request = Request(
            endpoint_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read().decode("utf-8")


def parse_model_json(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(text.strip())
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        payload = _decode_first_json_object(cleaned)
    if not isinstance(payload, dict):
        raise ModelProviderError("model JSON must be an object")
    return payload


def _strip_json_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text


def _decode_first_json_object(text: str) -> Any:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return payload
    raise ModelProviderError("model returned invalid JSON")

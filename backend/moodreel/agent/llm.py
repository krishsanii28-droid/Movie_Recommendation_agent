"""LLM backends for the agent loop (tool calling).

* ``HFInferenceLLM`` - Hugging Face Inference Providers (chat_completion with tools).
  Good for HF Spaces / Render: no GPU or model download needed, just ``HF_TOKEN``.
* ``LocalTransformersLLM`` - runs a small instruct model (Qwen2.5-1.5B-Instruct by
  default) locally via ``transformers``; tools are passed through the chat template
  and ``<tool_call>{...}</tool_call>`` blocks are parsed from the output.

``get_llm`` returns ``None`` when no LLM is configured or it fails to load; the
agent then uses its deterministic planner.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from moodreel.config import Settings, get_settings
from moodreel.log import get_logger

logger = get_logger("llm")


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    name: str

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict]) -> LLMResponse: ...


def _loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


_TOOL_TAG = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
_FENCED = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def parse_tool_calls(text: str) -> tuple[str, list[ToolCall]]:
    """Extract tool calls from raw model text (Qwen/Hermes tags, fenced or bare JSON)."""
    calls: list[ToolCall] = []
    for pattern in (_TOOL_TAG, _FENCED):
        for m in pattern.finditer(text):
            data = _loads(m.group(1))
            if "name" in data:
                calls.append(ToolCall(data["name"], _loads(data.get("arguments", data.get("parameters", {})))))
        if calls:
            text = pattern.sub("", text)
            break
    if not calls:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            data = _loads(stripped)
            if "name" in data and ("arguments" in data or "parameters" in data):
                calls.append(ToolCall(data["name"], _loads(data.get("arguments", data.get("parameters")))))
                text = ""
    return text.strip(), calls


class HFInferenceLLM:
    def __init__(self, model: str, token: str, max_tokens: int = 512) -> None:
        from huggingface_hub import AsyncInferenceClient

        self._client = AsyncInferenceClient(model=model, token=token or None, timeout=60)
        self.name = f"hf-inference:{model}"
        self.max_tokens = max_tokens

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict]) -> LLMResponse:
        resp = await self._client.chat_completion(
            messages=messages, tools=tools, tool_choice="auto",
            max_tokens=self.max_tokens, temperature=0.4,
        )
        msg = resp.choices[0].message
        calls = [
            ToolCall(tc.function.name, _loads(tc.function.arguments), tc.id or f"call_{i}")
            for i, tc in enumerate(msg.tool_calls or [])
        ]
        content = msg.content or ""
        if not calls and content:
            content, calls = parse_tool_calls(content)
        return LLMResponse(content, calls)


class LocalTransformersLLM:
    def __init__(self, model: str, max_new_tokens: int = 512, token: str | None = None) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(model, token=token or None)
        self._model = AutoModelForCausalLM.from_pretrained(
            model, token=token or None, torch_dtype="auto",
            device_map="auto" if torch.cuda.is_available() else None,
        )
        self.name = f"local:{model}"
        self.max_new_tokens = max_new_tokens

    def _generate(self, messages: list[dict[str, Any]], tools: list[dict]) -> str:
        prompt = self._tok.apply_chat_template(messages, tools=tools, add_generation_prompt=True, tokenize=False)
        inputs = self._tok(prompt, return_tensors="pt").to(self._model.device)
        out = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=True,
                                   temperature=0.4, top_p=0.9)
        return self._tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict]) -> LLMResponse:
        text = await asyncio.to_thread(self._generate, messages, tools)
        content, calls = parse_tool_calls(text)
        return LLMResponse(content, calls)


def get_llm(settings: Settings | None = None) -> LLM | None:
    settings = settings or get_settings()
    try:
        if settings.llm_backend == "hf_inference":
            return HFInferenceLLM(settings.llm_model, settings.hf_token, settings.llm_max_new_tokens)
        if settings.llm_backend == "local":
            return LocalTransformersLLM(settings.llm_model, settings.llm_max_new_tokens, settings.hf_token)
    except Exception as exc:
        logger.warning("LLM backend %s unavailable (%s); using rule-based planner", settings.llm_backend, exc)
    return None

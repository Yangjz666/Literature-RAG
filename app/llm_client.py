from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Generator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI, OpenAIError, RateLimitError


class LLMConfigError(RuntimeError):
    """LLM 配置缺失或不合法时抛出，方便界面给出清晰提示。"""


class LLMResponseError(RuntimeError):
    """中转站返回格式不符合预期时抛出。"""


def load_env_file(path: str | Path = ".env") -> None:
    """轻量读取 .env，不覆盖系统中已经存在的环境变量。"""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(Path(__file__).resolve().parent.parent / ".env")


def _config_value(config: dict | None, env_name: str, legacy_key: str | None = None) -> str:
    """优先读环境变量；兼容旧 config.yaml 字段，避免一次改动影响旧流程。"""
    if os.environ.get(env_name):
        return os.environ[env_name].strip()
    if config and legacy_key and config.get(legacy_key):
        return str(config[legacy_key]).strip()
    return ""


def _require(value: str, env_name: str) -> str:
    if not value:
        raise LLMConfigError(f"{env_name} 未配置，请在 .env 或系统环境变量中填写。")
    return value


def _format_context_chunks(context_chunks: list[dict] | None) -> str:
    """把检索到的 chunk 统一整理为带来源的上下文，供最终回答引用。"""
    if not context_chunks:
        return "（未提供 context）"

    parts: list[str] = []
    for i, chunk in enumerate(context_chunks, start=1):
        meta = chunk.get("metadata", chunk)
        source = meta.get("paper_name") or meta.get("filename") or f"chunk-{i}"
        page = meta.get("page", "?")
        section = meta.get("section", "?")
        chunk_id = meta.get("chunk_id") or chunk.get("chunk_id") or f"chunk-{i}"
        text = chunk.get("text", "")
        parts.append(
            f"[来源 {i}: {source} | 页码: {page} | 章节: {section} | chunk_id: {chunk_id}]\n{text}"
        )
    return "\n\n---\n\n".join(parts)


RAG_SYSTEM_PROMPT = """你是严谨的 CO2RR 文献 RAG 问答助手。
必须遵守：
1. 只能根据提供的 context 回答。
2. 不允许编造文献内容、实验条件、结论或引用。
3. 如果 context 中没有答案，必须回答“当前知识库中未检索到足够证据”。
4. 输出必须包含引用来源，引用来源应来自 context 中的来源、页码、章节或 chunk_id。
5. 尽量保留原文证据片段，不要把原文证据改写成无法追溯的表述。
6. 输出必须是 Markdown，并严格使用以下标题：

## 回答

## 依据文献

## 原文证据

## 不确定性说明
"""


class LLMClient:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.provider = (
            os.environ.get("LLM_PROVIDER")
            or self.config.get("llm_provider")
            or self.config.get("llm_backend")
            or "openai"
        ).strip().lower()

        if self.provider == "openai":
            self.api_key = _require(
                _config_value(self.config, "OPENAI_API_KEY", "openai_api_key"),
                "OPENAI_API_KEY",
            )
            self.base_url = _require(
                _config_value(self.config, "OPENAI_BASE_URL", "openai_base_url"),
                "OPENAI_BASE_URL",
            )
            self.model = _require(
                _config_value(self.config, "OPENAI_MODEL", "openai_model"),
                "OPENAI_MODEL",
            )
            # OpenAI-compatible 中转站通过 base_url 指向 /v1。
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            return

        if self.provider == "anthropic":
            self.api_key = _require(
                _config_value(self.config, "ANTHROPIC_API_KEY", "anthropic_api_key"),
                "ANTHROPIC_API_KEY",
            )
            self.base_url = _require(
                _config_value(self.config, "ANTHROPIC_BASE_URL", "anthropic_base_url"),
                "ANTHROPIC_BASE_URL",
            ).rstrip("/")
            self.model = _require(
                _config_value(self.config, "ANTHROPIC_MODEL", "anthropic_model"),
                "ANTHROPIC_MODEL",
            )
            self.client = None
            return

        raise LLMConfigError("LLM_PROVIDER 只支持 openai 或 anthropic。")

    def chat(self, prompt: str, json_mode: bool = False, system_prompt: str | None = None) -> str:
        """非流式调用，用于关键词扩展、信息抽取和最终问答。"""
        if self.provider == "openai":
            return self._openai_chat(prompt, json_mode=json_mode, system_prompt=system_prompt)
        return self._anthropic_messages(prompt, system_prompt=system_prompt, json_mode=json_mode)

    def stream(self, prompt: str) -> Generator[str, None, None]:
        """OpenAI 走流式输出；Anthropic 兼容接口先用非流式结果兜底。"""
        if self.provider != "openai":
            yield self.chat(prompt)
            return

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
        except RateLimitError as e:
            raise RuntimeError("LLM API 额度不足或触发限流，请检查中转站额度。") from e
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI-compatible API 请求失败：{e}") from e

        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
            except (AttributeError, IndexError) as e:
                raise LLMResponseError("OpenAI-compatible 流式返回格式异常。") from e
            if delta:
                yield delta

    def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: list[dict] | None,
    ) -> str:
        """统一 RAG 问答入口：上层不需要关心底层供应商。"""
        context = _format_context_chunks(context_chunks)
        prompt = f"""用户问题：
{user_prompt}

context：
{context}
"""
        final_system_prompt = f"{RAG_SYSTEM_PROMPT}\n\n{system_prompt or ''}".strip()
        return self.chat(prompt, json_mode=False, system_prompt=final_system_prompt)

    def _openai_chat(self, prompt: str, json_mode: bool = False, system_prompt: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs,
            )
        except RateLimitError as e:
            raise RuntimeError("LLM API 额度不足或触发限流，请检查中转站额度。") from e
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI-compatible API 请求失败：{e}") from e

        try:
            content = resp.choices[0].message.content
        except (AttributeError, IndexError) as e:
            raise LLMResponseError("OpenAI-compatible 返回格式异常，未找到 choices[0].message.content。") from e
        if not content:
            raise LLMResponseError("OpenAI-compatible 返回内容为空。")
        return content

    def _anthropic_messages(self, prompt: str, system_prompt: str | None = None, json_mode: bool = False) -> str:
        url = f"{self.base_url}/v1/messages"
        if json_mode:
            prompt = f"{prompt}\n\n请只输出有效 JSON，不要输出解释性文字。"

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(self.config.get("llm_max_tokens", 4096)),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=int(self.config.get("llm_timeout_sec", 120))) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic-compatible API 请求失败：HTTP {e.code} {detail}") from e
        except URLError as e:
            raise RuntimeError(f"Anthropic-compatible API 请求失败：{e}") from e
        except json.JSONDecodeError as e:
            raise LLMResponseError("Anthropic-compatible 返回不是合法 JSON。") from e

        try:
            blocks = data["content"]
            text_parts = [block.get("text", "") for block in blocks if block.get("type") == "text"]
            content = "".join(text_parts).strip()
        except (KeyError, TypeError, AttributeError) as e:
            raise LLMResponseError("Anthropic-compatible 返回格式异常，未找到 content[].text。") from e
        if not content:
            raise LLMResponseError("Anthropic-compatible 返回内容为空。")
        return content


def generate_answer(
    system_prompt: str,
    user_prompt: str,
    context_chunks: list[dict] | None,
    config: dict | None = None,
) -> str:
    """模块级统一函数，便于 RAG 主流程直接调用。"""
    return LLMClient(config).generate_answer(system_prompt, user_prompt, context_chunks)

"""
Minimal async LLM client for topology proposal generation.

Provider-configurable via OPENCLAW_LLM_PROVIDER env var.
Supports Anthropic, OpenAI, and Google Gemini.

Environment variables:
  OPENCLAW_LLM_PROVIDER  "anthropic" (default), "openai", or "gemini"
  OPENCLAW_LLM_MODEL     Model name override (provider-specific default applied if unset)
  ANTHROPIC_API_KEY      Anthropic API key (also accepts ANTHROPIC_TOKEN)
  OPENAI_API_KEY         OpenAI API key
  OPENAI_BASE_URL        Optional base URL for OpenAI-compatible providers
  GEMINI_API_KEY         Google Gemini API key

Usage:
  response_text = await call_llm(system_prompt, user_message)
  clean_json = strip_markdown_fences(response_text)
"""

import os
import re

import httpx

DEFAULT_PROVIDER = "anthropic"


async def call_llm(system_prompt: str, user_message: str) -> str:
    """Call LLM and return raw text response. Provider selected from env vars.

    Args:
        system_prompt: The system instruction for the LLM.
        user_message: The user turn message to send.

    Returns:
        Raw text response from the LLM.

    Raises:
        ValueError: If an unknown provider is configured.
        RuntimeError: If required API key env vars are missing.
        httpx.HTTPStatusError: On non-2xx HTTP responses (caller handles retries).
    """
    provider = os.environ.get("OPENCLAW_LLM_PROVIDER", DEFAULT_PROVIDER)
    if provider == "anthropic":
        return await _call_anthropic(system_prompt, user_message)
    elif provider == "openai":
        return await _call_openai(system_prompt, user_message)
    elif provider == "gemini":
        return await _call_gemini(system_prompt, user_message)
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Set OPENCLAW_LLM_PROVIDER to 'anthropic', 'openai', or 'gemini'.")


async def _call_anthropic(system_prompt: str, user_message: str) -> str:
    """Call the Anthropic Messages API and return the text content."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_TOKEN")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY or ANTHROPIC_TOKEN environment variable is required for Anthropic provider."
        )

    model = os.environ.get("OPENCLAW_LLM_MODEL", "claude-sonnet-4-20250514")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _call_gemini(system_prompt: str, user_message: str) -> str:
    """Call the Google Gemini generateContent API and return the text content."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is required for Gemini provider."
        )

    model = os.environ.get("OPENCLAW_LLM_MODEL", "gemini-2.5-flash")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_message}]}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_openai(system_prompt: str, user_message: str) -> str:
    """Call the OpenAI Chat Completions API and return the text content."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is required for OpenAI provider."
        )

    model = os.environ.get("OPENCLAW_LLM_MODEL", "gpt-4o")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences from an LLM response.

    LLMs frequently wrap JSON output in markdown code fences even when asked
    not to. This utility strips leading/trailing fences so the result can be
    passed directly to json.loads().

    Args:
        text: Raw LLM response text (possibly fenced).

    Returns:
        The text with outer fences removed and whitespace stripped.

    Examples:
        >>> strip_markdown_fences('```json\\n{"a": 1}\\n```')
        '{"a": 1}'
        >>> strip_markdown_fences('{"a": 1}')
        '{"a": 1}'
    """
    stripped = text.strip()
    # Remove opening fence: ```json or ``` (with optional trailing whitespace/newline)
    stripped = re.sub(r'^```(?:json)?\s*', '', stripped)
    # Remove closing fence: ``` (with optional leading whitespace/newline)
    stripped = re.sub(r'\s*```$', '', stripped)
    return stripped.strip()

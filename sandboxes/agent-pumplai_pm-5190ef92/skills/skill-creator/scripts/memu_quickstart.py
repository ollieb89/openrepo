#!/usr/bin/env python3
"""
Minimal memU ingest + retrieve loop for OpenClaw agents.

Usage:
  OPENAI_API_KEY=... python memu_quickstart.py
  OPENROUTER_API_KEY=... python memu_quickstart.py  # auto-switches provider

Optional env:
  MEMU_USER_ID=demo-user
  MEMU_RESOURCE=memory://demo/session-1
  MEMU_METHOD=rag|llm
  MEMU_CHAT_MODEL=gpt-4o | anthropic/claude-3.5-sonnet (when using OpenRouter)
  MEMU_EMBED_MODEL=text-embedding-3-small
"""

import asyncio
import json
import os
import sys
from typing import Dict

from memu import MemUService


def build_llm_profiles() -> Dict[str, Dict[str, str]]:
    """Select OpenAI or OpenRouter config based on available keys."""
    chat_model = os.environ.get("MEMU_CHAT_MODEL")
    embed_model = os.environ.get("MEMU_EMBED_MODEL", "text-embedding-3-small")

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if openrouter_key:
        return {
            "default": {
                "provider": "openrouter",
                "client_backend": "httpx",
                "base_url": "https://openrouter.ai",
                "api_key": openrouter_key,
                "chat_model": chat_model or "anthropic/claude-3.5-sonnet",
                "embed_model": "openai/text-embedding-3-small",
            }
        }

    if not openai_key:
        sys.exit("Set OPENAI_API_KEY or OPENROUTER_API_KEY before running memu_quickstart.py")

    return {
        "default": {"api_key": openai_key, "chat_model": chat_model or "gpt-4o"},
        "embedding": {"api_key": openai_key, "embed_model": embed_model},
    }


async def main() -> None:
    user_id = os.environ.get("MEMU_USER_ID", "demo-user")
    resource_url = os.environ.get("MEMU_RESOURCE", "memory://demo/session-1")
    method = os.environ.get("MEMU_METHOD", "rag")
    if method not in {"rag", "llm"}:
        sys.exit("MEMU_METHOD must be 'rag' or 'llm'")

    service = MemUService(
        llm_profiles=build_llm_profiles(),
        database_config={"metadata_store": {"provider": "inmemory"}},
    )

    print(f"Ingesting sample conversation into memU for user_id={user_id} ...")
    await service.memorize(
        resource_url=resource_url,
        modality="conversation",
        user={"user_id": user_id},
        content=[
            {"role": "user", "content": {"text": "I love concise updates and prefer morning summaries."}},
            {"role": "assistant", "content": {"text": "Got it, will keep replies short and send morning summaries."}},
        ],
    )

    print(f"Retrieving context via method={method} ...")
    result = await service.retrieve(
        queries=[{"role": "user", "content": {"text": "What should I remember about this user?"}}],
        where={"user_id": user_id},
        method=method,
    )

    print("memU response:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

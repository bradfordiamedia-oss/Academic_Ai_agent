"""Thin wrapper around the Anthropic API used by both agents."""
from __future__ import annotations

import json
import os
import re

from anthropic import Anthropic

DEFAULT_MODEL = "claude-sonnet-5"


def get_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            api_key = None
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key "
            "locally, or set it in Streamlit Cloud's app secrets."
        )
    return Anthropic(api_key=api_key)


def call_json(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Call the model and parse a JSON object out of its reply.

    The prompt asks the model to answer with a single JSON object; this
    strips markdown code fences defensively in case the model adds them.
    """
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return _parse_json(raw_text)


def _parse_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)
    return json.loads(cleaned)

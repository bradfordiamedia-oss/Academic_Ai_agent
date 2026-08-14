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
    api_key = api_key.strip()
    try:
        api_key.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeError(
            "ANTHROPIC_API_KEY contains a character that isn't valid in an API key "
            "(often caused by curly/smart quotes from a copy-paste, or another stray "
            "character mixed into the value). Re-enter it in Streamlit Cloud's Secrets "
            "using plain straight quotes and no extra text around it."
        ) from exc
    return Anthropic(api_key=api_key)


def call_json(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Call the model and parse a JSON object out of its reply.

    The prompt asks the model to answer with a single JSON object; this
    strips markdown code fences defensively in case the model adds them.
    """
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    if not raw_text.strip():
        raise RuntimeError(
            f"The model returned no text (stop_reason={response.stop_reason!r}). "
            "This usually means the uploaded documents are too long for a single "
            "response - try shorter/trimmed documents."
        )
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            "The model's response was cut off before it could finish (ran out of "
            "output budget). Please try again - if it keeps happening, the "
            "documents may be too long for a single evaluation."
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
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # The model sometimes emits large free-text fields (the markdown report)
        # with literal newlines/tabs inside a JSON string instead of properly
        # escaping them, which breaks strict parsing. Repair and retry once.
        return json.loads(_escape_raw_control_chars_in_strings(cleaned))


def _escape_raw_control_chars_in_strings(text: str) -> str:
    """Escape literal newline/tab/carriage-return characters found inside
    JSON string literals, without touching whitespace outside strings."""
    out = []
    in_string = False
    escape_next = False
    for ch in text:
        if in_string:
            if escape_next:
                out.append(ch)
                escape_next = False
            elif ch == "\\":
                out.append(ch)
                escape_next = True
            elif ch == '"':
                out.append(ch)
                in_string = False
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
        else:
            if ch == '"':
                in_string = True
            out.append(ch)
    return "".join(out)

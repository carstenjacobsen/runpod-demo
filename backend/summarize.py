"""Summarize text with an LLM on a RunPod Serverless vLLM endpoint (adapted from runpodsum/summarize.py).

Long inputs are split into chunks, each chunk is summarized, and the partial
summaries are then combined into one final summary (map-reduce).
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

STYLES = {
    "paragraph": "a concise paragraph",
    "bullets": "a bulleted list of the key points",
    "tldr": "a one- or two-sentence TL;DR",
}

SYSTEM_PROMPT = "You are a precise summarizer. Output only the summary, no preamble."


class SummarizeError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _timeout_error() -> SummarizeError:
    return SummarizeError(
        "Summarization timed out waiting for the RunPod LLM endpoint "
        "(is the worker cold-starting, throttled or failing? check the endpoint's Workers tab).",
        504,
    )


def chat(base_url: str, api_key: str, model: str, system: str, user: str,
         max_tokens: int, deadline: float, retries: int = 4) -> str:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    for attempt in range(retries):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _timeout_error()
        try:
            # Generous timeout: a cold-started serverless worker must load the model,
            # but never beyond the overall deadline.
            with urllib.request.urlopen(req, timeout=min(600, remaining)) as resp:
                data = json.load(resp)
            return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(min(2 ** attempt * 2, max(0, deadline - time.monotonic())))
                continue
            raise SummarizeError(f"RunPod API error {e.code}: {detail}")
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt * 2, max(0, deadline - time.monotonic())))
                continue
            if deadline - time.monotonic() <= 0:
                raise _timeout_error()
            raise SummarizeError(f"Network error: {e}")
    raise SummarizeError("RunPod request failed")


def chunk_text(text: str, size: int) -> list[str]:
    """Split on paragraph boundaries into chunks of at most ~size characters."""
    chunks, cur = [], ""
    for para in text.split("\n\n"):
        while len(para) > size:  # a single oversized paragraph
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(para[:size])
            para = para[size:]
        if len(cur) + len(para) + 2 > size and cur:
            chunks.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur.strip():
        chunks.append(cur)
    return chunks


def summarize(text: str, style: str = "paragraph", max_words: int = 150,
              chunk_chars: int = 12000) -> str:
    api_key = os.environ.get("RUNPOD_API_KEY")
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")
    model = os.environ.get("RUNPOD_MODEL")
    if not (api_key and endpoint_id and model):
        raise SummarizeError(
            "Server is not configured: set RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID and RUNPOD_MODEL.",
            500,
        )

    # One overall time limit for all LLM calls, so a stuck endpoint fails with a clear
    # error before the RunPod proxy gives up on the request (~5.5 minutes).
    deadline = time.monotonic() + float(os.environ.get("SUMMARIZE_TIMEOUT_SECONDS", "240"))

    base_url = f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1"
    max_tokens = max(256, int(max_words * 2.5))

    chunks = chunk_text(text, chunk_chars)
    if len(chunks) > 1:
        partials = [
            chat(base_url, api_key, model, SYSTEM_PROMPT,
                 f"Summarize this section of a longer text in under {max_words} words:\n\n{c}",
                 max_tokens, deadline)
            for c in chunks
        ]
        text = "\n\n".join(partials)
        intro = "Combine these partial summaries of one document into"
    else:
        intro = "Summarize the following text as"

    return chat(base_url, api_key, model, SYSTEM_PROMPT,
                f"{intro} {STYLES[style]} of at most {max_words} words:\n\n{text}",
                max_tokens, deadline)

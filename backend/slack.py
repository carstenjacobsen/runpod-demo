"""Send a message to a Slack channel via chat.postMessage (adapted from slacknotify/slack_notify.py)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SLACK_API_URL = "https://slack.com/api/chat.postMessage"


class SlackError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def send_slack_message(text: str, thread_ts: str | None = None) -> dict:
    """Post a message to the channel in $SLACK_CHANNEL and return the API response."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL")
    if not (token and channel):
        raise SlackError("Server is not configured: set SLACK_BOT_TOKEN and SLACK_CHANNEL.", 500)

    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    request = urllib.request.Request(
        SLACK_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
    except urllib.error.HTTPError as e:
        raise SlackError(f"Slack HTTP error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise SlackError(f"Slack network error: {e.reason}")

    if not result.get("ok"):
        raise SlackError(f"Slack API error: {result.get('error', 'unknown_error')}")
    return result

"""Fetch release notes from the GitHub API (adapted from gitfetch/fetch_release_notes.py)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.github.com/repos/{owner}/{repo}/releases/latest"


class GitHubError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def fetch_latest_release(owner: str, repo: str, token: str | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "release-backend",
    }
    token = token or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(API_URL.format(owner=owner, repo=repo), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GitHubError(
                f"No published release found for {owner}/{repo} (or repo not found).", 404
            )
        if e.code in (403, 429):
            raise GitHubError("Rate limited or forbidden. Set GITHUB_TOKEN to authenticate.", 429)
        raise GitHubError(f"GitHub API error: HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise GitHubError(f"Network error: {e.reason}")


def fetch_release_notes(owner: str, repo: str) -> str:
    """Return the release notes text of the latest release."""
    release = fetch_latest_release(owner, repo)
    return release.get("body") or ""

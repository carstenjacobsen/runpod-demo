import logging
import os
import secrets
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from github import GitHubError, fetch_release_notes
from request_log import LogError, list_release_requests, log_release_request
from slack import SlackError, send_slack_message
from summarize import SummarizeError, summarize

load_dotenv()  # load settings from .env (real environment variables take precedence)

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Release Backend")

# Allow the frontend (default: port 8200) to read /api/releases (GET only).
# Override with a comma-separated CORS_ORIGINS, e.g. for a deployed frontend.
cors_origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:8200,http://127.0.0.1:8200").split(",")
    if o.strip()
]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET"])


@app.get("/ping")
def ping():
    # Health check polled by RunPod load balancing endpoints (200 = healthy).
    return {"status": "healthy"}


class ReleaseRequest(BaseModel):
    owner: str
    repo: str
    html_url: str


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """If API_KEY is set, require it in the X-API-Key header. Unset means no check."""
    expected = os.environ.get("API_KEY")
    if expected and not secrets.compare_digest(x_api_key or "", expected):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")


def notify_slack(release: ReleaseRequest, summary: str) -> None:
    # Runs after the response is sent, so failures are logged instead of returned.
    try:
        send_slack_message(f"New release of {release.owner}/{release.repo}: {release.html_url}\n\n{summary}")
    except SlackError as e:
        logger.error("Could not send Slack message: %s", e)


def write_request_log(release: ReleaseRequest, summary: str) -> None:
    try:
        log_release_request(release.owner, release.repo, summary)
    except LogError as e:
        logger.warning("Could not log release request: %s", e)


@app.post("/api/release", dependencies=[Depends(require_api_key)])
def create_release(release: ReleaseRequest, background_tasks: BackgroundTasks):
    try:
        notes = fetch_release_notes(release.owner, release.repo)
    except GitHubError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    if not notes.strip():
        return {"status": "success", "summary": ""}    
    try:
        summary = summarize(notes, style="bullets")
    except SummarizeError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    # Slack and the CSV log run in the background so the response isn't delayed by them.
    background_tasks.add_task(notify_slack, release, summary)
    background_tasks.add_task(write_request_log, release, summary)
    return {"status": "success", "summary": summary}


@app.get("/api/alive")
def alive():
    return {"success": True}


@app.get("/api/releases")
def list_releases():
    try:
        return list_release_requests()
    except LogError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from cdp_capture import CDPCapture
from council_adapter import analyze


HERE = Path(__file__).resolve().parent
PROFILE_DIR = Path(os.getenv("PRIVACY_MONITOR_PROFILE", HERE / ".chrome-profile"))
capture = CDPCapture(port=int(os.getenv("CDP_PORT", "9222")))
app = FastAPI(title="Live Privacy Monitor", version="0.1.0")


class ManualEvent(BaseModel):
    event: dict[str, Any]


class AnalysisRequest(BaseModel):
    task_goal: str = ""
    mock: bool = False
    events: list[dict[str, Any]] | None = None


class LaunchRequest(BaseModel):
    browser_binary: str | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (HERE / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "capturing": capture.running,
        "events": len(capture.events),
        "cdp_endpoint": capture.endpoint,
        "browser_binary": capture.find_browser(),
        "profile_dir": str(PROFILE_DIR.resolve()),
    }


@app.post("/api/browser/launch")
def launch_browser(request: LaunchRequest) -> dict[str, Any]:
    try:
        return capture.launch_browser(PROFILE_DIR, request.browser_binary)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/capture/start")
async def start_capture() -> dict[str, Any]:
    capture.clear()
    await capture.start()
    return {"ok": True, "endpoint": capture.endpoint}


@app.post("/api/capture/stop")
async def stop_capture() -> dict[str, Any]:
    await capture.stop()
    return {"ok": True, "events": len(capture.events)}


@app.get("/api/events")
def events() -> dict[str, Any]:
    return {"events": capture.snapshot()}


@app.post("/api/events")
def add_event(request: ManualEvent) -> dict[str, Any]:
    capture.add_manual_event(request.event)
    return {"ok": True, "events": len(capture.events)}


@app.post("/api/analyze")
async def analyze_capture(request: AnalysisRequest) -> dict[str, Any]:
    selected_events = request.events if request.events is not None else capture.snapshot()
    if not selected_events:
        raise HTTPException(status_code=400, detail="Aucun événement à analyser")
    try:
        return await asyncio.to_thread(analyze, selected_events, request.task_goal, request.mock)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
LIVE_MONITOR_DIR = HERE.parent / "live_privacy_monitor"
if str(LIVE_MONITOR_DIR) not in sys.path:
    sys.path.insert(0, str(LIVE_MONITOR_DIR))

from step_council import run_per_step  # noqa: E402
from task_conditioner import condition_task  # noqa: E402

app = FastAPI(title="HAR Privacy Analyzer", version="0.1.0")


class AnalysisRequest(BaseModel):
    task_goal: str = ""
    task_context: str = ""
    mock: bool = False
    events: list[dict[str, Any]]


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(HERE / "index.html")


@app.get("/anthropic_filter.js", response_class=FileResponse)
def filter_script() -> FileResponse:
    return FileResponse(HERE / "anthropic_filter.js", media_type="text/javascript")


@app.get("/result_view.js", response_class=FileResponse)
def result_script() -> FileResponse:
    return FileResponse(HERE / "result_view.js", media_type="text/javascript")


@app.get("/step_result_view.js", response_class=FileResponse)
def step_result_script() -> FileResponse:
    return FileResponse(HERE / "step_result_view.js", media_type="text/javascript")


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "ok": True,
        "ollama_host": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        "model": os.getenv("COUNCIL_CHAIRMAN_MODEL", "gemma4:31b-cloud"),
        "conditioner_model": os.getenv("HAR_CONDITIONER_MODEL", "qwen2.5:72b"),
    }


@app.post("/api/analyze")
async def analyze_har(request: AnalysisRequest) -> dict[str, Any]:
    if not request.events:
        raise HTTPException(status_code=400, detail="No HAR steps to analyze")
    compact_events = []
    for position, event in enumerate(request.events, start=1):
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        compact_events.append({
            "step": position,
            "timestamp": event.get("timestamp"),
            "model": response.get("model"),
            "message_id": response.get("message_id"),
            "stop_reason": response.get("stop_reason"),
            "trajectory": response.get("reconstructed_trajectory", ""),
        })
    try:
        conditioning = await asyncio.to_thread(
            condition_task, request.task_goal, request.task_context, mock=request.mock,
            host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        )
        return await asyncio.to_thread(
            run_per_step, compact_events, request.task_goal, request.mock, conditioning
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

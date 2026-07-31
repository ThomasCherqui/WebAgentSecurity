from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

import websockets


class CDPCapture:
    """Capture Network-domain events from all debuggable Chrome targets."""

    def __init__(self, port: int = 9222, max_events: int = 2000) -> None:
        self.port = port
        self.events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self.running = False
        self._supervisor: asyncio.Task[None] | None = None
        self._target_tasks: dict[str, asyncio.Task[None]] = {}
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def clear(self) -> None:
        self.events.clear()

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self.events)

    def add_manual_event(self, event: dict[str, Any]) -> None:
        self.events.append({"captured_at": time.time(), "source": "manual", **event})

    def find_browser(self, configured: str | None = None) -> str | None:
        candidates = [
            configured,
            os.getenv("CHROME_BINARY"),
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "/snap/bin/chromium",
        ]
        playwright_cache = Path.home() / ".cache" / "ms-playwright"
        if playwright_cache.exists():
            candidates.extend(
                str(path)
                for path in sorted(playwright_cache.glob("chromium-*/chrome-linux64/chrome"), reverse=True)
            )
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) if not candidate.startswith("/") else candidate
            if resolved and Path(resolved).exists():
                return resolved
        return None

    def launch_browser(self, profile_dir: Path, browser_binary: str | None = None) -> dict[str, Any]:
        binary = self.find_browser(browser_binary)
        if not binary:
            raise RuntimeError("Chrome/Chromium introuvable. Définir CHROME_BINARY dans l'environnement.")
        profile_dir.mkdir(parents=True, exist_ok=True)
        args = [
            binary,
            f"--user-data-dir={profile_dir.resolve()}",
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        self._process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"pid": self._process.pid, "binary": binary, "profile_dir": str(profile_dir.resolve())}

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._supervisor = asyncio.create_task(self._discover_targets())

    async def stop(self) -> None:
        self.running = False
        tasks = list(self._target_tasks.values())
        if self._supervisor:
            self._supervisor.cancel()
            tasks.append(self._supervisor)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._target_tasks.clear()
        self._supervisor = None

    async def _json_targets(self) -> list[dict[str, Any]]:
        def fetch() -> list[dict[str, Any]]:
            with urllib.request.urlopen(self.endpoint + "/json", timeout=2) as response:
                value = json.loads(response.read().decode("utf-8"))
                return value if isinstance(value, list) else []

        return await asyncio.to_thread(fetch)

    async def _discover_targets(self) -> None:
        while self.running:
            try:
                targets = await self._json_targets()
                active_ids = set()
                for target in targets:
                    target_id = str(target.get("id") or "")
                    ws_url = target.get("webSocketDebuggerUrl")
                    if not target_id or not ws_url:
                        continue
                    active_ids.add(target_id)
                    task = self._target_tasks.get(target_id)
                    if task is None or task.done():
                        self._target_tasks[target_id] = asyncio.create_task(self._capture_target(target, ws_url))
                for target_id in set(self._target_tasks) - active_ids:
                    self._target_tasks.pop(target_id).cancel()
            except Exception as exc:
                self.events.append({
                    "captured_at": time.time(), "source": "cdp", "kind": "capture_error",
                    "error": str(exc),
                })
            await asyncio.sleep(1)

    async def _capture_target(self, target: dict[str, Any], ws_url: str) -> None:
        pending: dict[str, dict[str, Any]] = {}
        command_id = 0
        try:
            async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as socket:
                command_id += 1
                await socket.send(json.dumps({"id": command_id, "method": "Network.enable", "params": {}}))
                while self.running:
                    message = json.loads(await socket.recv())
                    method = message.get("method")
                    params = message.get("params") or {}
                    request_id = str(params.get("requestId") or "")
                    if method == "Network.requestWillBeSent":
                        req = params.get("request") or {}
                        event = {
                            "captured_at": time.time(), "source": "cdp", "kind": "request",
                            "target_id": target.get("id"), "target_type": target.get("type"),
                            "target_url": target.get("url"), "request_id": request_id,
                            "url": req.get("url"), "method": req.get("method"),
                            "post_data": req.get("postData"), "resource_type": params.get("type"),
                            "initiator": params.get("initiator"),
                        }
                        pending[request_id] = event
                        self.events.append(event)
                    elif method == "Network.responseReceived":
                        response = params.get("response") or {}
                        event = {
                            "captured_at": time.time(), "source": "cdp", "kind": "response",
                            "target_id": target.get("id"), "target_type": target.get("type"),
                            "request_id": request_id, "url": response.get("url"),
                            "status": response.get("status"), "mime_type": response.get("mimeType"),
                        }
                        pending.setdefault(request_id, {}).update(event)
                        self.events.append(event)
                    elif method == "Network.loadingFinished" and request_id in pending:
                        command_id += 1
                        await socket.send(json.dumps({
                            "id": command_id, "method": "Network.getResponseBody",
                            "params": {"requestId": request_id},
                        }))
                        pending[str(command_id)] = {"body_for": request_id}
                    elif method in {"Network.webSocketFrameSent", "Network.webSocketFrameReceived"}:
                        frame = params.get("response") or {}
                        self.events.append({
                            "captured_at": time.time(), "source": "cdp", "kind": method.rsplit(".", 1)[-1],
                            "target_id": target.get("id"), "request_id": request_id,
                            "payload": frame.get("payloadData"), "opcode": frame.get("opcode"),
                        })
                    elif "id" in message:
                        command = pending.pop(str(message["id"]), {})
                        body_for = command.get("body_for")
                        result = message.get("result") or {}
                        if body_for and "body" in result:
                            body = result["body"]
                            if result.get("base64Encoded"):
                                body = base64.b64decode(body).decode("utf-8", "replace")
                            self.events.append({
                                "captured_at": time.time(), "source": "cdp", "kind": "response_body",
                                "target_id": target.get("id"), "request_id": body_for, "body": body,
                            })
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.events.append({
                "captured_at": time.time(), "source": "cdp", "kind": "target_error",
                "target_id": target.get("id"), "target_type": target.get("type"), "error": str(exc),
            })


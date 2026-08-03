#!/usr/bin/env python3
"""Probe outgoing Claude/browser traffic through Chrome DevTools Protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import websockets

CLAUDE_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
EVENTS = {
    "Network.requestWillBeSent",
    "Network.webSocketFrameSent",
    "Network.eventSourceMessageReceived",
}


def targets(endpoint: str) -> list[dict[str, Any]]:
    with urllib.request.urlopen(endpoint.rstrip("/") + "/json", timeout=2) as response:
        value = json.loads(response.read().decode())
    return value if isinstance(value, list) else []


def normalize(method: str, params: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    event: dict[str, Any] = {
        "captured_at": time.time(),
        "target_type": target.get("type"),
        "target_url": target.get("url"),
        "cdp_method": method,
    }
    if method == "Network.requestWillBeSent":
        request = params.get("request") or {}
        event.update(
            kind="request",
            method=request.get("method"),
            url=request.get("url"),
            post_data=request.get("postData"),
            resource_type=params.get("type"),
        )
    elif method == "Network.webSocketFrameSent":
        frame = params.get("response") or {}
        event.update(kind="websocket_sent", payload=frame.get("payloadData"))
    else:
        event.update(kind="event_source_message", data=params.get("data"))
    return event


class Probe:
    def __init__(self, endpoint: str, output: Path, marker: str, claude_only: bool) -> None:
        self.endpoint = endpoint
        self.output = output
        self.marker = marker
        self.claude_only = claude_only
        self.captured: list[dict[str, Any]] = []
        self.tasks: dict[str, asyncio.Task[None]] = {}

    async def watch(self, target: dict[str, Any]) -> None:
        try:
            async with websockets.connect(target["webSocketDebuggerUrl"], max_size=32_000_000) as socket:
                await socket.send(json.dumps({"id": 1, "method": "Network.enable", "params": {}}))
                print(f"Attached: {target.get('type')} {target.get('url')}", flush=True)
                while True:
                    message = json.loads(await socket.recv())
                    method = message.get("method")
                    if method not in EVENTS:
                        continue
                    event = normalize(method, message.get("params") or {}, target)
                    self.captured.append(event)
                    serialized = json.dumps(event, ensure_ascii=False)
                    found = "  <<< MARKER FOUND" if self.marker in serialized else ""
                    print(f"[{event['target_type']}] {event['kind']} {event.get('url', '')}{found}", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Target unavailable: {exc}", flush=True)

    async def run(self) -> None:
        print("Capture active. Perform the Claude action, then press Ctrl+C.\n")
        while True:
            seen: set[str] = set()
            for target in await asyncio.to_thread(targets, self.endpoint):
                target_id = str(target.get("id") or "")
                url = str(target.get("url") or "")
                supported = target.get("type") in {
                    "page", "iframe", "service_worker", "shared_worker", "background_page"
                }
                if not target_id or not supported or not target.get("webSocketDebuggerUrl"):
                    continue
                if self.claude_only and CLAUDE_ID not in url:
                    continue
                seen.add(target_id)
                task = self.tasks.get(target_id)
                if task is None or task.done():
                    self.tasks[target_id] = asyncio.create_task(self.watch(target))
            for target_id in set(self.tasks) - seen:
                self.tasks.pop(target_id).cancel()
            await asyncio.sleep(0.5)

    async def close(self) -> None:
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.output.write_text(json.dumps(self.captured, ensure_ascii=False, indent=2))
        matches = sum(
            self.marker in json.dumps(event, ensure_ascii=False) for event in self.captured
        )
        print(f"\nSaved {len(self.captured)} events to {self.output}")
        print(f"Marker {self.marker!r}: {matches} match(es)")


async def execute(args: argparse.Namespace) -> None:
    probe = Probe(args.endpoint, args.output, args.marker, args.claude_only)
    try:
        await probe.run()
    finally:
        await probe.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:9222")
    parser.add_argument("--output", type=Path, default=Path("cdp-capture.json"))
    parser.add_argument("--marker", default="TEST_PRIVATE_8472")
    parser.add_argument("--claude-only", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except KeyboardInterrupt:
        pass
    except (OSError, urllib.error.URLError) as exc:
        raise SystemExit(f"Cannot reach Chrome CDP: {exc}") from exc


if __name__ == "__main__":
    main()

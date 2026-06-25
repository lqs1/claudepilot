#!/usr/bin/env python3
"""端到端测试脚本：发送消息并通过 WebSocket 观察事件流."""

import asyncio
import json
import time
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"
SESSION_ID = "7d3f23b3-bbb6-4b54-89d1-216cf8d8f2e2"


async def test_with_websocket():
    """Connect WS, subscribe, send message via HTTP, observe events."""
    print(f"=== Connecting to {WS_URL} ===")
    async with websockets.connect(WS_URL) as ws:
        # Subscribe to session
        await ws.send(json.dumps({"type": "subscribe", "session_id": SESSION_ID}))
        print(f"Subscribed to session {SESSION_ID}")

        # Give subscription a moment
        await asyncio.sleep(0.5)

        # Send message via HTTP (using curl subprocess to avoid blocking)
        print("\n=== Sending message via HTTP ===")
        import subprocess

        curl_cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{BASE_URL}/api/sessions/{SESSION_ID}/messages",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps({"content": "Say hello in one word"}),
            "-w",
            "\nHTTP_CODE: %{http_code}\n",
        ]
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
        print(f"HTTP Response:\n{result.stdout}")
        if result.stderr:
            print(f"HTTP stderr: {result.stderr}")

        # Now listen for WebSocket events for 30 seconds
        print("\n=== Listening for WebSocket events (30s) ===")
        start = time.time()
        event_count = 0
        while time.time() - start < 30:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                event_count += 1
                data = json.loads(msg)
                event_type = data.get("data", {}).get("type", "unknown")
                print(f"[{event_count}] WS event type={event_type}")
                if event_type == "assistant":
                    text = data.get("data", {}).get("text", "")
                    print(f"    text={text[:100]!r}")
                elif event_type == "raw_output":
                    content = data.get("data", {}).get("content", "")
                    print(f"    raw={content[:200]!r}")
                elif event_type == "error":
                    print(f"    ERROR: {data.get('data', {}).get('message', '')}")
                elif event_type == "status":
                    print(f"    status={data.get('data', {}).get('status', '')}")
                else:
                    print(f"    full={json.dumps(data, ensure_ascii=False)[:300]}")
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket closed!")
                break

        print(f"\n=== Total events received: {event_count} ===")


if __name__ == "__main__":
    asyncio.run(test_with_websocket())

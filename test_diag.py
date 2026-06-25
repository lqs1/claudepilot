"""Test script to diagnose ClaudePilot chat flow end-to-end."""

import asyncio
import json
import time
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"
SESSION_ID = "7d3f23b3-bbb6-4b54-89d1-216cf8d8f2e2"


async def test_websocket():
    """Connect to WS, subscribe, and listen for events."""
    print("=" * 60)
    print("STEP 1: Connecting to WebSocket...")
    print("=" * 60)

    async with websockets.connect(WS_URL) as ws:
        print(f"[WS] Connected to {WS_URL}")

        # Subscribe to session
        sub_msg = json.dumps({"type": "subscribe", "session_id": SESSION_ID})
        await ws.send(sub_msg)
        print(f"[WS] Sent subscribe: {sub_msg}")

        # Wait a moment for subscription to register
        await asyncio.sleep(0.5)

        print("\n" + "=" * 60)
        print("STEP 2: Sending message via HTTP API...")
        print("=" * 60)

        # Send message via HTTP using curl
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
            json.dumps({"content": "Hello, say hi back in one word"}),
        ]
        print(f"[HTTP] Running: {' '.join(curl_cmd)}")
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        print(f"[HTTP] Response: {result.stdout}")
        if result.returncode != 0:
            print(f"[HTTP] Error: {result.stderr}")

        print("\n" + "=" * 60)
        print("STEP 3: Listening for WebSocket events (30s timeout)...")
        print("=" * 60)

        # Listen for events with timeout
        start_time = time.time()
        timeout = 30
        events_received = []

        while time.time() - start_time < timeout:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                events_received.append(data)
                print(f"[WS] Event: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[WS] Error: {e}")
                break

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total events received: {len(events_received)}")
        event_types = {}
        for ev in events_received:
            et = ev.get("data", {}).get("type", "unknown")
            event_types[et] = event_types.get(et, 0) + 1
        print(f"Event type breakdown: {event_types}")

        if not events_received:
            print("\n!!! NO EVENTS RECEIVED - This is the bug !!!")
            print("Possible causes:")
            print("1. Claude CLI not producing events")
            print("2. Events not being parsed correctly")
            print("3. WebSocket broadcast not working")
            print("4. Subscription not working")
        else:
            print("\nEvents were received - WebSocket flow is working")


if __name__ == "__main__":
    asyncio.run(test_websocket())

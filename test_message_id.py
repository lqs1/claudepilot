#!/usr/bin/env python3
"""测试 Claude CLI 的 assistant 事件结构，特别关注 message_id."""

import asyncio
import json
import websockets

WS_URL = "ws://127.0.0.1:8000/ws"
SESSION_ID = "7d3f23b3-bbb6-4b54-89d1-216cf8d8f2e2"


async def test():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({"type": "subscribe", "session_id": SESSION_ID}))
        await asyncio.sleep(0.5)

        import subprocess

        subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                f"http://127.0.0.1:8000/api/sessions/{SESSION_ID}/messages",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps({"content": "Say hi"}),
            ],
            capture_output=True,
        )

        print("=== Listening for assistant events ===")
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < 20:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                event_type = data.get("data", {}).get("type")
                if event_type == "assistant":
                    msg_data = data.get("data", {})
                    print("assistant event:")
                    print(f"  message_id={msg_data.get('message_id')!r}")
                    print(f"  text={msg_data.get('text')!r}")
                    print(f"  tool_uses={msg_data.get('tool_uses')}")
                    print(f"  usage={msg_data.get('usage')}")
                    print()
                elif event_type == "error":
                    print(f"ERROR: {data}")
            except asyncio.TimeoutError:
                continue


if __name__ == "__main__":
    asyncio.run(test())

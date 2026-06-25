import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.claude_manager import session_manager


async def main():
    session_id = str(uuid.uuid4())
    project_path = Path("/tmp")

    events = []

    def cb(sid, payload):
        print(f"CALLBACK: {sid} {payload}", flush=True)
        events.append(payload)

    session_manager.add_callback(cb)
    print(f"Starting session {session_id}", flush=True)
    try:
        engine = await session_manager.start_session(
            session_id, project_path, language="zh", initial_message="Say exactly pong"
        )
    except Exception as exc:
        print(f"START ERROR: {type(exc).__name__}: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        return

    print(f"After start, status: {engine.status}", flush=True)
    print(f"Process: {engine._process}", flush=True)
    print(
        f"Process returncode: {engine._process.returncode if engine._process else None}",
        flush=True,
    )

    await asyncio.sleep(10)
    print(f"After sleep, status: {engine.status}", flush=True)
    print(
        f"Process returncode: {engine._process.returncode if engine._process else None}",
        flush=True,
    )
    await session_manager.stop_session(session_id)
    print(f"Total events: {len(events)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

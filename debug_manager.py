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
        print(f"CALLBACK: {sid} {payload}")
        events.append(payload)

    session_manager.add_callback(cb)
    engine = await session_manager.start_session(
        session_id, project_path, language="zh", initial_message="Say hello in one word"
    )
    print(f"After start, status: {engine.status}")
    print(f"Process: {engine._process}")
    print(
        f"Process returncode: {engine._process.returncode if engine._process else None}"
    )
    engine.add_handler(lambda e: print(f"ENGINE EVENT: {type(e).__name__} {e}"))

    await asyncio.sleep(10)
    print(f"After sleep, status: {engine.status}")
    print(
        f"Process returncode: {engine._process.returncode if engine._process else None}"
    )
    await session_manager.stop_session(session_id)
    print(f"Total events: {len(events)}")


if __name__ == "__main__":
    asyncio.run(main())

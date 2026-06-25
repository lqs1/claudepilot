import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.claude_driver import ClaudeEngine

logging.basicConfig(level=logging.DEBUG)


async def main():
    events = []
    engine = ClaudeEngine(
        project_path=Path("/tmp"),
        append_system_prompt="请用中文回答。生成的代码注释和文档默认使用中文。",
    )
    engine.add_handler(lambda e: print("EVENT:", type(e).__name__, e))
    engine.add_handler(events.append)

    await engine.start()
    print("Engine started, status:", engine.status)
    await engine.send_message("Say exactly the word 'pong' and nothing else.")

    await asyncio.wait_for(_wait_for_init(events), timeout=30.0)
    print("Got init event")
    await asyncio.sleep(5.0)

    await engine.stop()
    print("Stopped, total events:", len(events))


async def _wait_for_init(events):
    from app.claude_driver import InitEvent

    for _ in range(300):
        if any(isinstance(e, InitEvent) for e in events):
            return
        await asyncio.sleep(0.1)
    raise TimeoutError()


if __name__ == "__main__":
    asyncio.run(main())

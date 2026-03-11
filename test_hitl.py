import asyncio
from tools import execute_tool, _tool_requires_confirmation
from config import OWNER_ID

async def test():
    print("Requires confirmation for run_command:", _tool_requires_confirmation("run_command"))
    class DummyTaskManager: pass
    res = await execute_tool("run_command", {"command": "echo hello"}, OWNER_ID, DummyTaskManager())
    print("Result:", res)

asyncio.run(test())

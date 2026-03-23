import os
import asyncio
import mcp_manager

os.environ['ENABLE_CHROME_MCP'] = 'true'

async def check():
    await mcp_manager.start_mcp_servers()
    tools = mcp_manager.get_tools()
    print("Tools fetched:", len(tools))
    for t in tools:
        print("-", t.get('function', {}).get('name'))

asyncio.run(check())

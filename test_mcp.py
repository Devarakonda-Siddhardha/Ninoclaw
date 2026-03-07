import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
import os

async def test():
    print("Starting...")
    params = StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-playwright"], env=os.environ.copy())
    try:
        async with stdio_client(params) as (r, w):
            print("Connected!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())

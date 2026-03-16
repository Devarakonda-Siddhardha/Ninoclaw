"""
mcp_manager.py — Model Context Protocol Client Integration
Connects Ninoclaw to external MCP servers (e.g., filesystem, github) to fetch and execute tools.
"""

import os
import json
import asyncio
from contextlib import AsyncExitStack
from dotenv import load_dotenv

# MCP package import (optional - if not installed, returns empty tools)
try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Define placeholders if mcp not available
    stdio_client = None
    StdioServerParameters = None
    ClientSession = None

# Manage lifecycles of multiple subprocess streams
_stack = None
_sessions = {}   # Map: server_name -> ClientSession
_mcp_tools = []  # Cached list of OpenAI-formatted tool schemas

def _clean_schema(schema: dict) -> dict:
    """Ensure the JSON schema is perfectly valid for OpenAI/Gemini."""
    # Sometimes MCP tools return root types other than object, or missing properties.
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}
    if schema.get("type") != "object":
        schema["type"] = "object"
    if "properties" not in schema:
        schema["properties"] = {}
    return schema

async def start_mcp_servers():
    """Start all servers defined in MCP_SERVERS env var"""
    if not MCP_AVAILABLE:
        print("[MCP] MCP package not installed. Skipping MCP server initialization.")
        return

    global _stack
    if _stack is None:
        _stack = AsyncExitStack()

    mcp_servers_env = os.getenv("MCP_SERVERS")
    try:
        servers = json.loads(mcp_servers_env) if mcp_servers_env else {}
    except json.JSONDecodeError as e:
        print(f"[MCP] Failed to parse MCP_SERVERS JSON: {e}")
        servers = {}

    # Dynamically inject Chrome DevTools MCP if enabled in Dashboard
    if os.getenv("ENABLE_CHROME_MCP", "false").lower() == "true":
        servers["chrome_devtools"] = {
            "command": "npx",
            "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect"]
        }
        
    if not servers:
        return

    # print(f"[MCP] Initializing {len(servers)} server(s)...")

    for name, config in servers.items():
        try:
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env", None)
            
            if not command:
                print(f"[MCP] Server '{name}' missing 'command'. Skipping.")
                continue


            # Overlay custom env on system env
            server_env = os.environ.copy()
            if env:
                # server_env expects string values
                server_env.update({str(k): str(v) for k, v in env.items()})
                
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=server_env
            )
            
            # Start the stdio subprocess and keep it alive in the stack
            read_stream, write_stream = await _stack.enter_async_context(stdio_client(server_params))
            session = await _stack.enter_async_context(ClientSession(read_stream, write_stream))
            
            await session.initialize()
            
            # Fetch tools
            tools_response = await session.list_tools()
            tools_count = 0
            
            for mcp_tool in tools_response.tools:
                # Namespace the tools to avoid collisions and track routing
                tool_name = f"mcp__{name}__{mcp_tool.name}"
                # Sanitize the schema names if they have dashes, etc.
                tool_name = tool_name.replace("-", "_")
                
                global _mcp_name_mapping
                _mcp_name_mapping[tool_name] = mcp_tool.name

                _mcp_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": mcp_tool.description or f"MCP tool: {mcp_tool.name}",
                        "parameters": _clean_schema(mcp_tool.inputSchema)
                    }
                })
                tools_count += 1
                
            _sessions[name] = session
            print(f"[MCP] Started server '{name}' with {tools_count} tools.")
            
        except Exception as e:
            print(f"[MCP] Failed to start server '{name}': {e}")


def get_tools():
    """Return all loaded MCP tools formatted for the AI API."""
    return _mcp_tools


async def execute_tool(namespaced_tool: str, arguments: dict) -> str:
    """Route the tool call to the correct MCP server session."""
    if not namespaced_tool.startswith("mcp__"):
        return f"❌ Not an MCP tool: {namespaced_tool}"
        
    parts = namespaced_tool.split("__", 2)
    if len(parts) != 3:
        return "❌ Malformed MCP tool name."
        
    _, server_name, actual_tool_name = parts
    
    session = _sessions.get(server_name)
    if not session:
        return f"❌ MCP sever '{server_name}' is not running."
        
    try:
        # print(f"[MCP] Calling '{actual_tool_name}' on '{server_name}'...")
        
        # We need to map underscores back to hyphens if the server uses hyphens, but MCP standard sends the actual name as listed. 
        # Actually, since we modified the tool_name sent to the LLM to remove dashes, we might need a mapping to the REAL tool name.
        # But wait, we didn't map them back. Let's fix this securely.
        
        # It's better to find the real tool name by searching the session tools by regex or just using a strict dict lookup.
        # Since MCP server tools often use dashes (like 'list_allowed_directories'), we must send the exact string.
        # Let's fix this in start_mcp_servers and use a global dict for mapping.
        real_tool_name = actual_tool_name # The original string will be stored in a mapping (implemented below)
        
        # Use mapping if available (we will parse the original list of tools)
        global _mcp_name_mapping
        mapped = _mcp_name_mapping.get(namespaced_tool)
        if mapped:
             real_tool_name = mapped

        result = await session.call_tool(real_tool_name, arguments)
        
        if result.isError:
            return f"❌ MCP Tool Error: {result.content}"

        output = ""
        for item in result.content:
            if item.type == "text":
                output += item.text
            elif hasattr(item, "text"):
                output += str(item.text)
        
        return output if output else "✅ Tool executed successfully (no output)."
        
    except Exception as e:
        return f"❌ MCP Tool Execution Failed: {str(e)}"

_mcp_name_mapping = {} # AI_safe_name -> real_MCP_name

async def cleanup():
    """Close all MCP server sessions and background processes."""
    global _stack
    if _sessions:
        print("[MCP] Shutting down servers...")
    if _stack is not None:
        await _stack.aclose()
        _stack = None
    _sessions.clear()
    _mcp_tools.clear()
    _mcp_name_mapping.clear()

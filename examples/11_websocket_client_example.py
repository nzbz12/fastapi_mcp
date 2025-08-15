"""
Example showing how to use FastAPI-MCP as a WebSocket client to connect to external MCP services.

This example demonstrates connecting to an external MCP server via WebSocket
and forwarding tool calls through the connection.
"""

import asyncio
import json
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from fastapi_mcp.transport.websocket import FastApiWebSocketTransport
from mcp.types import JSONRPCMessage, JSONRPCRequest
from mcp.server.lowlevel.server import Server

# External WebSocket URL from xiaozhi.me
EXTERNAL_WS_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjE2MSwiYWdlbnRJZCI6MTcwMSwiZW5kcG9pbnRJZCI6ImFnZW50XzE3MDEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzU1MjUzOTY3fQ.AQS81b4c9ic2jwjRRUBNErmIr34GZcodfTLams2BXwnC-4mBtDr12l-_YGMrL4Rc-PqScbpEjsW2bnl9DTmIJA"

app = FastAPI(title="WebSocket MCP Client Example")

# Create a minimal MCP server for demonstration
mcp_server = Server("WebSocket Client", "Example WebSocket MCP client")

# Create WebSocket transport
ws_transport = FastApiWebSocketTransport(mcp_server=mcp_server)


async def test_external_connection():
    """Test connecting to the external WebSocket MCP server."""
    try:
        print(f"Connecting to external WebSocket: {EXTERNAL_WS_URL}")
        await ws_transport.connect_to_external_websocket(EXTERNAL_WS_URL)
        
        # Send an initialization request
        init_request = JSONRPCMessage(root=JSONRPCRequest(
            jsonrpc="2.0",
            id="1",
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "FastAPI-MCP WebSocket Client",
                    "version": "0.4.0"
                }
            }
        ))
        
        print("Sending initialization request...")
        response = await ws_transport.send_to_external_websocket(init_request)
        print(f"Received response: {response}")
        
        # List available tools
        tools_request = JSONRPCMessage(root=JSONRPCRequest(
            jsonrpc="2.0",
            id="2",
            method="tools/list",
            params={}
        ))
        
        print("Requesting tools list...")
        tools_response = await ws_transport.send_to_external_websocket(tools_request)
        print(f"Available tools: {tools_response}")
        
    except Exception as e:
        print(f"Error connecting to external WebSocket: {e}")
    finally:
        await ws_transport.disconnect_external_websocket()


@app.on_event("startup")
async def startup():
    """Run the WebSocket client test on startup."""
    print("Starting WebSocket MCP client example...")
    await test_external_connection()


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    print("Shutting down WebSocket transport...")
    await ws_transport.shutdown()


@app.get("/")
async def root():
    """Basic endpoint to verify the app is running."""
    return {
        "message": "WebSocket MCP Client Example",
        "external_ws_url": EXTERNAL_WS_URL,
        "status": "ready"
    }


@app.get("/test-connection")
async def test_connection():
    """Endpoint to manually test the WebSocket connection."""
    try:
        await test_external_connection()
        return {"status": "success", "message": "Connection test completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    print("WebSocket MCP Client Example")
    print(f"Connecting to: {EXTERNAL_WS_URL}")
    print("Server will be available at http://localhost:8001")
    print("Visit http://localhost:8001/test-connection to test the connection")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
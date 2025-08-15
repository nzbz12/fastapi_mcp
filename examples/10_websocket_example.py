from examples.shared.apps.items import app  # The FastAPI app
from examples.shared.setup import setup_logging

from fastapi_mcp import FastApiMCP

setup_logging()

# External WebSocket URL from xiaozhi.me
EXTERNAL_WS_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjE2MSwiYWdlbnRJZCI6MTcwMSwiZW5kcG9pbnRJZCI6ImFnZW50XzE3MDEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzU1MjUzOTY3fQ.AQS81b4c9ic2jwjRRUBNErmIr34GZcodfTLams2BXwnC-4mBtDr12l-_YGMrL4Rc-PqScbpEjsW2bnl9DTmIJA"

# Add MCP server to the FastAPI app
mcp = FastApiMCP(app)

# Mount the MCP WebSocket server with external connection
mcp.mount_websocket(
    mount_path="/ws",
    external_ws_url=EXTERNAL_WS_URL
)

# Also mount HTTP for comparison
mcp.mount_http()


if __name__ == "__main__":
    import uvicorn
    import asyncio
    import signal
    import sys

    async def shutdown_handler():
        """Handle graceful shutdown"""
        print("Shutting down...")
        await mcp.shutdown()
        
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        asyncio.create_task(shutdown_handler())
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Starting FastAPI app with WebSocket MCP support")
    print(f"WebSocket MCP server: ws://localhost:8000/ws")
    print(f"HTTP MCP server: http://localhost:8000/mcp")
    print(f"External WebSocket connection: {EXTERNAL_WS_URL}")
    print("Press Ctrl+C to shutdown")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
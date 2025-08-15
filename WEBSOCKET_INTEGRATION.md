# WebSocket Integration for FastAPI-MCP

This document describes the new WebSocket transport functionality added to FastAPI-MCP, which enables bidirectional communication with MCP servers over WebSocket connections.

## Features

- **WebSocket Server**: Accept incoming WebSocket connections for MCP communication
- **WebSocket Client**: Connect to external WebSocket MCP servers as a client
- **Bidirectional**: Act as both server and client simultaneously
- **External Integration**: Connect to external MCP services like `wss://api.xiaozhi.me/mcp/`

## Installation

The WebSocket functionality requires the `websockets` library, which is now included in the dependencies:

```bash
uv add fastapi-mcp
# or
pip install fastapi-mcp
```

## Basic Usage

### WebSocket Server Only

```python
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

app = FastAPI()
mcp = FastApiMCP(app)

# Mount WebSocket transport
mcp.mount_websocket(mount_path="/ws")
```

Your WebSocket MCP server will be available at `ws://localhost:8000/ws`

### WebSocket Client Connection

```python
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

app = FastAPI()
mcp = FastApiMCP(app)

# Connect to external WebSocket MCP server
external_url = "wss://api.xiaozhi.me/mcp/?token=YOUR_TOKEN"
mcp.mount_websocket(
    mount_path="/ws",
    external_ws_url=external_url
)
```

### Bidirectional (Server + Client)

The above example acts as both server and client - it accepts incoming connections at `/ws` while also connecting to the external service.

## API Reference

### `mount_websocket()`

```python
def mount_websocket(
    self,
    router: Optional[FastAPI | APIRouter] = None,
    mount_path: str = "/ws",
    external_ws_url: Optional[str] = None,
) -> None
```

**Parameters:**
- `router`: FastAPI app or APIRouter to mount to (defaults to the main app)
- `mount_path`: Path where WebSocket endpoint will be available (default: "/ws")
- `external_ws_url`: Optional external WebSocket URL to connect to as a client

## WebSocket Transport Features

### Connection Management
- Automatic connection handling and cleanup
- Session management with unique session IDs
- Graceful disconnect handling

### Message Processing
- JSON-RPC 2.0 compliant message handling
- Support for MCP protocol methods (`initialize`, `tools/list`, etc.)
- Error handling with proper JSON-RPC error responses

### External Client Support
- Automatic reconnection handling
- Request-response correlation
- Concurrent request handling

## Examples

### Example 1: Basic WebSocket Server

```python
# examples/10_websocket_example.py
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id, "name": f"Item {item_id}"}

mcp = FastApiMCP(app)
mcp.mount_websocket()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Example 2: WebSocket Client

```python
# examples/11_websocket_client_example.py
import asyncio
from fastapi_mcp.transport.websocket import FastApiWebSocketTransport
from mcp.server.lowlevel.server import Server
from mcp.types import JSONRPCMessage, JSONRPCRequest

async def connect_to_external():
    server = Server("Client", "WebSocket client")
    transport = FastApiWebSocketTransport(server)
    
    await transport.connect_to_external_websocket(
        "wss://api.xiaozhi.me/mcp/?token=YOUR_TOKEN"
    )
    
    # Send initialization
    message = JSONRPCMessage(root=JSONRPCRequest(
        jsonrpc="2.0",
        id="1",
        method="initialize",
        params={}
    ))
    
    response = await transport.send_to_external_websocket(message)
    print(f"Response: {response}")

asyncio.run(connect_to_external())
```

## Testing

Run the WebSocket tests:

```bash
python -m pytest tests/test_websocket_transport.py -v
```

Or run the demo script:

```bash
python test_websocket_demo.py
```

## Integration with External Services

The WebSocket transport has been tested with the xiaozhi.me MCP service:

```python
EXTERNAL_WS_URL = "wss://api.xiaozhi.me/mcp/?token=YOUR_TOKEN_HERE"

mcp.mount_websocket(external_ws_url=EXTERNAL_WS_URL)
```

## Error Handling

The WebSocket transport includes comprehensive error handling:

- **Connection Errors**: Automatic retry logic for external connections
- **Message Errors**: JSON-RPC error responses for malformed messages
- **Timeout Handling**: Configurable timeouts for connections and requests
- **Graceful Shutdown**: Proper cleanup of all connections on shutdown

## Configuration Options

### Connection Settings

```python
from fastapi_mcp.transport.websocket import FastApiWebSocketTransport

transport = FastApiWebSocketTransport(
    mcp_server=server,
    external_ws_url="wss://example.com/mcp",
    connection_timeout=30.0,    # Connection timeout in seconds
    ping_interval=20.0,         # Ping interval in seconds
    ping_timeout=20.0,          # Ping timeout in seconds  
    close_timeout=10.0,         # Close timeout in seconds
)
```

## Shutdown and Cleanup

Always ensure proper cleanup:

```python
@app.on_event("shutdown")
async def shutdown():
    await mcp.shutdown()
```

This will properly close all WebSocket connections and clean up resources.

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the external WebSocket URL is correct and accessible
2. **Authentication Errors**: Verify tokens and authentication parameters
3. **Message Format Errors**: Ensure JSON-RPC 2.0 compliance in messages

### Debug Logging

Enable debug logging to see detailed WebSocket communication:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] WebSocket authentication middleware
- [ ] Automatic reconnection with exponential backoff
- [ ] WebSocket message compression
- [ ] Custom message routing and filtering
- [ ] WebSocket clustering support
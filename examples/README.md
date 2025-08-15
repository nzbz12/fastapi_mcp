# FastAPI-MCP Examples

## Examples

This directory contains examples demonstrating various features of FastAPI-MCP.

- `01_basic_usage_example.py` - Basic usage with HTTP transport
- `02_full_schema_description_example.py` - Full schema descriptions
- `03_custom_exposed_endpoints_example.py` - Custom endpoint filtering
- `04_separate_server_example.py` - Running MCP server separately
- `05_reregister_tools_example.py` - Re-registering tools dynamically
- `06_custom_mcp_router_example.py` - Custom router configuration
- `07_configure_http_timeout_example.py` - HTTP timeout configuration
- `08_auth_example_token_passthrough.py` - Token passthrough authentication
- `09_auth_example_auth0.py` - Auth0 integration
- `10_websocket_example.py` - **NEW** WebSocket transport with external connection
- `11_websocket_client_example.py` - **NEW** WebSocket client for external MCP services

### WebSocket Examples

The WebSocket examples demonstrate the new WebSocket transport capabilities:

- **Server Mode**: Accept incoming WebSocket connections for MCP communication
- **Client Mode**: Connect to external WebSocket MCP servers
- **Bidirectional**: Act as both server and client simultaneously

#### Running WebSocket Examples

```bash
# Basic WebSocket server with external connection
python examples/10_websocket_example.py

# WebSocket client connecting to external services
python examples/11_websocket_client_example.py
```

The WebSocket examples include connection to `wss://api.xiaozhi.me/mcp/` which demonstrates real-world integration with external MCP services.

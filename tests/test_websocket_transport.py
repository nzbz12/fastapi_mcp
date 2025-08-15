import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from fastapi_mcp import FastApiMCP
from fastapi_mcp.transport.websocket import FastApiWebSocketTransport
from mcp.server.lowlevel.server import Server
from mcp.types import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse


@pytest.fixture
def simple_app():
    """Create a simple FastAPI app for testing."""
    app = FastAPI(title="Test WebSocket App")
    
    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"item_id": item_id, "name": f"Item {item_id}"}
    
    return app


@pytest.fixture
def mcp_server():
    """Create a basic MCP server for testing."""
    return Server("Test WebSocket Server", "Test WebSocket MCP server")


@pytest.fixture
def websocket_transport(mcp_server):
    """Create a WebSocket transport for testing."""
    return FastApiWebSocketTransport(mcp_server=mcp_server)


class TestFastApiWebSocketTransport:
    """Test cases for FastAPI WebSocket transport."""

    def test_transport_initialization(self, mcp_server):
        """Test transport initialization with different parameters."""
        transport = FastApiWebSocketTransport(
            mcp_server=mcp_server,
            external_ws_url="wss://example.com/ws",
            connection_timeout=60.0,
            ping_interval=30.0
        )
        
        assert transport.mcp_server == mcp_server
        assert transport.external_ws_url == "wss://example.com/ws"
        assert transport.connection_timeout == 60.0
        assert transport.ping_interval == 30.0
        assert transport.active_connections == {}

    @pytest.mark.asyncio
    async def test_websocket_connection_handling(self, websocket_transport):
        """Test basic WebSocket connection handling."""
        # Mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=[
            '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}',
            # Simulate WebSocket disconnect after first message
            Exception("WebSocket disconnected")
        ])
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        # Test connection handling
        with pytest.raises(Exception, match="WebSocket disconnected"):
            await websocket_transport.handle_fastapi_websocket(mock_websocket, "test-session")

        # Verify connection was accepted
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_message_processing(self, websocket_transport):
        """Test MCP message processing."""
        # Test initialization message
        init_message = JSONRPCMessage(root=JSONRPCRequest(
            jsonrpc="2.0",
            id="1",
            method="initialize",
            params={}
        ))
        
        response = await websocket_transport._process_mcp_message(init_message)
        
        assert response is not None
        assert isinstance(response, JSONRPCResponse)
        assert response.id == "1"
        assert "protocolVersion" in response.result
        assert "capabilities" in response.result

    @pytest.mark.asyncio
    async def test_tools_list_message(self, websocket_transport):
        """Test tools list message processing."""
        tools_message = JSONRPCMessage(root=JSONRPCRequest(
            jsonrpc="2.0",
            id="2",
            method="tools/list",
            params={}
        ))
        
        response = await websocket_transport._process_mcp_message(tools_message)
        
        assert response is not None
        assert isinstance(response, JSONRPCResponse)
        assert response.id == "2"
        assert "tools" in response.result

    @pytest.mark.asyncio
    async def test_external_websocket_connection_mock(self, websocket_transport):
        """Test external WebSocket connection with mocked websockets."""
        # Mock the websockets.connect function
        mock_connection = AsyncMock()
        mock_connection.closed = False
        mock_connection.send = AsyncMock()
        mock_connection.close = AsyncMock()
        
        # Mock the __aiter__ for listening
        mock_connection.__aiter__ = AsyncMock(return_value=iter([]))
        
        # Patch websockets.connect
        with pytest.mock.patch('websockets.connect', return_value=mock_connection):
            await websocket_transport.connect_to_external_websocket("wss://test.example.com")
            
            assert websocket_transport.external_ws_connection == mock_connection
            assert websocket_transport.external_connection_task is not None

    @pytest.mark.asyncio
    async def test_shutdown(self, websocket_transport):
        """Test transport shutdown."""
        # Add some mock connections
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.close = AsyncMock()
        websocket_transport.active_connections["test"] = mock_websocket
        
        # Mock external connection
        mock_external = AsyncMock()
        mock_external.closed = False
        mock_external.close = AsyncMock()
        websocket_transport.external_ws_connection = mock_external
        
        # Mock external task
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()
        websocket_transport.external_connection_task = mock_task
        
        await websocket_transport.shutdown()
        
        # Verify cleanup
        mock_websocket.close.assert_called_once()
        assert len(websocket_transport.active_connections) == 0
        mock_external.close.assert_called_once()


class TestFastApiMCPWebSocketIntegration:
    """Integration tests for FastAPI-MCP WebSocket functionality."""

    def test_mount_websocket(self, simple_app):
        """Test mounting WebSocket transport to FastAPI app."""
        mcp = FastApiMCP(simple_app)
        
        # Mount WebSocket transport
        mcp.mount_websocket(mount_path="/test-ws")
        
        # Verify WebSocket transport was created and stored
        assert mcp._websocket_transport is not None
        assert isinstance(mcp._websocket_transport, FastApiWebSocketTransport)

    def test_mount_websocket_with_external_url(self, simple_app):
        """Test mounting WebSocket transport with external URL."""
        mcp = FastApiMCP(simple_app)
        
        # Mount WebSocket transport with external URL
        external_url = "wss://api.example.com/mcp"
        mcp.mount_websocket(
            mount_path="/test-ws",
            external_ws_url=external_url
        )
        
        # Verify transport configuration
        assert mcp._websocket_transport is not None
        assert mcp._websocket_transport.external_ws_url == external_url

    @pytest.mark.asyncio
    async def test_mcp_shutdown_with_websocket(self, simple_app):
        """Test MCP shutdown with WebSocket transport."""
        mcp = FastApiMCP(simple_app)
        mcp.mount_websocket()
        
        # Mock the transport shutdown
        mcp._websocket_transport.shutdown = AsyncMock()
        
        await mcp.shutdown()
        
        # Verify shutdown was called
        mcp._websocket_transport.shutdown.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
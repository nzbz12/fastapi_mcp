import logging
import asyncio
import json
from typing import Any, Dict, Optional, Callable, Awaitable
from uuid import uuid4

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.client import WebSocketClientProtocol
from fastapi import WebSocket, WebSocketDisconnect
from mcp.server.lowlevel.server import Server
from mcp.types import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse, JSONRPCError, ErrorData
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class FastApiWebSocketTransport:
    """
    WebSocket transport for FastAPI-MCP that can act as both a WebSocket server 
    (handling incoming FastAPI WebSocket connections) and a WebSocket client 
    (connecting to external WebSocket servers).
    """

    def __init__(
        self,
        mcp_server: Server,
        external_ws_url: Optional[str] = None,
        connection_timeout: float = 30.0,
        ping_interval: Optional[float] = 20.0,
        ping_timeout: Optional[float] = 20.0,
        close_timeout: Optional[float] = 10.0,
    ):
        """
        Initialize the WebSocket transport.
        
        Args:
            mcp_server: The MCP server instance
            external_ws_url: Optional external WebSocket URL to connect to
            connection_timeout: Timeout for establishing connections
            ping_interval: Interval for sending ping frames
            ping_timeout: Timeout for ping-pong frames
            close_timeout: Timeout for closing connections
        """
        self.mcp_server = mcp_server
        self.external_ws_url = external_ws_url
        self.connection_timeout = connection_timeout
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.close_timeout = close_timeout
        
        # For server mode (handling incoming connections)
        self.active_connections: Dict[str, WebSocket] = {}
        
        # For client mode (connecting to external servers)  
        self.external_ws_connection: Optional[WebSocketClientProtocol] = None
        self.external_connection_task: Optional[asyncio.Task] = None
        self.connection_lock = asyncio.Lock()
        
        # Message handling
        self.pending_requests: Dict[str, asyncio.Event] = {}
        self.responses: Dict[str, JSONRPCResponse] = {}

    async def handle_fastapi_websocket(self, websocket: WebSocket, session_id: Optional[str] = None) -> None:
        """
        Handle an incoming FastAPI WebSocket connection.
        
        Args:
            websocket: The FastAPI WebSocket connection
            session_id: Optional session identifier
        """
        if session_id is None:
            session_id = str(uuid4())
            
        logger.info(f"New WebSocket connection established: {session_id}")
        
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                logger.debug(f"Received message from {session_id}: {data}")
                
                try:
                    # Parse JSON-RPC message
                    message = JSONRPCMessage.model_validate_json(data)
                    
                    # Process the message through MCP server
                    response = await self._process_mcp_message(message)
                    
                    if response:
                        # Send response back to client
                        response_json = response.model_dump_json()
                        await websocket.send_text(response_json)
                        logger.debug(f"Sent response to {session_id}: {response_json}")
                        
                except ValidationError as e:
                    logger.error(f"Invalid JSON-RPC message from {session_id}: {e}")
                    error_response = JSONRPCError(
                        jsonrpc="2.0",
                        id=None,
                        error=ErrorData(
                            code=-32700,
                            message="Parse error",
                            data={"validation_error": str(e)}
                        )
                    )
                    await websocket.send_text(error_response.model_dump_json())
                    
                except Exception as e:
                    logger.error(f"Error processing message from {session_id}: {e}")
                    error_response = JSONRPCError(
                        jsonrpc="2.0", 
                        id=None,
                        error=ErrorData(
                            code=-32603,
                            message="Internal error",
                            data={"error": str(e)}
                        )
                    )
                    await websocket.send_text(error_response.model_dump_json())
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket client {session_id} disconnected")
        except Exception as e:
            logger.error(f"Error in WebSocket connection {session_id}: {e}")
        finally:
            # Clean up connection
            if session_id in self.active_connections:
                del self.active_connections[session_id]
            logger.info(f"WebSocket connection {session_id} closed")

    async def connect_to_external_websocket(self, url: str) -> None:
        """
        Connect to an external WebSocket server.
        
        Args:
            url: The WebSocket URL to connect to
        """
        async with self.connection_lock:
            if self.external_ws_connection and not self.external_ws_connection.closed:
                logger.warning("Already connected to external WebSocket")
                return
                
            logger.info(f"Connecting to external WebSocket: {url}")
            
            try:
                self.external_ws_connection = await websockets.connect(
                    url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=self.close_timeout,
                )
                
                # Start listening for messages
                self.external_connection_task = asyncio.create_task(
                    self._listen_external_websocket()
                )
                
                logger.info("Successfully connected to external WebSocket")
                
            except Exception as e:
                logger.error(f"Failed to connect to external WebSocket {url}: {e}")
                raise

    async def send_to_external_websocket(self, message: JSONRPCMessage) -> Optional[JSONRPCResponse]:
        """
        Send a message to the external WebSocket server and wait for response.
        
        Args:
            message: The JSON-RPC message to send
            
        Returns:
            The response message, if any
        """
        if not self.external_ws_connection or self.external_ws_connection.closed:
            raise ConnectionError("Not connected to external WebSocket")
            
        message_json = message.model_dump_json()
        request_id = None
        
        # Extract request ID for response correlation
        if hasattr(message.root, 'id'):
            request_id = str(message.root.id)
            
        try:
            logger.debug(f"Sending to external WebSocket: {message_json}")
            await self.external_ws_connection.send(message_json)
            
            # If this is a request, wait for response
            if request_id and isinstance(message.root, JSONRPCRequest):
                # Set up response waiting
                response_event = asyncio.Event()
                self.pending_requests[request_id] = response_event
                
                try:
                    # Wait for response with timeout
                    await asyncio.wait_for(response_event.wait(), timeout=30.0)
                    return self.responses.pop(request_id, None)
                finally:
                    # Clean up
                    self.pending_requests.pop(request_id, None)
                    
        except Exception as e:
            logger.error(f"Error sending message to external WebSocket: {e}")
            raise

    async def _listen_external_websocket(self) -> None:
        """Listen for messages from the external WebSocket connection."""
        try:
            async for message in self.external_ws_connection:
                logger.debug(f"Received from external WebSocket: {message}")
                
                try:
                    # Parse the message
                    parsed_message = JSONRPCMessage.model_validate_json(message)
                    
                    # Handle response messages
                    if hasattr(parsed_message.root, 'id') and isinstance(parsed_message.root, JSONRPCResponse):
                        response_id = str(parsed_message.root.id)
                        if response_id in self.pending_requests:
                            self.responses[response_id] = parsed_message.root
                            self.pending_requests[response_id].set()
                        else:
                            logger.warning(f"Received response for unknown request ID: {response_id}")
                    
                    # Handle notification messages or requests from external server
                    else:
                        # Forward to MCP server if needed
                        await self._process_external_message(parsed_message)
                        
                except ValidationError as e:
                    logger.error(f"Invalid message from external WebSocket: {e}")
                except Exception as e:
                    logger.error(f"Error processing external WebSocket message: {e}")
                    
        except ConnectionClosed:
            logger.info("External WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in external WebSocket listener: {e}")
        finally:
            # Clean up pending requests
            for event in self.pending_requests.values():
                event.set()
            self.pending_requests.clear()

    async def _process_mcp_message(self, message: JSONRPCMessage) -> Optional[JSONRPCResponse]:
        """
        Process a message through the MCP server.
        
        Args:
            message: The JSON-RPC message to process
            
        Returns:
            The response message, if any
        """
        try:
            # Create a simple request/response handler
            # This is a simplified version - in practice, you might want to use
            # the full MCP transport infrastructure
            
            if isinstance(message.root, JSONRPCRequest):
                # Handle different MCP methods
                method = message.root.method
                params = message.root.params or {}
                
                if method == "initialize":
                    # Handle initialization
                    return JSONRPCResponse(
                        jsonrpc="2.0",
                        id=message.root.id,
                        result={
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {},
                                "resources": {},
                                "prompts": {},
                                "logging": {}
                            },
                            "serverInfo": {
                                "name": "FastAPI-MCP WebSocket Server",
                                "version": "0.4.0"
                            }
                        }
                    )
                elif method == "tools/list":
                    # Get tools from MCP server
                    tools = []
                    if hasattr(self.mcp_server, 'list_tools'):
                        tools_result = await self.mcp_server.list_tools()
                        tools = tools_result.tools if tools_result else []
                    
                    return JSONRPCResponse(
                        jsonrpc="2.0",
                        id=message.root.id,
                        result={"tools": [tool.model_dump() for tool in tools]}
                    )
                else:
                    # Forward other methods to the MCP server
                    # This would require implementing the full MCP protocol handling
                    logger.warning(f"Unhandled MCP method: {method}")
                    return JSONRPCError(
                        jsonrpc="2.0",
                        id=message.root.id,
                        error=ErrorData(
                            code=-32601,
                            message="Method not found",
                            data={"method": method}
                        )
                    )
            
        except Exception as e:
            logger.error(f"Error processing MCP message: {e}")
            return JSONRPCError(
                jsonrpc="2.0",
                id=getattr(message.root, 'id', None),
                error=ErrorData(
                    code=-32603,
                    message="Internal error",
                    data={"error": str(e)}
                )
            )
        
        return None

    async def _process_external_message(self, message: JSONRPCMessage) -> None:
        """
        Process a message received from external WebSocket server.
        
        Args:
            message: The message received from external server
        """
        # This could be used to handle notifications or requests from external servers
        logger.info(f"Received message from external server: {message}")

    async def disconnect_external_websocket(self) -> None:
        """Disconnect from the external WebSocket server."""
        async with self.connection_lock:
            if self.external_connection_task and not self.external_connection_task.done():
                self.external_connection_task.cancel()
                try:
                    await self.external_connection_task
                except asyncio.CancelledError:
                    pass
                    
            if self.external_ws_connection and not self.external_ws_connection.closed:
                await self.external_ws_connection.close()
                logger.info("Disconnected from external WebSocket")

    async def shutdown(self) -> None:
        """Shutdown the WebSocket transport and clean up all connections."""
        logger.info("Shutting down WebSocket transport")
        
        # Close all active FastAPI WebSocket connections
        for session_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket connection {session_id}: {e}")
        
        self.active_connections.clear()
        
        # Disconnect from external WebSocket
        await self.disconnect_external_websocket()
        
        logger.info("WebSocket transport shutdown complete")
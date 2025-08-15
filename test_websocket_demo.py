#!/usr/bin/env python3
"""
Simple demonstration script for the new WebSocket functionality in FastAPI-MCP.

This script creates a basic FastAPI app with MCP WebSocket transport and demonstrates
connecting to the external WebSocket service.
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# External WebSocket URL
EXTERNAL_WS_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjE2MSwiYWdlbnRJZCI6MTcwMSwiZW5kcG9pbnRJZCI6ImFnZW50XzE3MDEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzU1MjUzOTY3fQ.AQS81b4c9ic2jwjRRUBNErmIr34GZcodfTLams2BXwnC-4mBtDr12l-_YGMrL4Rc-PqScbpEjsW2bnl9DTmIJA"

def create_demo_app():
    """Create a demo FastAPI app with some endpoints."""
    app = FastAPI(
        title="WebSocket MCP Demo",
        description="Demonstration of FastAPI-MCP WebSocket functionality",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        return {
            "message": "WebSocket MCP Demo",
            "endpoints": {
                "websocket": "ws://localhost:8000/ws",
                "http_mcp": "http://localhost:8000/mcp"
            }
        }
    
    @app.get("/items/{item_id}")
    async def get_item(item_id: int, q: str = None):
        """Get an item by ID."""
        return {
            "item_id": item_id,
            "name": f"Item {item_id}",
            "query": q
        }
    
    @app.post("/items/")
    async def create_item(name: str, price: float):
        """Create a new item."""
        return {
            "message": "Item created",
            "item": {"name": name, "price": price}
        }
    
    return app


async def test_websocket_functionality():
    """Test the WebSocket functionality."""
    logger.info("Testing WebSocket functionality...")
    
    app = create_demo_app()
    mcp = FastApiMCP(app)
    
    try:
        # Mount WebSocket transport with external connection
        logger.info(f"Mounting WebSocket transport with external URL: {EXTERNAL_WS_URL}")
        mcp.mount_websocket(
            mount_path="/ws",
            external_ws_url=EXTERNAL_WS_URL
        )
        
        # Also mount HTTP for comparison
        mcp.mount_http()
        
        logger.info("✅ WebSocket transport mounted successfully!")
        logger.info("✅ HTTP transport mounted successfully!")
        
        # Wait a bit to see if external connection works
        await asyncio.sleep(2)
        
        # Test external WebSocket if available
        if mcp._websocket_transport and mcp._websocket_transport.external_ws_connection:
            logger.info("✅ External WebSocket connection established!")
        else:
            logger.warning("⚠️ External WebSocket connection not established")
            
    except Exception as e:
        logger.error(f"❌ Error testing WebSocket functionality: {e}")
    finally:
        # Clean up
        try:
            await mcp.shutdown()
            logger.info("✅ MCP server shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")


def main():
    """Main function to run the demo."""
    print("🚀 FastAPI-MCP WebSocket Demo")
    print("=" * 50)
    print(f"External WebSocket URL: {EXTERNAL_WS_URL}")
    print("=" * 50)
    
    try:
        # Run the test
        asyncio.run(test_websocket_functionality())
        print("\n✅ Demo completed successfully!")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
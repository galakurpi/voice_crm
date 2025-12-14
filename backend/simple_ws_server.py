"""
Simple WebSocket server for testing connection.
Run with: python simple_ws_server.py
"""
import asyncio
import websockets

async def handler(websocket, path=None):
    # websockets v12+ passes a single connection object; older versions pass (websocket, path).
    if path is None:
        path = getattr(websocket, "path", None)
        if path is None:
            path = getattr(getattr(websocket, "request", None), "path", None)
    print(f"Client connected! Path: {path}")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    print("Starting WebSocket server on ws://127.0.0.1:8001")
    async with websockets.serve(handler, "127.0.0.1", 8001):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.error("TestConsumer.connect() called")
        print("[DEBUG] TestConsumer.connect() called")
        await self.accept()
        logger.error("TestConsumer: WebSocket accepted")
        print("[DEBUG] TestConsumer: WebSocket accepted")

    async def disconnect(self, close_code):
        logger.error(f"TestConsumer: Disconnected with code {close_code}")
        print(f"[DEBUG] TestConsumer: Disconnected with code {close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        logger.error(f"TestConsumer: Received {text_data}")
        print(f"[DEBUG] TestConsumer: Received {text_data}")


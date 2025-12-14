import json
import os
import asyncio
import websockets
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .close_service import (
    search_leads, 
    add_lead_note, 
    get_lead_details, 
    create_lead, 
    update_lead_description, 
    create_opportunity,
    get_lead_notes,
    update_note,
    get_opportunities,
    list_leads
)

logger = logging.getLogger(__name__)

# Load API key - will be set from environment or .env file
def get_openai_api_key():
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.warning("OPENAI_API_KEY not found in environment")
        print("[WARNING] OPENAI_API_KEY not found in environment")
    return key

from websockets.protocol import State

class VoiceAgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle incoming WebSocket connection from the frontend."""
        try:
            await self.accept()
            print(f"[INFO] Frontend connected: {self.scope['client']}")
            logger.info(f"Frontend WebSocket connected from {self.scope['client']}")
            
            self.openai_ws = None
            self.openai_task = None
        except Exception as e:
            logger.error(f"Error in connect(): {e}", exc_info=True)
            print(f"[ERROR] Connection error: {e}")
            raise

    async def disconnect(self, close_code):
        """Cleanup when frontend disconnects."""
        print(f"[INFO] Frontend disconnected. Close code: {close_code}")
        logger.info(f"Frontend WebSocket disconnected. Close code: {close_code}")
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except:
                pass
        if hasattr(self, 'openai_task') and self.openai_task:
            self.openai_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        """Receive message from frontend and relay to OpenAI."""
        
        # Connect to OpenAI on first message if not already connected
        if self.openai_task is None:
            print("[INFO] Starting OpenAI connection...")
            self.openai_task = asyncio.create_task(self.connect_to_openai())
            # Wait a bit for connection to establish
            await asyncio.sleep(0.5)
        
        if self.openai_ws and self.openai_ws.state == State.OPEN:
            if text_data:
                # Direct relay of JSON messages (like input_audio_buffer.append)
                await self.openai_ws.send(text_data)

    async def connect_to_openai(self):
        """Main loop for OpenAI Realtime API connection."""
        api_key = get_openai_api_key()
        if not api_key:
            error_msg = "OPENAI_API_KEY not set in environment"
            print(f"[ERROR] {error_msg}")
            logger.error(error_msg)
            await self.send(text_data=json.dumps({"type": "error", "error": error_msg}))
            return
        
        # Debug: Log first/last few chars of key (for debugging without exposing full key)
        key_preview = f"{api_key[:10]}...{api_key[-10:]}" if len(api_key) > 20 else "***"
        print(f"[INFO] Using API key: {key_preview}")
        logger.info(f"Connecting to OpenAI with API key: {key_preview}")
            
        url = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        
        print(f"[INFO] Connecting to OpenAI Realtime API...")
        try:
            # websockets 14+ uses additional_headers instead of extra_headers
            async with websockets.connect(url, additional_headers=headers) as openai_ws:
                self.openai_ws = openai_ws
                
                # Initialize session with instructions and tools
                await self.send_session_update()
                
                async for message in openai_ws:
                    data = json.loads(message)
                    
                    # Log interesting events
                    msg_type = data.get("type")
                    if msg_type == "session.created":
                        print("[INFO] OpenAI Session Created")
                    elif msg_type == "response.done":
                        # Log full response details to debug why output is empty
                        print(f"[DEBUG] Full Response Done: {json.dumps(data)}")
                        usage = data.get("response", {}).get("usage", {})
                        print(f"[INFO] OpenAI Response Done. Usage: {usage}")
                    elif msg_type == "error":
                        print(f"[ERROR] OpenAI Error: {data}")
                    elif msg_type == "input_audio_buffer.speech_started":
                        print("[INFO] User started speaking")
                    elif msg_type == "input_audio_buffer.speech_stopped":
                        print("[INFO] User stopped speaking")
                    elif msg_type == "response.created":
                        print("[INFO] OpenAI Response Created")
                    elif msg_type == "response.audio.delta":
                        # Only log occasional deltas to prove it's working without spamming
                        pass 
                    elif msg_type == "conversation.item.input_audio_transcription.completed":
                        transcript = data.get("transcript", "")
                        print(f"[USER] {transcript}")
                    elif msg_type == "response.audio_transcript.done":
                        transcript = data.get("transcript", "")
                        print(f"[AI] {transcript}")

                    # Relay everything back to client first (audio, transcripts, etc.)
                    await self.send(text_data=message)
                    
                    # Intercept and handle tool calls
                    if data.get("type") == "response.function_call_arguments.done":
                        await self.handle_tool_call(data)
                        
        except InvalidStatus as e:
            error_msg = f"OpenAI API authentication failed (HTTP 401). Check your API key."
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Full error: {e}")
            logger.error(f"OpenAI authentication failed: {e}")
            # Send error to frontend
            await self.send(text_data=json.dumps({
                "type": "error", 
                "error": "OpenAI API authentication failed. Please check your API key."
            }))
            # Don't close the frontend connection - let user see the error
        except Exception as e:
            error_msg = f"OpenAI connection error: {e}"
            print(f"[ERROR] {error_msg}")
            logger.error(error_msg, exc_info=True)
            # Send error to frontend
            await self.send(text_data=json.dumps({
                "type": "error", 
                "error": str(e)
            }))
            # Don't close the frontend connection on OpenAI error - let it retry

    async def send_session_update(self):
        """Configure the OpenAI session with tools and instructions."""
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": (
                    "You are a helpful CRM voice assistant. "
                    "You can search for leads, get their details, create new leads, and add notes. "
                    "You can also create opportunities and update lead descriptions. "
                    "When adding a note, be concise. "
                    "Always ask for clarification if multiple leads match a search."
                ),
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "search_leads",
                        "description": "Search for leads by name or query.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "The search query (e.g., company name or person name)."},
                                "limit": {"type": "integer", "description": "Number of leads to return. Default 200."}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_lead_details",
                        "description": "Get full details of a specific lead.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "lead_id": {"type": "string", "description": "The ID of the lead."}
                            },
                            "required": ["lead_id"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "add_lead_note",
                        "description": "Add a note to a lead.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "lead_id": {"type": "string", "description": "The ID of the lead."},
                                "note_text": {"type": "string", "description": "The content of the note."}
                            },
                            "required": ["lead_id", "note_text"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "create_lead",
                        "description": "Create a new lead.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "company_name": {"type": "string", "description": "The name of the company."},
                                "contact_name": {"type": "string", "description": "The name of the contact person (optional)."},
                                "email": {"type": "string", "description": "The email of the contact (optional)."}
                            },
                            "required": ["company_name"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "update_lead_description",
                        "description": "Update the description of a lead.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "lead_id": {"type": "string", "description": "The ID of the lead."},
                                "description": {"type": "string", "description": "The new description text."}
                            },
                            "required": ["lead_id", "description"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "create_opportunity",
                        "description": "Create a new opportunity for a lead.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "lead_id": {"type": "string", "description": "The ID of the lead."},
                                "note": {"type": "string", "description": "Description or note for the opportunity."},
                                "value": {"type": "integer", "description": "The value of the opportunity in cents."},
                                "status": {"type": "string", "description": "The status (e.g., 'Active'). Optional."}
                            },
                            "required": ["lead_id", "note", "value"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_lead_notes",
                        "description": "Get all notes for a specific lead.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "lead_id": {"type": "string", "description": "The ID of the lead."}
                            },
                            "required": ["lead_id"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "update_note",
                        "description": "Update the content of a specific note.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "note_id": {"type": "string", "description": "The ID of the note to update."},
                                "new_text": {"type": "string", "description": "The new content for the note."}
                            },
                            "required": ["note_id", "new_text"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_opportunities",
                        "description": "Get a list of opportunities, sorted by newest first.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "description": "Number of opportunities to return. Default 200."},
                                "sort_by": {"type": "string", "description": "Sort field. Default '-date_created'."},
                                "status_label": {"type": "string", "description": "Optional status label to filter by (e.g. 'Active', 'Won')."}
                            },
                            "required": []
                        }
                    },
                    {
                        "type": "function",
                        "name": "list_leads",
                        "description": "List multiple leads, sorted by newest first.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "description": "Number of leads to return. Default 200."},
                                "query": {"type": "string", "description": "Optional search query."}
                            },
                            "required": []
                        }
                    }
                ],
                "tool_choice": "auto",
            }
        }
        await self.openai_ws.send(json.dumps(session_update))

    async def handle_tool_call(self, data):
        """Execute the tool and return results to OpenAI."""
        call_id = data.get("call_id")
        name = data.get("name")
        arguments = json.loads(data.get("arguments"))
        
        print(f"Executing tool: {name} with args: {arguments}")
        
        result = "Error: Tool not found"
        if name == "search_leads":
            result = await search_leads(arguments.get("query"), arguments.get("limit", 200))
        elif name == "get_lead_details":
            result = await get_lead_details(arguments.get("lead_id"))
        elif name == "add_lead_note":
            result = await add_lead_note(arguments.get("lead_id"), arguments.get("note_text"))
        elif name == "create_lead":
            result = await create_lead(
                arguments.get("company_name"), 
                arguments.get("contact_name"), 
                arguments.get("email")
            )
        elif name == "update_lead_description":
            result = await update_lead_description(arguments.get("lead_id"), arguments.get("description"))
        elif name == "create_opportunity":
            result = await create_opportunity(
                arguments.get("lead_id"), 
                arguments.get("note"), 
                arguments.get("value"),
                arguments.get("status", "Active")
            )
        elif name == "get_lead_notes":
            result = await get_lead_notes(arguments.get("lead_id"))
        elif name == "update_note":
            result = await update_note(arguments.get("note_id"), arguments.get("new_text"))
        elif name == "get_opportunities":
            result = await get_opportunities(
                arguments.get("limit", 200), 
                arguments.get("sort_by", "-date_created"),
                arguments.get("status_label")
            )
        elif name == "list_leads":
            result = await list_leads(arguments.get("limit", 200), arguments.get("query", ""))
            
        print(f"Tool Result: {result}")

        # 1. Send result back to OpenAI
        tool_output = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result
            }
        }
        await self.openai_ws.send(json.dumps(tool_output))
        
        # 2. Trigger response generation so the AI speaks the result
        await self.openai_ws.send(json.dumps({"type": "response.create"}))

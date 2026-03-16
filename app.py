"""
Drive Chat — FastAPI server
Chat with Claude while it can browse and read your Google Drive files.
"""

import json
import os
from typing import AsyncIterator

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from drive import DRIVE_TOOLS, execute_drive_tool
from gcalendar import CALENDAR_TOOLS, execute_calendar_tool

load_dotenv()

app = FastAPI(title="Drive Chat", description="Chat with Claude + your Google Drive")

# Conversation history per session (in-memory; keyed by session ID)
# For production, replace with a database or Redis.
sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """You are a helpful assistant with access to the user's Google Drive and Google Calendar.

When the user asks about their files, documents, spreadsheets, or any content stored
in their Drive, use the available Drive tools to find and read the relevant files before
answering. Always cite the file name when you reference content from Drive.

When the user asks about their schedule, events, or wants to create a calendar event,
use the available Calendar tools. When creating events, infer the timezone from context
(e.g. if the user mentions "Philippine time", use Asia/Manila). Default event duration
to 1 hour if not specified.

Be concise but thorough. If a file is too large to read in full, summarize what
you found and offer to look at specific sections."""


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ClearRequest(BaseModel):
    session_id: str = "default"


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the chat UI."""
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html")) as f:
        return f.read()


@app.post("/chat/clear")
async def clear_session(req: ClearRequest):
    sessions.pop(req.session_id, None)
    return {"status": "cleared"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Stream a chat response from Claude.
    Claude may call Drive tools mid-stream; tool results are injected automatically.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    # Get or create conversation history
    history = sessions.setdefault(req.session_id, [])
    history.append({"role": "user", "content": req.message})

    return StreamingResponse(
        _stream_response(client, history, req.session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_response(
    client: anthropic.Anthropic,
    history: list[dict],
    session_id: str,
) -> AsyncIterator[str]:
    """
    Agentic loop: stream Claude's reply, handle tool calls, then continue.
    Yields SSE-formatted events.
    """
    MAX_TOOL_ROUNDS = 5  # prevent runaway loops

    for _round in range(MAX_TOOL_ROUNDS):
        # Collect the full assistant response for this round
        full_content: list = []
        text_so_far = ""

        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=DRIVE_TOOLS + CALENDAR_TOOLS,
            thinking={"type": "adaptive"},
            messages=history,
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "text":
                        full_content.append({"type": "text", "text": ""})
                    elif block.type == "tool_use":
                        full_content.append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": {},
                            }
                        )
                    elif block.type == "thinking":
                        full_content.append({"type": "thinking", "thinking": ""})

                elif event.type == "content_block_delta":
                    delta = event.delta
                    idx = event.index
                    if delta.type == "text_delta":
                        full_content[idx]["text"] += delta.text
                        text_so_far += delta.text
                        # Stream text tokens to the browser
                        yield f"data: {json.dumps({'type': 'text', 'text': delta.text})}\n\n"
                    elif delta.type == "input_json_delta":
                        # Accumulate tool input JSON
                        existing = full_content[idx].get("_raw_input", "")
                        full_content[idx]["_raw_input"] = existing + delta.partial_json
                    elif delta.type == "thinking_delta":
                        full_content[idx]["thinking"] += delta.thinking

            final = stream.get_final_message()

        # Parse accumulated tool inputs
        for block in full_content:
            if block["type"] == "tool_use" and "_raw_input" in block:
                try:
                    block["input"] = json.loads(block["_raw_input"])
                except json.JSONDecodeError:
                    block["input"] = {}
                del block["_raw_input"]

        # Append assistant turn to history
        history.append({"role": "assistant", "content": full_content})

        # Check if we're done
        if final.stop_reason != "tool_use":
            break

        # Execute tool calls and build tool_result messages
        tool_results = []
        for block in full_content:
            if block["type"] != "tool_use":
                continue

            tool_name = block["name"]
            tool_input = block["input"]
            tool_id = block["id"]

            # Tell the browser a tool is running
            yield (
                f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'input': tool_input})}\n\n"
            )

            if tool_name.startswith("calendar_"):
                result = execute_calendar_tool(tool_name, tool_input)
            else:
                result = execute_drive_tool(tool_name, tool_input)

            yield (
                f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'preview': result[:200]})}\n\n"
            )

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                }
            )

        history.append({"role": "user", "content": tool_results})

    # Signal completion
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

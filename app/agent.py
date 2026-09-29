# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_item,
    check_reorder_alerts,
    find_nearby_places,
    generate_item_image,
    generate_item_video,
    geocode_address,
    get_item,
    list_items,
    search_external_market_prices,
)


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "AI inventory assistant that helps users view, search, and manage items stored in Firestore. "
        "You remember and track all stated user facts, preferences, and allergies (e.g. food allergies, chemical sensitivities, or dietary restrictions) "
        "across conversations and ensure any item suggestions or inventory responses prioritize user safety."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


MEMORY_BANK_ID = "132660475937685504"
PROJECT_ID = "qwiklabs-gcp-01-c7b63de2e7a5"
LOCATION = "us-east1"


def get_memory_service() -> VertexAiMemoryBankService:
    """Configures Vertex AI Memory Bank service for redeployment."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to send session data to Memory Bank for long-term extraction."""
    await callback_context.add_session_to_memory()
    return None



def _get_code_executor() -> AgentEngineSandboxCodeExecutor:
    metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            meta = json.load(f)
        sandbox_name = meta.get("sandbox_resource_name")
        engine_name = meta.get("remote_agent_runtime_id")

        if sandbox_name:
            return AgentEngineSandboxCodeExecutor(sandbox_resource_name=sandbox_name)
        elif engine_name:
            return AgentEngineSandboxCodeExecutor(agent_engine_resource_name=engine_name)

    return AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name="projects/606763693613/locations/us-east1/reasoningEngines/132660475937685504"
    )


def get_weather(query: str) -> str:

    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        get_weather,
        get_current_time,
        list_items,
        get_item,
        add_item,
        check_reorder_alerts,
        search_external_market_prices,
        geocode_address,
        find_nearby_places,
        generate_item_image,
        generate_item_video,
        PreloadMemoryTool(),
    ],
    code_executor=_get_code_executor(),
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)




app = App(
    root_agent=root_agent,
    name="app",
)


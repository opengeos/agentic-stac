"""STAC search agent powered by LiteLLM."""

import json
import logging
from typing import Optional

import litellm

from .catalogs import CATALOGS, resolve_catalog
from .tools import TOOLS, TOOL_DISPATCH

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a geospatial data search assistant that helps users find satellite \
imagery and other Earth observation data from STAC (SpatioTemporal Asset \
Catalog) APIs.

Current catalog: {catalog_name} ({catalog_url})

## Your Workflow

1. When a user mentions a location by name (e.g., "San Francisco", "Amazon \
rainforest"), FIRST call geocode_location to get the bounding box coordinates.

2. If unsure which collection to search, call list_collections to see what is \
available, optionally filtering by keyword.

3. Use get_collection_info to learn about a collection's properties, temporal \
range, and available bands before searching if needed.

4. Call search_stac_items with appropriate parameters to find matching items.

## Key Knowledge

- Sentinel-2 L2A: Collection ID is usually "sentinel-2-l2a". Use \
query {{"eo:cloud_cover": {{"lt": N}}}} for cloud cover filtering. Global \
coverage, 10m resolution, revisit every 5 days.
- Landsat Collection 2: Collection ID is usually "landsat-c2-l2". 30m \
resolution, global coverage.
- NAIP: Collection ID is "naip". 1m resolution aerial imagery, USA only. \
No cloud cover filter available.
- Copernicus DEM: Collection ID is "cop-dem-glo-30". 30m global elevation \
data. No temporal filter needed.

## Parameter Formats

- bbox: [west, south, east, north] in WGS84 decimal degrees
- datetime_range: ISO 8601 format, e.g., "2024-01-01/2024-01-31"
- query: Property filters, e.g., {{"eo:cloud_cover": {{"lt": 10}}}}
- Always pass catalog_url as "{catalog_url}" for tool calls unless the user \
specifies a different catalog.

## Response Format

After retrieving results, summarize them clearly including:
- Number of items found
- Date range of results
- Cloud cover percentage (if applicable)
- Available assets/bands
- Item IDs for reference

Be concise but informative. If no results are found, suggest broadening the \
search parameters (wider date range, larger area, higher cloud cover threshold).
"""


class STACAgent:
    """AI agent for searching STAC catalogs using natural language.

    Uses LiteLLM to support multiple LLM providers (OpenAI, Anthropic,
    Amazon Bedrock, Ollama) with a unified interface.

    Args:
        model: LLM model identifier. Examples:
            - "gpt-4.1" (OpenAI)
            - "anthropic/claude-sonnet-4-6-20250627" (Anthropic)
            - "bedrock/anthropic.claude-sonnet-4-6-20250627-v1:0" (AWS Bedrock)
            - "ollama/llama3.1" (Ollama local)
        catalog: STAC catalog alias (e.g., "pc", "earth-search") or full URL.
        **kwargs: Extra keyword arguments passed to litellm.completion(),
            such as temperature, max_tokens, or api_base.

    Example:
        >>> agent = STACAgent(model="gpt-4.1", catalog="earth-search")
        >>> result = agent.chat("Find Sentinel-2 images over Paris from 2024")
        >>> print(result)
    """

    def __init__(
        self,
        model: str = "gpt-4.1",
        catalog: str = "planetary-computer",
        **kwargs,
    ):
        """Initialize the STAC search agent.

        Args:
            model: LLM model identifier string.
            catalog: STAC catalog alias or URL.
            **kwargs: Extra arguments for litellm.completion().
        """
        self.model = model
        self.catalog_url = resolve_catalog(catalog)
        self.kwargs = kwargs

        # Determine a human-readable catalog name
        catalog_name = catalog
        for alias, url in CATALOGS.items():
            if url == self.catalog_url and "-" in alias:
                catalog_name = alias
                break

        self.system_prompt = SYSTEM_PROMPT.format(
            catalog_url=self.catalog_url,
            catalog_name=catalog_name,
        )

        self.messages = [{"role": "system", "content": self.system_prompt}]

    def chat(self, message: str, max_iterations: int = 20) -> str:
        """Send a message and get a response, executing tool calls as needed.

        This method handles the full tool-calling loop: the message is sent
        to the LLM, and if the LLM requests tool calls, those tools are
        executed and results fed back until the LLM produces a final text
        response.

        Args:
            message: The user's natural language query about geospatial data.
            max_iterations: Maximum number of LLM call iterations to prevent
                infinite tool-calling loops. Defaults to 20.

        Returns:
            The agent's text response as a string.
        """
        self.messages.append({"role": "user", "content": message})

        for _iteration in range(max_iterations):
            response = litellm.completion(
                model=self.model,
                messages=self.messages,
                tools=TOOLS,
                **self.kwargs,
            )
            choice = response.choices[0]
            assistant_message = choice.message

            # Append assistant message to history
            self.messages.append(assistant_message.model_dump())

            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}

                    logger.info("Calling tool %s with args %s", fn_name, fn_args)

                    fn = TOOL_DISPATCH.get(fn_name)
                    if fn is None:
                        result = json.dumps({"error": f"Unknown tool: {fn_name}"})
                    else:
                        result = fn(**fn_args)

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
            else:
                return assistant_message.content

        logger.warning("Reached max iterations (%d)", max_iterations)
        return assistant_message.content or "Max iterations reached."

    def interactive(self):
        """Start an interactive multi-turn conversation in the terminal.

        Reads user input in a loop, sends each message via ``chat()``,
        and prints the response. The conversation history is preserved
        across turns. Type 'quit', 'exit', or 'q' to end the session.
        """
        print("STAC Agent (type 'quit' to exit)")
        print(f"  Catalog: {self.catalog_url}")
        print(f"  Model:   {self.model}")
        print("-" * 50)

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if not user_input:
                continue

            try:
                response = self.chat(user_input)
                print(f"\nAgent: {response}")
            except Exception as e:
                print(f"\nError: {e}")
                logger.exception("Error during chat")

    def reset(self):
        """Clear the conversation history and start fresh.

        The system prompt is preserved. Only user, assistant, and tool
        messages are removed.
        """
        self.messages = [self.messages[0]]

"""Integration tests for the STACAgent using a local Ollama model.

These tests require:
- Ollama running locally at http://localhost:11434
- A model pulled (e.g., ollama pull qwen3)
- Network access to STAC APIs
"""

import json

import pytest

from agentic_stac import STACAgent

OLLAMA_MODEL = "ollama/qwen3"
OLLAMA_BASE = "http://localhost:11434"


def ollama_available():
    """Check if Ollama is running and the model is available."""
    try:
        import requests

        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        models = [m["name"] for m in resp.json().get("models", [])]
        return any("qwen3" in m for m in models)
    except Exception:
        return False


requires_ollama = pytest.mark.skipif(
    not ollama_available(),
    reason="Ollama with qwen3 not available",
)


class TestSTACAgentInit:
    """Tests for agent initialization (no LLM required)."""

    def test_default_init(self):
        """Default initialization with GPT-4.1 and Planetary Computer."""
        agent = STACAgent()
        assert agent.model == "gpt-4.1"
        assert "planetarycomputer" in agent.catalog_url

    def test_custom_catalog(self):
        """Initialize with a catalog alias."""
        agent = STACAgent(catalog="earth-search")
        assert "earth-search" in agent.catalog_url

    def test_custom_url(self):
        """Initialize with a custom catalog URL."""
        url = "https://my-stac.example.com/v1"
        agent = STACAgent(catalog=url)
        assert agent.catalog_url == url

    def test_system_prompt_contains_catalog(self):
        """The system prompt includes the catalog URL."""
        agent = STACAgent(catalog="earth-search")
        assert agent.catalog_url in agent.system_prompt

    def test_reset_clears_history(self):
        """Reset keeps only the system message."""
        agent = STACAgent()
        agent.messages.append({"role": "user", "content": "test"})
        agent.messages.append({"role": "assistant", "content": "reply"})
        assert len(agent.messages) == 3
        agent.reset()
        assert len(agent.messages) == 1
        assert agent.messages[0]["role"] == "system"


@requires_ollama
class TestSTACAgentWithOllama:
    """Integration tests using a local Ollama model."""

    def _make_agent(self, catalog="earth-search"):
        """Create an agent configured for local Ollama."""
        return STACAgent(
            model=OLLAMA_MODEL,
            catalog=catalog,
            api_base=OLLAMA_BASE,
        )

    def test_list_collections(self):
        """Ask the agent to list collections."""
        agent = self._make_agent()
        result = agent.chat(
            "List the available collections. Just list their names.",
            max_iterations=10,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_with_location(self):
        """Search for imagery over a named location."""
        agent = self._make_agent()
        result = agent.chat(
            "Find 3 Sentinel-2 images over San Francisco from January 2024.",
            max_iterations=10,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multi_turn_conversation(self):
        """Multi-turn conversation preserves context."""
        agent = self._make_agent()
        result1 = agent.chat(
            "What Sentinel collections are available?", max_iterations=10
        )
        assert isinstance(result1, str)

        result2 = agent.chat(
            "Search that collection for images over Denver from 2024 "
            "with low cloud cover.",
            max_iterations=10,
        )
        assert isinstance(result2, str)
        assert len(result2) > 0

    def test_reset_and_new_query(self):
        """After reset, the agent starts fresh."""
        agent = self._make_agent()
        agent.chat("List collections.", max_iterations=10)
        assert len(agent.messages) > 2

        agent.reset()
        assert len(agent.messages) == 1

        result = agent.chat("What collections are available?", max_iterations=10)
        assert isinstance(result, str)

# agentic-stac

[![PyPI version](https://badge.fury.io/py/agentic-stac.svg)](https://pypi.org/project/agentic-stac/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI Agents for SpatioTemporal Asset Catalogs (STAC). Search any STAC catalog using natural language with support for multiple LLM providers.

## Features

- **Natural language search** - Ask for satellite imagery in plain English
- **Multi-provider LLM support** - OpenAI, Anthropic, Amazon Bedrock, Ollama (local)
- **Any STAC catalog** - Planetary Computer, Earth Search, NASA CMR, or custom URLs
- **Automatic geocoding** - Mention places by name, not coordinates
- **Structured results** - Item IDs, dates, cloud cover, asset links, and more
- **Interactive & programmatic** - CLI chat mode or Python API

## Installation

```bash
pip install agentic-stac
```

Or install from source:

```bash
git clone https://github.com/opengeos/agentic-stac.git
cd agentic-stac
pip install -e .
```

## Quick Start

### Python API

```python
from agentic_stac import STACAgent

# Create an agent (default: OpenAI GPT-4.1 + Planetary Computer)
agent = STACAgent()

# Search with natural language
result = agent.chat(
    "Find Sentinel-2 images over San Francisco from January 2024 "
    "with less than 10% cloud cover"
)
print(result)
```

### CLI

```bash
# Interactive chat
agentic-stac chat

# Single query
agentic-stac ask "List available collections on Earth Search" -c earth-search
```

## Supported LLM Providers

Set the appropriate API key as an environment variable, then pass the model string:

| Provider | Model Example | Environment Variable |
|----------|--------------|---------------------|
| OpenAI | `gpt-4.1` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-6-20250627` | `ANTHROPIC_API_KEY` |
| Amazon Bedrock | `bedrock/anthropic.claude-sonnet-4-6-20250627-v1:0` | AWS credentials |
| Ollama (local) | `ollama/llama3.1` | None (local) |

```python
# OpenAI (default)
agent = STACAgent(model="gpt-4.1")

# Anthropic Claude
agent = STACAgent(model="anthropic/claude-sonnet-4-6-20250627")

# AWS Bedrock
agent = STACAgent(model="bedrock/anthropic.claude-sonnet-4-6-20250627-v1:0")

# Ollama (local, no API key needed)
agent = STACAgent(model="ollama/llama3.1", api_base="http://localhost:11434")
```

## Pre-configured Catalogs

| Alias | Catalog | URL |
|-------|---------|-----|
| `planetary-computer`, `pc` | Microsoft Planetary Computer | `https://planetarycomputer.microsoft.com/api/stac/v1` |
| `earth-search`, `es` | Element 84 Earth Search | `https://earth-search.aws.element84.com/v1` |
| `nasa-cmr`, `cmr` | NASA CMR-STAC | `https://cmr.earthdata.nasa.gov/stac/` |

```python
# Use a pre-configured catalog
agent = STACAgent(catalog="earth-search")

# Use a custom STAC API URL
agent = STACAgent(catalog="https://my-stac-server.com/api/v1")
```

## Examples

### Search for Sentinel-2 imagery

```python
agent = STACAgent(catalog="earth-search")
result = agent.chat(
    "Find Sentinel-2 images over the Amazon rainforest "
    "from June 2024 with less than 20% cloud cover"
)
```

### Discover available collections

```python
agent = STACAgent(catalog="planetary-computer")
result = agent.chat("What Landsat collections are available?")
```

### Multi-turn conversation

```python
agent = STACAgent()

# First query
agent.chat("What collections have data over New York City?")

# Follow-up
agent.chat("Search the Sentinel-2 collection for images from last summer")

# Reset conversation
agent.reset()
```

### CLI with different providers

```bash
# Use Anthropic Claude
agentic-stac chat -m anthropic/claude-sonnet-4-6-20250627

# Use Earth Search catalog
agentic-stac chat -c earth-search

# Single query with Ollama
agentic-stac ask "Find NAIP imagery over Denver" -m ollama/llama3.1
```

## License

MIT License. See [LICENSE](LICENSE) for details.

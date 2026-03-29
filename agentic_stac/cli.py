"""Command-line interface for agentic-stac."""

import click


@click.group()
@click.version_option(package_name="agentic-stac")
def main():
    """AI Agents for SpatioTemporal Asset Catalogs (STAC)."""


@main.command()
@click.option(
    "--model",
    "-m",
    default="gpt-4.1",
    show_default=True,
    help="LLM model string (e.g., gpt-4.1, anthropic/claude-sonnet-4-6-20250627, ollama/llama3.1).",
)
@click.option(
    "--catalog",
    "-c",
    default="planetary-computer",
    show_default=True,
    help="STAC catalog alias or URL.",
)
def chat(model, catalog):
    """Start an interactive chat session with the STAC agent."""
    from agentic_stac import STACAgent

    agent = STACAgent(model=model, catalog=catalog)
    agent.interactive()


@main.command()
@click.argument("query")
@click.option(
    "--model",
    "-m",
    default="gpt-4.1",
    show_default=True,
    help="LLM model string.",
)
@click.option(
    "--catalog",
    "-c",
    default="planetary-computer",
    show_default=True,
    help="STAC catalog alias or URL.",
)
def ask(query, model, catalog):
    """Send a single query to the STAC agent and print the response."""
    from agentic_stac import STACAgent

    agent = STACAgent(model=model, catalog=catalog)
    result = agent.chat(query)
    click.echo(result)

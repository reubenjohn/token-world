# Getting Started

## Prerequisites

- **Python 3.12+** -- [Download](https://www.python.org/downloads/)
- **uv** -- [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Anthropic API key** -- [Get one here](https://console.anthropic.com/)

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/reubenjohn/token-world.git
cd token-world
uv sync
```

## Configuration

Copy the environment template and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and set your `ANTHROPIC_API_KEY`.

## Running Tests

Verify everything is working:

```bash
uv run pytest
```

## Basic Usage

Token World is under active development (simulation engine lands in Phase 05). The graph foundation, mechanic framework, spatial/temporal indices, and visualisation tooling are ready today.

### Create a universe

```bash
uv run token-world create my-world
uv run token-world list
```

This scaffolds a universe folder with `CLAUDE.md`, `.mcp.json`, `universe.db`, `mechanics/`, and `agents/`.

### Visualise the graph

Once a universe has state, render it as a [Mermaid](https://mermaid.js.org/) flowchart:

```bash
uv run token-world viz-graph my-world --node alice --depth 2
```

See the [viz-graph guide](viz-graph.md) for the full CLI reference (filters, output modes, styling).

## Next Steps

- Read the [Architecture Overview](../design/architecture.md) to understand how the system works
- Browse the [viz-graph guide](viz-graph.md) for graph inspection tooling
- Check out the [pyproject.toml](https://github.com/reubenjohn/token-world/blob/main/pyproject.toml) for project configuration details

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

*Token World is under active development. Usage instructions will be added as the simulation engine takes shape.*

## Next Steps

- Read the [Architecture Overview](../design/architecture.md) to understand how the system works
- Check out the [pyproject.toml](https://github.com/reubenjohn/token-world/blob/main/pyproject.toml) for project configuration details

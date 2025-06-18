# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a Temporal-based Python application that monitors and tests Testflinger agents in specific hardware racks. The architecture consists of:

- **workflow.py**: Core Temporal workflow (`AgentJobWorkflow`) and activities for interacting with MAAS API and Testflinger API
- **worker.py**: Temporal worker that executes workflows and activities 
- **client.py**: CLI client to start workflows for specific racks
- **docker-compose.yml**: Full stack including Temporal server, PostgreSQL, UI, and worker containers

### Key Components

1. **Temporal Workflow**: `AgentJobWorkflow` runs continuously (6-hour cycles) via `continue_as_new`
2. **Activities**: Non-deterministic operations (API calls to MAAS/Testflinger) are isolated in Temporal activities
3. **MAAS Integration**: Fetches machines by rack tag using OAuth1 authentication
4. **Testflinger Integration**: Monitors agents, submits jobs, and tracks completion status

### Error Handling & Timeouts

All HTTP requests have 30-second timeouts to prevent hanging. Activities have 90-second Temporal timeouts. Key resilience features:

- **MAAS API failures**: Return empty list, workflow continues and retries in 6 hours
- **Testflinger API failures**: Individual agent failures don't kill workflow; HTTP errors (403 Forbidden, etc.) return empty lists
- **Network timeouts**: Caught and logged, workflow continues with other agents
- **Agent data retrieval**: Uses Temporal RetryPolicy (3 attempts, 1-hour intervals)

## Development Commands

### Formatting

Use black to format Python code

### Linting

Use ruff check

### Running the Application

```bash
# Start the full stack (Temporal + worker)
docker-compose up

# Run worker locally (requires Temporal server)
uv run worker.py

# Start a workflow for a specific rack
uv run client.py <rack_name>
```

### Package Management

```bash
# Add dependencies
uv add <package>

# Install dependencies
uv sync

# Run scripts
uv run <script.py>
```

### Docker Operations

```bash
# Build worker image
docker-compose build worker

# Scale workers
docker-compose up --scale worker=3

# View Temporal UI
# http://localhost:8000
```

## Environment Variables

Required for MAAS API access:
- `MAAS_URL`: MAAS server URL
- `MAAS_API_KEY`: OAuth credentials in format "consumer_key:token_key:token_secret"

## Our relationship

- Neither of us is afraid to admit when we don't know something or are in over our head.
- When we think we're right, it is *good* to push back, but we should cite evidence.

## Writing Code

- We prefer simple, clean, maintainable solutions over clever or complex ones, even if the latter are more concise or performant. Readability and maintainability are primary concerns unless explicitly asked for.
- When modifying code, match the style and formatting of surrounding code, even if it differs from standard style guidelines. Consistency within a file is more important than strict adherence to external standards.
- When writing comments, avoid referring to temporal context about refactors or recent changes. Comments should be evergreen and describe the code as is, not how it evolved or was recently changed.
- NEVER name things as "improved" or "new" or "enhanced" etc. Code naming should be evergreen. What is new today will be "old" someday.
- NEVER skip or comment out tests that are failing. When a test fails it is important to debug it, not just skip it. Ask me for help if you need it.

## Getting Help

- ALWAYS ask for clarification rather than making assumptions
- If you're having trouble with something, it's ok to stop and ask for help. Especially if it's something I might be better at.
- Ask me questions frequently, I'm here to help you.

## Python preferences

- I prefer `uv` for package management. I like adding packages with `uv add` and run the script with `uv run`.

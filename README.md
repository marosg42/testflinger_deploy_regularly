# Testflinger Deploy Regularly

An automated testing system that continuously monitors and deploys hardware machines in specific racks using Temporal workflows. The system integrates with MAAS (Metal as a Service) to discover machines and Testflinger to manage deployment jobs.

## Architecture

The application uses a Temporal-based architecture for reliable, long-running workflows:

- **workflow.py**: Core Temporal workflow (`AgentJobWorkflow`) and activities for MAAS/Testflinger API interactions
- **worker.py**: Temporal worker that executes workflows and activities
- **client.py**: CLI client to start workflows for specific hardware racks
- **docker-compose.yml**: Complete infrastructure stack with Temporal server, PostgreSQL, UI, and workers

### How It Works

1. **Machine Discovery**: Queries MAAS API to find machines tagged with specific rack identifiers
2. **Agent Filtering**: Identifies machines that have corresponding Testflinger agents in TOR3 location
3. **Job Submission**: Submits deployment jobs to Testflinger for machines in "waiting" state
4. **Job Monitoring**: Tracks job completion status until finished or cancelled
5. **Continuous Cycle**: Waits 6 hours then restarts the workflow using `continue_as_new`

Each rack runs its own independent workflow, allowing parallel processing of multiple hardware racks.

## Prerequisites

- Docker and Docker Compose
- MAAS server access with API credentials
- Access to Testflinger service

## Setup

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
MAAS_URL=https://your-maas-server.com/MAAS/
MAAS_API_KEY=consumer_key:token_key:token_secret
```

The MAAS API key format is: `consumer_key:token_key:token_secret` (OAuth1 credentials)

### Start the Infrastructure

```bash
# Start Temporal server, PostgreSQL, UI, and workers
docker-compose up

# Scale workers if needed
docker-compose up --scale worker=3
```

This starts:

- **Temporal Server**: Core workflow engine (port 7233)
- **PostgreSQL**: Temporal's database backend
- **Temporal UI**: Web interface at http://localhost:8000
- **Workers**: Python workers that execute workflow activities

## Usage

### Start a Workflow for a Rack

```bash
# Start monitoring and deployment for a specific rack
uv run client.py rack-name
```

This creates a workflow named `testflinger-agents-{rack-name}` that runs continuously.

### Monitor Workflows

- **Temporal UI**: Visit http://localhost:8000 to see workflow status, history, and logs
- **Logs**: Check Docker logs for detailed activity information

### Development

```bash
# Install dependencies
uv sync

# Format code
black *.py

# Lint code
ruff check

# Run worker locally (requires Temporal server running)
uv run worker.py
```

## Workflow Behavior

- **6-Hour Cycles**: Each workflow runs continuously, waiting 6 hours between deployment rounds
- **State Filtering**: Only processes machines in "waiting" state, skips others
- **Job Tracking**: Monitors each deployment job until completion or cancellation
- **Error Handling**: Temporal provides automatic retry and failure handling
- **Parallel Racks**: Multiple racks can run simultaneously as independent workflows

## Monitoring and Debugging

- Use the Temporal UI to inspect workflow execution, view logs, and debug issues
- Each workflow maintains detailed activity logs for troubleshooting
- Failed activities are automatically retried according to Temporal's retry policies

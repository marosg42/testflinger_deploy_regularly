import asyncio
import logging
import sys

from temporalio.client import Client


async def main(rack: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("testflinger_client")
    client = await Client.connect("cml-test.lan:7233")
    handle = await client.start_workflow(
        "AgentJobWorkflow",
        args=[rack],
        id=f"testflinger-agents-{rack}",
        task_queue="testflinger-task-queue",
    )
    logger.info(f"Started workflow with workflow_id: {handle.id}, run_id: {handle.first_execution_run_id}")

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))

import asyncio
import logging
from temporalio.worker import Worker
from workflow import submit_job_activity, monitor_job_activity, get_machines_activity, get_tor3_agents_activity, get_agent_data_activity, AgentJobWorkflow

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    async def main():
        # Connect to Temporal server (default localhost:7233)
        from temporalio.client import Client
        client = await Client.connect("temporal:7233")
        # Start worker for the workflow and activities
        worker = Worker(
            client,
            task_queue="testflinger-task-queue",
            workflows=[AgentJobWorkflow],
            activities=[submit_job_activity, monitor_job_activity, get_machines_activity, get_tor3_agents_activity, get_agent_data_activity],
        )
        print("Worker started. Waiting for workflows...")
        await worker.run()
    asyncio.run(main())

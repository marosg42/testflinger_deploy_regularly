import logging
from temporalio import activity, workflow
from typing import Optional
from datetime import timedelta
from temporalio.common import RetryPolicy
from dotenv import load_dotenv


logger = logging.getLogger("testflinger_deploy")

# Deterministic helpers (no requests/os/requests_oauthlib)
def get_auth(api_key):
    from requests_oauthlib import OAuth1  # Import inside function for Temporal compatibility
    keys = api_key.split(":")
    auth = OAuth1(keys[0], "", keys[1], keys[2])
    return auth

# All non-deterministic code must be in activities
@activity.defn
async def get_machines_activity(rack):
    import os
    import requests

    logger.info(f"{rack=}")
    logger.info(f"load_dotenv={load_dotenv()}")
    maas_url = os.environ.get("MAAS_URL")
    api_key = os.environ.get("MAAS_API_KEY")
    auth = get_auth(api_key)
    url = maas_url + "api/2.0/machines/"
    s = requests.Session()
    req = requests.Request(
        "GET",
        url,
        auth=auth,
        params={"tags": rack},
    )
    prepped = req.prepare()
    resp = s.send(prepped)
    if resp.status_code != 200:
        logger.error(f"No machines found, exiting")
        return []
    machines = resp.json()
    return [machine["hostname"] for machine in machines]

@activity.defn
async def get_tor3_agents_activity():
    import requests
    url = "https://testflinger.canonical.com/v1/agents/data"
    response = requests.get(url)
    response.raise_for_status()
    agents = response.json()
    filtered = [
        agent["name"]
        for agent in agents
        if "location" in agent and "TOR3" in agent["location"]
    ]
    return filtered

@activity.defn
async def get_agent_data_activity(agent_name):
    import requests
    url = "https://testflinger.canonical.com/v1/agents/data"
    response = requests.get(url)
    response.raise_for_status()
    agents = response.json()
    for agent in agents:
        if agent.get("name") == agent_name:
            return (agent_name, agent.get("state"), agent.get("provision_streak_count"), agent.get("provision_streak_type"))
    return None

@activity.defn
async def submit_job_activity(agent_name: str) -> Optional[str]:
    import requests
    url = "https://testflinger.canonical.com/v1/job"
    headers = {"Content-Type": "application/json"}
    payload = {
        "job_queue": agent_name,
        "provision_data": {"distro": "noble"},
        "reserve_data": {"timeout": 120},
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        job_id = response.json().get("job_id")
        logger.info(f"[Activity] Submitted job for agent {agent_name}, job_id: {job_id}")
        return job_id
    else:
        logger.error(f"[Activity] Failed to submit job for {agent_name}: {response.status_code} {response.text}")
        raise Exception(f"Failed to submit job for {agent_name}: {response.status_code} {response.text}")

@activity.defn
async def monitor_job_activity(job_id: str, agent_name: str) -> str:
    import requests
    url = f"https://testflinger.canonical.com/v1/result/{job_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        state = data.get("job_state")
        logger.info(f"[Activity] Agent {agent_name}, job_id {job_id} state: {state}")
        if state == "complete" or state == "cancelled":
            return "complete"
        else:
            raise Exception(f"Job for agent {agent_name} not complete yet (state: {state})")
    else:
        logger.error(f"[Activity] Failed to get job status for {agent_name}: {response.status_code} {response.text}")
        raise Exception(f"Failed to get job status for {agent_name}: {response.status_code} {response.text}")

# --- Temporal Workflow ---
@workflow.defn
class AgentJobWorkflow:
    @workflow.run
    async def run(self, rack):
        workflow.logger.info(f"[Workflow] Starting AgentJobWorkflow with rack: {rack}")
        results = {}
        # Get machines and agents via activities
        machines_with_tag = await workflow.execute_activity(
            get_machines_activity,
            args=[rack],
            schedule_to_close_timeout=timedelta(seconds=60),
        )
        tor3_agents = await workflow.execute_activity(
            get_tor3_agents_activity,
            args=[],
            schedule_to_close_timeout=timedelta(seconds=60),
        )
        agents_in_rack = [agent for agent in tor3_agents if agent in machines_with_tag]
        tested_agents = []
        for agent in agents_in_rack:
            _, state, streak_count, streak_type = await workflow.execute_activity(
                get_agent_data_activity,
                args=[agent],
                schedule_to_close_timeout=timedelta(seconds=60),
            )
            workflow.logger.info(f"[Workflow] Agent: {agent}, State: {state}")
            if state != "waiting":
                workflow.logger.info(f"[Workflow] Skipping agent {agent} (state: {state})")
                results[agent] = "not_waiting"
                continue
            if streak_type == "fail":
                if streak_count > 20:
                    workflow.logger.info(f"[Workflow] Agent {agent} has failed {streak_count} times, taking no action.")
                    results[agent] = f"failed {streak_count} time already"
                    continue

            workflow.logger.info(f"[Workflow] Submitting job for agent: {agent}")
            try:
                job_id = await workflow.execute_activity(
                    submit_job_activity,
                    args=[agent],
                    schedule_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=30),
                        backoff_coefficient=1.0,
                    ),
                )
            except Exception as e:
                workflow.logger.info(f"[Workflow] Failed to submit job for agent {agent} after retries: {e}")
                results[agent] = "submit_failed"
                continue
            workflow.logger.info(f"[Workflow] Monitoring job {job_id} for agent: {agent}")
            try:
                job_result = await workflow.execute_activity(
                    monitor_job_activity,
                    args=[job_id, agent],
                    schedule_to_close_timeout=timedelta(minutes=60),
                    retry_policy=RetryPolicy(
                        maximum_attempts=15,
                        initial_interval=timedelta(seconds=300),
                        backoff_coefficient=1.0,
                    ),
                )
            except Exception as e:
                workflow.logger.info(f"[Workflow] Monitoring job for agent {agent} failed after retries: {e}")
                job_result = "monitor_failed"
            workflow.logger.info(f"[Workflow] Job for agent {agent} finished with result: {job_result}")
            results[agent] = job_result
            tested_agents.append(agent)
        workflow.logger.info(f"[Workflow] Agents intended to be tested: {agents_in_rack}")
        workflow.logger.info(f"[Workflow] Agents actually tested: {tested_agents}")
        workflow.logger.info(f"[Workflow] Six hours sleep before continue_as_new")
        await workflow.sleep(21600)
        workflow.logger.info("[Workflow] continue_as_new: restarting the workflow with the same parameters")
        raise workflow.continue_as_new(rack)

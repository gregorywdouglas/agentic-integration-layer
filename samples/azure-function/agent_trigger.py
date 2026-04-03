"""
Azure Function: Agent Event Trigger
====================================
Illustrative example — not production-ready.

This Function demonstrates an AIL-aligned event processing pattern.
It is triggered by an Azure Service Bus message published by an AI agent,
validates the request, enforces a basic authorization check, calls a
downstream system API via a governed endpoint, and emits a result event.

Runtime: Python 3.11
Trigger: Azure Service Bus (queue)
Output: Azure Event Grid (custom topic)

Required application settings:
  - DOWNSTREAM_API_URL: Base URL of the governed downstream API (via APIM)
  - DOWNSTREAM_API_KEY: Managed identity credential is preferred; this key
                         is shown for illustration only. In production, use
                         DefaultAzureCredential from azure-identity.
  - EVENT_GRID_TOPIC_ENDPOINT: Event Grid custom topic endpoint
  - ALLOWED_AGENT_IDS: Comma-separated list of authorized agent identifiers
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
import requests

app = func.FunctionApp()

DOWNSTREAM_API_URL = os.environ["DOWNSTREAM_API_URL"]
EVENT_GRID_TOPIC_ENDPOINT = os.environ["EVENT_GRID_TOPIC_ENDPOINT"]
ALLOWED_AGENT_IDS = set(os.environ.get("ALLOWED_AGENT_IDS", "").split(","))


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="agent-action-requests",
    connection="ServiceBusConnection",
)
def agent_trigger(msg: func.ServiceBusMessage) -> None:
    """
    Process an agent-initiated action request from Service Bus.

    Expected message format:
    {
        "agent_id": "inventory-monitor-agent-001",
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        "action": "create_purchase_order",
        "payload": {
            "sku": "PROD-8472",
            "quantity": 500,
            "supplier_id": "SUP-001"
        }
    }
    """
    correlation_id = "unknown"

    try:
        body = msg.get_body().decode("utf-8")
        request_data = json.loads(body)

        agent_id = request_data.get("agent_id", "")
        correlation_id = request_data.get("correlation_id", str(uuid.uuid4()))
        action = request_data.get("action", "")
        payload = request_data.get("payload", {})

        log = logging.getLogger(__name__)
        log.info(
            "Processing agent request",
            extra={
                "correlation_id": correlation_id,
                "agent_id": agent_id,
                "action": action,
            },
        )

        # Authorization check: verify the agent is in the allowed set.
        # In production, this check is enforced at the APIM layer via OAuth
        # scopes. This in-function check is a defense-in-depth measure only.
        if agent_id not in ALLOWED_AGENT_IDS:
            log.warning(
                "Unauthorized agent request rejected",
                extra={"agent_id": agent_id, "correlation_id": correlation_id},
            )
            # Do not raise — raising here would cause Service Bus to retry,
            # which is not appropriate for an authorization failure.
            _emit_result_event(
                correlation_id=correlation_id,
                agent_id=agent_id,
                action=action,
                status="rejected",
                reason="unauthorized_agent",
            )
            return

        # Dispatch to the appropriate handler based on action type.
        # In a production implementation, consider a registry-based dispatch
        # pattern rather than a conditional chain.
        if action == "create_purchase_order":
            result = _create_purchase_order(payload, correlation_id)
        else:
            log.warning(
                "Unknown action type",
                extra={"action": action, "correlation_id": correlation_id},
            )
            _emit_result_event(
                correlation_id=correlation_id,
                agent_id=agent_id,
                action=action,
                status="rejected",
                reason=f"unknown_action:{action}",
            )
            return

        _emit_result_event(
            correlation_id=correlation_id,
            agent_id=agent_id,
            action=action,
            status="completed",
            result=result,
        )

    except json.JSONDecodeError as exc:
        logging.error(
            "Invalid message format: %s | correlation_id=%s", exc, correlation_id
        )
        raise  # Re-raise to trigger Service Bus dead-lettering


def _create_purchase_order(payload: dict, correlation_id: str) -> dict:
    """
    Call the downstream purchase order API via the governed APIM endpoint.
    Returns the API response body as a dict.
    """
    url = f"{DOWNSTREAM_API_URL}/v1/purchase-orders"
    headers = {
        "Content-Type": "application/json",
        # In production, obtain a token via DefaultAzureCredential:
        #   from azure.identity import DefaultAzureCredential
        #   credential = DefaultAzureCredential()
        #   token = credential.get_token("https://management.azure.com/.default")
        #   headers["Authorization"] = f"Bearer {token.token}"
        "X-Correlation-Id": correlation_id,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _emit_result_event(
    correlation_id: str,
    agent_id: str,
    action: str,
    status: str,
    result: dict | None = None,
    reason: str | None = None,
) -> None:
    """
    Publish an action result event to Azure Event Grid.
    This event is consumed by the originating agent's event subscription
    so it can evaluate the outcome and continue or replan.
    """
    event = {
        "id": str(uuid.uuid4()),
        "source": "/ail/integration/agent-trigger-function",
        "specversion": "1.0",
        "type": "ail.agent.action.result",
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "correlation_id": correlation_id,
            "agent_id": agent_id,
            "action": action,
            "status": status,
            "result": result,
            "reason": reason,
        },
    }

    # In production, use azure-eventgrid SDK with DefaultAzureCredential.
    # Shown here as a direct HTTP call for clarity.
    response = requests.post(
        EVENT_GRID_TOPIC_ENDPOINT,
        json=[event],
        headers={"Content-Type": "application/cloudevents-batch+json"},
        timeout=10,
    )
    response.raise_for_status()

    logging.info(
        "Result event published",
        extra={"correlation_id": correlation_id, "status": status},
    )

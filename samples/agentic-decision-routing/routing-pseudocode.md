# Agentic Decision Routing — Pseudocode Reference

This document presents pseudocode illustrating how an AIL-aligned autonomous agent determines routing decisions at runtime. This is not executable code — it is an architectural reference for the reasoning and routing logic that an agent operating within AIL infrastructure would implement.

---

## Context

In a Level 5 AIL architecture, agents do not follow pre-defined workflow templates. They evaluate available capabilities, reason over current context, and select an execution path dynamically. The pseudocode below illustrates this decision loop for a representative scenario: an inventory monitoring agent that must decide how to respond to a low-stock condition.

---

## Agent Initialization

```
FUNCTION initialize_agent(goal_definition, agent_identity):

    # Authenticate to the Integration Layer
    credentials = acquire_managed_identity_token(
        scope = "api://ail-integration-layer/.default"
    )

    # Query the capability registry for available actions
    available_capabilities = query_capability_registry(
        credentials = credentials,
        domain = "inventory",
        permission_scope = agent_identity.permissions
    )
    # Returns: list of APICapability objects, each with:
    #   - capability_id
    #   - description
    #   - endpoint (via APIM)
    #   - required_parameters
    #   - estimated_latency
    #   - side_effects (e.g., "creates_purchase_order", "sends_notification")

    # Subscribe to relevant event streams
    event_subscriptions = subscribe_to_events(
        credentials = credentials,
        event_types = [
            "inventory.threshold.breached",
            "inventory.stockout.imminent",
            "supplier.api.unavailable"
        ],
        handler = handle_event
    )

    agent_state = {
        "goal": goal_definition,
        "capabilities": available_capabilities,
        "subscriptions": event_subscriptions,
        "active_executions": {},
        "execution_history": []
    }

    RETURN agent_state
```

---

## Event Handler and Routing Decision

```
FUNCTION handle_event(event, agent_state):

    correlation_id = generate_correlation_id()
    log_event_received(event, correlation_id)

    # Step 1: Enrich the event with additional context
    context = enrich_context(event, agent_state, correlation_id)

    # Step 2: Determine if this event warrants action
    action_required = evaluate_action_necessity(context, agent_state.goal)

    IF NOT action_required:
        log_no_action_taken(event, correlation_id, reason = "below_threshold")
        RETURN

    # Step 3: Reason over available capabilities to determine the response
    execution_plan = reason_and_plan(context, agent_state.capabilities)

    # Step 4: Validate the plan against governance policies
    validated_plan = validate_plan_against_policies(
        plan = execution_plan,
        policies = load_agent_policies(agent_state.goal.policy_set)
    )

    IF validated_plan.requires_human_approval:
        request_human_approval(validated_plan, correlation_id)
        log_awaiting_human_approval(correlation_id)
        RETURN  # Execution resumes via approval callback

    # Step 5: Execute the validated plan
    execute_plan(validated_plan, agent_state, correlation_id)
```

---

## Context Enrichment

```
FUNCTION enrich_context(event, agent_state, correlation_id):

    base_context = {
        "event": event,
        "timestamp": current_utc_timestamp(),
        "correlation_id": correlation_id
    }

    # Retrieve current inventory state for the affected SKU
    inventory_state = call_api(
        capability_id = "inventory.read",
        parameters = { "sku": event.data.sku },
        credentials = agent_state.credentials,
        correlation_id = correlation_id
    )

    # Retrieve preferred supplier information
    supplier_state = call_api(
        capability_id = "supplier.read",
        parameters = { "product_category": inventory_state.category },
        credentials = agent_state.credentials,
        correlation_id = correlation_id
    )

    # Retrieve applicable procurement policies
    policy_context = call_api(
        capability_id = "policy.read",
        parameters = { "domain": "procurement", "sku": event.data.sku },
        credentials = agent_state.credentials,
        correlation_id = correlation_id
    )

    RETURN MERGE(base_context, inventory_state, supplier_state, policy_context)
```

---

## Reasoning and Plan Construction

```
FUNCTION reason_and_plan(context, available_capabilities):

    # Construct a structured reasoning prompt from context
    reasoning_prompt = build_reasoning_prompt(
        template = load_prompt_template("inventory_response_v2"),
        context = context
    )

    # Submit to AI reasoning layer (e.g., Azure OpenAI GPT-4o)
    reasoning_response = call_ai_reasoning(
        prompt = reasoning_prompt,
        max_tokens = 1000,
        temperature = 0.1,  # Low temperature for deterministic reasoning
        response_format = "structured_json"
    )

    # Parse the AI response into a structured execution plan
    # The response indicates: which capability to invoke, with what parameters,
    # in what sequence, and what the expected outcomes are
    raw_plan = parse_ai_response(reasoning_response)

    # Validate that the AI-selected capabilities exist in the registry
    # (guard against hallucinated capability IDs)
    FOR each step IN raw_plan.steps:
        IF step.capability_id NOT IN available_capabilities:
            RAISE CapabilityNotFoundError(step.capability_id)

    RETURN raw_plan
```

---

## Policy Validation

```
FUNCTION validate_plan_against_policies(plan, policies):

    validation_result = {
        "approved_steps": [],
        "blocked_steps": [],
        "requires_human_approval": False,
        "approval_reason": None
    }

    FOR each step IN plan.steps:

        # Check if this action type is permitted for this agent
        IF step.action_type NOT IN policies.permitted_actions:
            validation_result.blocked_steps.APPEND(step)
            CONTINUE

        # Check if human approval is required based on business rules
        IF step.action_type == "create_purchase_order":
            IF step.parameters.quantity * step.parameters.unit_cost > policies.auto_approve_threshold:
                validation_result.requires_human_approval = True
                validation_result.approval_reason = (
                    f"Purchase order value exceeds auto-approve threshold "
                    f"of {policies.auto_approve_threshold}"
                )

        # Check rate limits (prevent runaway agent behavior)
        recent_actions = query_execution_history(
            action_type = step.action_type,
            time_window = "1 hour"
        )
        IF COUNT(recent_actions) >= policies.rate_limits[step.action_type]:
            validation_result.blocked_steps.APPEND(step)
            log_rate_limit_reached(step.action_type)
            CONTINUE

        validation_result.approved_steps.APPEND(step)

    RETURN validation_result
```

---

## Plan Execution

```
FUNCTION execute_plan(validated_plan, agent_state, correlation_id):

    execution_record = {
        "correlation_id": correlation_id,
        "plan": validated_plan,
        "started_at": current_utc_timestamp(),
        "steps_completed": [],
        "steps_failed": [],
        "final_status": None
    }

    FOR each step IN validated_plan.approved_steps:

        TRY:
            result = call_api(
                capability_id = step.capability_id,
                parameters = step.parameters,
                credentials = agent_state.credentials,
                correlation_id = correlation_id
            )

            execution_record.steps_completed.APPEND({
                "step": step,
                "result": result,
                "completed_at": current_utc_timestamp()
            })

            # Publish step completion event for observability
            publish_event(
                event_type = "ail.agent.step.completed",
                data = {
                    "correlation_id": correlation_id,
                    "step": step.capability_id,
                    "result_summary": result.summary
                }
            )

        CATCH ApiError AS error:

            execution_record.steps_failed.APPEND({
                "step": step,
                "error": error,
                "failed_at": current_utc_timestamp()
            })

            IF error.is_transient AND step.retry_count < step.max_retries:
                step.retry_count += 1
                WAIT exponential_backoff(step.retry_count)
                RETRY step  # Re-execute this step
            ELSE:
                # Determine recovery action: skip step, abort plan, or escalate
                recovery = determine_recovery_action(step, error, validated_plan)
                EXECUTE recovery

    execution_record.final_status = determine_final_status(execution_record)

    # Write immutable audit record
    write_audit_record(execution_record)

    # Publish overall execution result event
    publish_event(
        event_type = "ail.agent.execution.completed",
        data = execution_record
    )
```

---

## Notes on Implementation

1. **Prompt templates are version-controlled.** The `load_prompt_template` call retrieves a versioned template from a configuration store. Prompt changes are treated as configuration changes, not code changes, but they go through the same review and deployment process.

2. **AI reasoning is constrained.** The reasoning step determines *which* capability to invoke and *what parameters* to use. It does not have direct access to execute actions. All execution goes through the `call_api` function, which enforces policy validation regardless of what the AI reasoned.

3. **Capability IDs are validated against the registry.** The plan validation step (`validate_plan_against_policies`) rejects any capability ID that does not exist in the current registry. This prevents AI hallucinations from producing calls to non-existent or unauthorized APIs.

4. **All decisions produce audit records.** `write_audit_record` is called unconditionally — even for plans that were blocked or required human approval. The audit record captures the full context: the event that triggered reasoning, the enriched context, the AI response, the policy validation outcome, and the execution results.

5. **Rate limits are enforced in code, not just configuration.** The policy validation checks execution history to enforce rate limits at the application layer, complementing rate limits enforced at the APIM gateway layer.

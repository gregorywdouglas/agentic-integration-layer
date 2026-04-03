# Pattern: Composite API Orchestration

**Category:** API Integration  
**AIL Maturity Level:** 3–5  
**Applicable platforms:** Azure API Management, Azure Functions, any API gateway

---

## Summary

Composite API Orchestration is the practice of exposing a single, unified API endpoint to consuming agents while that endpoint internally coordinates calls to multiple downstream systems, aggregates the results, and returns a composed response. The agent interacts with one API surface; the complexity of multi-system data retrieval or action execution is encapsulated behind that surface.

---

## Problem Context

AI agents frequently require data from multiple enterprise systems to complete a reasoning step or initiate an action. Without composite orchestration, agents must:

1. Discover and call each system API individually
2. Manage the sequencing of dependent calls (System B requires data from System A)
3. Handle partial failures and inconsistent states across multiple calls
4. Aggregate and reconcile responses in their own reasoning layer

This approach couples agent logic to the structure of enterprise system APIs, increases agent complexity, and exposes agents to partial failure scenarios that are difficult to reason about. It also multiplies the governance surface — each individual system API must be secured, monitored, and managed as a distinct agent-facing endpoint.

---

## Solution Structure

A composite API endpoint encapsulates the multi-system interaction behind a single governed API contract:

```
┌────────────────────────────────────────────────────────────────┐
│                         AI AGENT                               │
│   "Get customer order context for customer ID 8472"            │
└──────────────────────────────┬─────────────────────────────────┘
                               │ Single API call
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                 COMPOSITE API ENDPOINT (APIM)                  │
│   POST /v1/context/customer-order                              │
│                                                                │
│   Internal orchestration (Azure Functions / Logic Apps):       │
│   ┌──────────────────────────────────────────────────────┐     │
│   │ 1. GET /crm/customers/{id}          → customer data  │     │
│   │ 2. GET /erp/orders?customerId={id}  → order list    │     │
│   │ 3. GET /inventory/items/{orderId}   → item status   │     │
│   │    (parallel calls for each order item)             │     │
│   │ 4. Aggregate → normalize → compose response         │     │
│   └──────────────────────────────────────────────────────┘     │
└──────────────────────────────┬─────────────────────────────────┘
                               │ Composed response
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                         AI AGENT                               │
│   Receives unified CustomerOrderContext object                 │
│   Proceeds with reasoning — no multi-system awareness needed   │
└────────────────────────────────────────────────────────────────┘
```

---

## AIL Alignment

| AIL Principle | How This Pattern Supports It |
|---|---|
| **API-first design** | The composite endpoint presents a clean, versioned contract to agents |
| **Dynamic orchestration** | Internal orchestration can vary based on request parameters without changing the agent-facing contract |
| **Governance** | A single API endpoint means a single point of policy enforcement, logging, and rate limiting |
| **Observability** | All downstream calls are correlated to the single inbound agent request |

---

## Implementation Notes

### Parallel vs. Sequential Calls

Where downstream calls are independent, execute them in parallel to minimize response latency. Where calls are dependent (the result of Call A is required as input to Call B), execute sequentially. Map this dependency graph during API design, not during agent runtime.

### Partial Failure Handling

Define a contract for how partial failures are communicated. Options:

- **Fail fast:** If any downstream call fails, return an error to the agent with details about which system failed
- **Partial response:** Return whatever data was successfully retrieved, with a `dataAvailability` field indicating which sections are complete or unavailable
- **Cached fallback:** Return a cached version of missing data segments, clearly marked as stale

The choice depends on whether the agent can reason meaningfully with partial data.

### Response Schema Design

Design the composite response schema around the agent's information needs, not around the internal structure of the contributing systems. The agent should receive a coherent, semantically meaningful object — not a stitched-together array of system-specific response formats.

### Caching

Composite responses that aggregate slowly-changing reference data should be cached at the API gateway layer. Define cache keys based on the request parameters that determine the response content. Cache invalidation should be triggered by events from the source systems, not by TTL expiry alone.

---

## Considerations and Trade-offs

| Consideration | Notes |
|---|---|
| **Latency** | The composite response is only as fast as the slowest downstream call. Parallel execution and timeouts are essential. |
| **Coupling** | The composite endpoint is coupled to its constituent APIs. Changes in downstream API contracts require updates to the composite implementation. |
| **Testability** | Each downstream call should be mockable independently for unit testing of the composite logic. |
| **Versioning** | When constituent APIs change, composite APIs may need to version in parallel. Plan versioning strategy upfront. |

---

*See also: [Event-Driven Decision Workflows](event-driven-decision-workflows.md) | [AI-Triggered Execution](ai-triggered-execution.md)*

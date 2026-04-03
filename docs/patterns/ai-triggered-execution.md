# Pattern: AI-Triggered Execution Flows

**Category:** Agentic Execution  
**AIL Maturity Level:** 5  
**Applicable platforms:** Azure OpenAI, Azure Container Apps, Azure API Management, Azure Functions, Azure Service Bus

---

## Summary

AI-Triggered Execution Flows describe the architecture in which an autonomous AI agent, operating within a governed execution environment, independently determines when and how to initiate multi-step enterprise actions. The agent is not responding to a single event or executing a fixed workflow — it is pursuing a goal through dynamic, context-driven interaction with enterprise systems via the Integration Layer.

This pattern represents the defining capability of AIL Level 5.

---

## Problem Context

Lower-maturity integration patterns are reactive: they respond to events or requests with pre-defined logic. At Level 5, the integration challenge inverts. The agent is the initiating entity. It:

- Monitors conditions across multiple systems simultaneously
- Determines independently when conditions warrant action
- Plans the sequence of actions required to achieve a goal
- Executes that plan across enterprise systems via governed APIs
- Evaluates outcomes and adjusts the plan in response

The integration infrastructure must support this agentic execution model without requiring pre-defined workflows or human-initiated triggers.

---

## Solution Structure

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          GOAL ASSIGNMENT                                  │
│   Human operator or orchestrating system assigns a goal to the agent:     │
│   "Monitor inventory levels for Product Group A. If any SKU falls below   │
│    reorder threshold, initiate purchase order workflow with preferred      │
│    supplier. Escalate if supplier API is unavailable."                    │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      AGENT EXECUTION LOOP                                 │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ PERCEIVE                                                            │  │
│  │ • Subscribe to inventory.threshold.breached events (Event Grid)     │  │
│  │ • Poll inventory API for SKUs not publishing events (via APIM)      │  │
│  └──────────────────────────────────┬──────────────────────────────────┘  │
│                                     │                                     │
│  ┌──────────────────────────────────▼──────────────────────────────────┐  │
│  │ REASON                                                              │  │
│  │ • Evaluate current inventory against reorder rules                  │  │
│  │ • Query capability registry for available supplier APIs             │  │
│  │ • Query preferred supplier availability and lead time               │  │
│  │ • Determine: initiate PO with supplier A, or escalate?              │  │
│  └──────────────────────────────────┬──────────────────────────────────┘  │
│                                     │                                     │
│  ┌──────────────────────────────────▼──────────────────────────────────┐  │
│  │ ACT                                                                 │  │
│  │ • POST /v1/purchase-orders via APIM → ERP system                   │  │
│  │ • POST /v1/supplier-orders via APIM → Supplier API                  │  │
│  │ • Publish order.initiated event to Event Grid                       │  │
│  │ • Write audit record: goal, reasoning, actions, outcomes            │  │
│  └──────────────────────────────────┬──────────────────────────────────┘  │
│                                     │                                     │
│  ┌──────────────────────────────────▼──────────────────────────────────┐  │
│  │ EVALUATE                                                            │  │
│  │ • Monitor for order.confirmed or order.failed events                │  │
│  │ • If failed: replan — try alternate supplier or escalate            │  │
│  │ • If confirmed: goal satisfied, return to monitoring state          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Requirements

For this pattern to function correctly, the following infrastructure must be in place:

### Capability Registry

The agent must be able to discover available APIs, event topics, and data services at runtime. A capability registry (implemented as an APIM product catalog, an OpenAPI specification catalog, or a purpose-built registry service) provides this discoverability.

The registry must be queryable by:
- Domain (e.g., "supplier management", "inventory")
- Capability type (read, write, event subscription)
- Required permissions (what the requesting agent is authorized to use)

### Agent Identity and Authorization

Each agent has a managed identity with a defined permission scope. The API gateway enforces these permissions on every request. An inventory monitoring agent may have:

- Read access to inventory and supplier APIs
- Write access to purchase order APIs
- No access to HR, financial reporting, or other unrelated domains

Permission scope is defined by the integration team, not by the agent itself.

### Execution State Store

Multi-step agent execution requires state persistence. If the agent is executing a five-step procurement workflow and the third step fails, the agent must be able to resume from the correct point rather than restarting. Azure Cosmos DB or Azure Table Storage can serve as the execution state store, with state keyed by goal ID and execution session.

### Human-in-the-Loop Checkpoints

Define the set of actions that require human approval before execution. For financial transactions, data deletion, or external communications, the agent workflow should pause and await human confirmation before proceeding. Logic Apps with approval workflows, or Azure Communication Services notifications, can implement these checkpoints.

---

## Agent Execution Flow (Detailed)

```
Agent receives goal
       │
       ▼
Query capability registry
→ Discover available APIs and event streams for this domain
       │
       ▼
Subscribe to relevant event topics (Event Grid)
       │
       ▼
┌──── MONITORING LOOP ──────────────────────────────────────────┐
│                                                               │
│  Event received  ──► Evaluate context ──► Threshold breached? │
│                                                │              │
│                                         No ◄──┤              │
│                                                │ Yes          │
│                                                ▼              │
│                                       Plan action sequence    │
│                                                │              │
│                                                ▼              │
│                                   Human approval required?    │
│                                                │              │
│                           Yes ──► Pause and notify ──► Await  │
│                                                │              │
│                           No ──────────────────┤              │
│                                                │              │
│                                                ▼              │
│                                   Execute action via APIM     │
│                                                │              │
│                                                ▼              │
│                                   Log: context, decision,     │
│                                   action, outcome             │
│                                                │              │
│                                                ▼              │
│                                   Evaluate outcome            │
│                                   → Success: return to loop   │
│                                   → Failure: replan or        │
│                                     escalate                  │
└───────────────────────────────────────────────────────────────┘
```

---

## AIL Alignment

| AIL Principle | How This Pattern Supports It |
|---|---|
| **Event-driven architecture** | Agent perception is event-driven; events initiate the reasoning cycle |
| **API-first design** | All agent actions are executed through governed APIs; no direct system access |
| **Dynamic orchestration** | Agent plans and replans based on runtime context and outcomes |
| **Real-time execution** | Event subscription enables sub-second response to threshold conditions |

---

## Governance and Safety Requirements

This pattern carries the highest governance responsibility of any AIL pattern:

- **Immutable audit log:** Every agent decision cycle must produce a tamper-evident audit record. This is not optional.
- **Action rate limits:** Configure maximum action rates per agent at the APIM layer. An agent should not be able to initiate more than N purchase orders per hour, regardless of how many threshold events it perceives.
- **Kill switch:** Provide an operational mechanism to suspend any agent's execution without requiring code changes or redeployment.
- **Scope boundaries:** Regularly review and validate that agent permission scopes are minimal. Agents should have access only to the capabilities they require for their assigned goals.
- **Anomaly detection:** Monitor agent behavior patterns. Unusual spikes in API calls, unexpected action sequences, or repeated escalations should trigger operational alerts.

---

## Considerations and Trade-offs

| Consideration | Notes |
|---|---|
| **Goal ambiguity** | Poorly defined goals produce unpredictable agent behavior. Goal definitions must be precise, testable, and reviewed by domain experts. |
| **Cascading actions** | Agent actions may trigger events that activate other agents. Map agent interaction dependencies to prevent unintended cascades. |
| **Replanning cost** | AI replanning (when an action fails) incurs additional inference cost and latency. Design failure handling to be deterministic where possible. |
| **State management complexity** | Long-running agent goals require robust state management. Define state schema carefully and plan for schema evolution. |

---

*See also: [Event-Driven Decision Workflows](event-driven-decision-workflows.md) | [Hybrid Cloud Integration](hybrid-cloud-integration.md)*

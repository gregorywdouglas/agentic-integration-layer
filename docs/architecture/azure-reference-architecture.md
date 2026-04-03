# Azure Reference Architecture for AIL

This document maps the Agentic Integration Layer architectural pattern to specific Azure services, describing how each component supports AIL principles and how they compose into a coherent enterprise integration platform for AI-driven workloads.

---

## Overview

Microsoft Azure provides a comprehensive set of managed integration services that can be composed to implement AIL. This reference architecture does not prescribe a single deployment topology — it describes the role each service plays in an AIL-aligned architecture and the configuration principles that govern their use.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      AZURE AIL REFERENCE ARCHITECTURE                           │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           AGENT LAYER                                    │  │
│  │  Azure OpenAI (GPT-4o) + Semantic Kernel / AutoGen / LangChain agents    │  │
│  │  Agents run in: Azure Container Apps | Azure Kubernetes Service          │  │
│  └────────────────────────────────┬──────────────────────────────────────┬──┘  │
│                                   │ API calls                            │ Events
│  ┌────────────────────────────────▼──────────────────────────────────────▼──┐  │
│  │                    INTEGRATION LAYER (AIL)                              │  │
│  │                                                                         │  │
│  │  ┌──────────────────────┐     ┌──────────────────────────────────────┐  │  │
│  │  │  Azure API Management│     │         Event Infrastructure         │  │  │
│  │  │  (API Gateway)       │     │  ┌─────────────┐  ┌───────────────┐  │  │  │
│  │  │                      │     │  │ Azure        │  │ Azure         │  │  │  │
│  │  │  • Auth & AuthZ      │     │  │ Service Bus  │  │ Event Grid    │  │  │  │
│  │  │  • Rate limiting     │     │  │              │  │               │  │  │  │
│  │  │  • Usage policies    │     │  │ (Commands,   │  │ (System       │  │  │  │
│  │  │  • API versioning    │     │  │  Workflows)  │  │  events,      │  │  │  │
│  │  │  • Developer portal  │     │  └─────────────┘  │  routing)     │  │  │  │
│  │  └──────────┬───────────┘     │                   └───────────────┘  │  │  │
│  │             │                 └──────────────────────────────────────┘  │  │
│  │             │                                   │                       │  │
│  │  ┌──────────▼───────────────────────────────────▼───────────────────┐  │  │
│  │  │                     Azure Functions                              │  │  │
│  │  │  (Stateless execution: transformation, routing, adapters)        │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │         Logic Apps (Standard) — Complex Workflow Orchestration  │   │  │
│  │  │         (Stateful, long-running, human-in-the-loop workflows)   │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │                     Observability                               │   │  │
│  │  │  Application Insights | Azure Monitor | Log Analytics           │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┬─────────────────┘  │
│                                                         │                     │
│  ┌──────────────────────────────────────────────────────▼─────────────────┐  │
│  │                          SYSTEM LAYER                                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │  │
│  │  │Dynamics  │  │SAP / ERP │  │Azure SQL /│  │On-prem  │  │External │  │  │
│  │  │365 / CRM │  │          │  │Cosmos DB  │  │Systems  │  │SaaS APIs│  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### Azure API Management (APIM)

**AIL role:** Governed API gateway — the mandatory boundary between agents and enterprise systems.

Azure API Management serves as the central enforcement point for all agent-initiated interactions with enterprise systems. In an AIL architecture, every API exposed to agents is published through APIM. Direct system access by agents is prohibited.

**Configuration principles for AIL:**

- **Products and subscriptions:** Each agent identity is assigned a subscription with specific product access. Agents can only call APIs included in their assigned product.
- **Policies:** Inbound policies validate agent-provided JWT tokens (issued by Azure Entra ID / Managed Identity). Rate limiting policies prevent runaway agent behavior from overwhelming downstream systems.
- **API versioning:** All APIs exposed to agents are versioned. Breaking changes require a new API version — existing agent contracts are not modified in place.
- **Developer portal:** Used by integration teams to document and register available capabilities. In AIL, this doubles as a human-readable representation of the capability registry.
- **Logging:** All requests and responses are logged to Application Insights with correlation IDs that trace through to downstream systems.

**Relevant APIM capabilities:**
- Built-in OAuth 2.0 / OpenID Connect validation
- Rate limiting, throttling, and quota policies
- Request/response transformation
- Backend load balancing and circuit breaker (with retry policies)
- Azure Monitor integration

---

### Azure Service Bus

**AIL role:** Asynchronous command and workflow message broker — decouples agents from system-side processing.

Azure Service Bus provides reliable, ordered, at-least-once message delivery for integration workloads. In AIL, Service Bus carries command messages and workflow coordination signals — messages that require guaranteed delivery and ordered processing.

**Usage patterns in AIL:**

- **Agent-initiated commands:** When an agent decides to initiate a multi-step system action (e.g., create an order, trigger a fulfillment workflow), it sends a command message to a Service Bus queue. The downstream processor dequeues and executes the command independently of the agent's execution loop.
- **Dead-letter queues:** Messages that fail processing are routed to dead-letter queues. Agents or operations teams can inspect and reprocess failed messages. Agents can subscribe to dead-letter notifications to adapt their execution plans.
- **Topic subscriptions:** Multiple agents or processing functions can subscribe to the same topic with independent subscription filters. This supports fan-out scenarios where a single agent action must trigger multiple downstream workflows.
- **Message sessions:** Session-aware queues support ordered processing for workflows that require sequenced execution (e.g., order-line processing where line items must be processed in order).

**Configuration principles:**
- Enable dead-letter queues on all queues and topic subscriptions
- Set appropriate message time-to-live values aligned with business SLAs
- Use managed identity for agent authentication to Service Bus — avoid shared access signatures where possible
- Enable duplicate detection for idempotent command processing

---

### Azure Event Grid

**AIL role:** Event routing infrastructure — distributes system state change events to subscribed agents.

Azure Event Grid provides low-latency, high-throughput event routing. In AIL, Event Grid carries system events — notifications that something has happened in the enterprise environment that agents may need to respond to.

**Usage patterns in AIL:**

- **System event distribution:** Azure services publish events natively to Event Grid (e.g., blob storage events, Cosmos DB change feed via custom topic, Azure Resource Manager events). These events surface system state changes for agent consumption.
- **Custom domain events:** Enterprise applications publish custom events to Event Grid custom topics (e.g., "OrderPlaced", "InventoryThresholdBreached", "CustomerStatusChanged"). Agents subscribe to relevant topics and receive notifications as events occur.
- **Event filtering:** Event Grid subscriptions support server-side filtering by event type and data properties, ensuring agents receive only the events relevant to their domain.
- **Push delivery:** Event Grid pushes events to subscribers (Azure Functions, webhooks, Service Bus) without polling. Agents are activated by events, not by schedules.

**Configuration principles:**
- Use custom topics for domain events; use system topics for Azure service events
- Define event schemas using CloudEvents 1.0 for interoperability
- Configure retry policies and dead-letter storage for failed event deliveries
- Use managed identity for authentication between Event Grid and subscriber endpoints

---

### Azure Functions

**AIL role:** Stateless execution units — transformation adapters, integration bridges, event processors.

Azure Functions provides serverless compute for the stateless execution work of AIL: payload transformation, protocol adaptation, lightweight routing logic, and system adapter implementations.

**Usage patterns in AIL:**

- **Event processors:** Functions triggered by Service Bus or Event Grid that transform, enrich, or route messages before they reach downstream systems or agents
- **System adapters:** Functions that translate between AIL's governed API contracts and the specific protocols or message formats required by legacy or third-party systems
- **Transformation pipelines:** Functions that perform schema mapping, data enrichment from reference data stores, or format conversion
- **Webhook receivers:** HTTP-triggered functions that receive webhooks from external systems and convert them to AIL-standard events published to Event Grid

**Configuration principles:**
- Functions should be stateless; state that must persist between invocations belongs in Durable Functions or an external state store
- Use managed identity for all outbound connections — avoid connection strings in configuration
- Configure Application Insights integration for distributed tracing
- Scale plan selection: Consumption Plan for unpredictable event-driven workloads; Premium Plan for latency-sensitive or VNet-integrated functions

---

### Logic Apps (Standard)

**AIL role:** Stateful, long-running workflow orchestration — human-in-the-loop workflows, complex conditional flows, and approval processes.

While AIL rejects static workflow templates for agent orchestration, Logic Apps (Standard) remains appropriate for specific categories of integration work that require statefulness, long-running execution, or human involvement.

**Appropriate AIL use cases for Logic Apps:**

- **Human-in-the-loop checkpoints:** Workflows where agent execution must pause for human review or approval before proceeding (e.g., large transaction authorization, compliance review)
- **Long-running business processes:** Workflows that span hours or days, where state must be persisted between steps (e.g., multi-day order fulfillment, onboarding workflows)
- **Complex conditional branching with auditable state:** Workflows where the decision tree is defined by business policy rather than agent reasoning, and where each decision must be auditable

**What Logic Apps should NOT do in AIL:**

- Logic Apps should not be used to hard-code the orchestration sequences for agentic workloads — this is the responsibility of the Agent Layer
- Logic Apps should not bypass the API gateway — all outbound system calls should route through APIM

---

### Application Insights and Azure Monitor

**AIL role:** Observability platform — distributed tracing, structured logging, metrics, and alerts.

AIL requires comprehensive observability. Application Insights and Azure Monitor provide the telemetry infrastructure.

**Key observability requirements for AIL:**

- **Distributed tracing:** Every agent-initiated request must carry a correlation ID that propagates through APIM, Service Bus, Functions, and into downstream systems. End-to-end traces must be queryable.
- **Structured logging:** All AIL components emit structured logs (JSON) that include: agent identity, correlation ID, operation type, target system, outcome, and latency.
- **Agent decision logging:** Agent reasoning steps and action selections must be logged at a sufficient level of detail to support after-the-fact audit review.
- **Alerting:** Alerts are configured for: agent error rate thresholds, APIM rate limit violations, Service Bus dead-letter queue depth, and Function execution failure rates.

---

## Security Model

All AIL components use **Azure Managed Identity** for service-to-service authentication. No secrets, connection strings, or API keys are stored in application configuration.

```
Agent (Container App)
  │
  │ Managed Identity token
  ▼
Azure API Management
  │ Validates token via Azure Entra ID
  │ Applies authorization policies
  ▼
Azure Functions / Service Bus / Downstream Systems
  │ Managed Identity (APIM's identity or Function's identity)
  ▼
Target System
```

**Key Vault** stores any secrets that cannot be eliminated (e.g., third-party API keys for external systems). All services reference Key Vault via managed identity — no direct secret access.

---

## Deployment Considerations

- **All AIL components should be deployed in a single Azure region** where latency and data residency requirements allow. Multi-region deployment introduces complexity that should only be accepted when availability or compliance requirements mandate it.
- **Virtual Network integration** should be applied to all compute components (Functions Premium Plan, Container Apps, APIM Developer/Premium tier) for environments with network isolation requirements.
- **Infrastructure as Code:** All AIL infrastructure should be defined using Bicep or Terraform. Manual portal configuration is not acceptable for production environments.

---

*See also: [Architecture Overview](overview.md) | [Traditional vs. AIL](traditional-vs-ail.md)*

# Pattern: Hybrid Cloud Integration

**Category:** Infrastructure  
**AIL Maturity Level:** 3–5  
**Applicable platforms:** Azure API Management, Azure Arc, Azure Service Bus, Azure Functions, Azure VPN Gateway / ExpressRoute

---

## Summary

Hybrid Cloud Integration describes the architectural approach for enabling AIL in organizations where enterprise systems are distributed across on-premises data centers, private clouds, and public cloud environments. Rather than requiring full cloud migration as a prerequisite for AIL adoption, this pattern extends AIL's governed, event-driven integration fabric to include on-premises systems as equal participants.

---

## Problem Context

Most enterprise organizations operate in hybrid environments. Core business systems — ERP, mainframes, proprietary databases, regulated data stores — remain on-premises due to cost, compliance, performance, or organizational constraints. At the same time, AI capabilities, event infrastructure, and API management platforms are cloud-native.

Without a deliberate hybrid integration architecture, organizations face two problematic choices:

1. **Exclude on-premises systems from AIL**, limiting agent capabilities to cloud-native systems only
2. **Expose on-premises systems directly to cloud agents**, bypassing governance and creating security risk

The Hybrid Cloud Integration pattern provides a third path: extend AIL governance to on-premises systems through a consistent, secure integration fabric.

---

## Solution Structure

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          AZURE (PUBLIC CLOUD)                             │
│                                                                           │
│  ┌────────────┐   ┌──────────────┐   ┌─────────────┐   ┌─────────────┐   │
│  │ AI Agents  │   │    APIM      │   │ Service Bus │   │  Functions  │   │
│  │(Container  │──►│ (API Gateway)│──►│ (Messaging) │──►│(Processing) │   │
│  │    Apps)   │   │              │   │             │   │             │   │
│  └────────────┘   └──────┬───────┘   └─────────────┘   └─────────────┘   │
│                          │                                                │
└──────────────────────────┼────────────────────────────────────────────────┘
                           │ ExpressRoute / VPN Gateway
                           │ (Private, encrypted connectivity)
┌──────────────────────────┼────────────────────────────────────────────────┐
│                          │   ON-PREMISES                                  │
│                          ▼                                                │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │                    ON-PREMISES INTEGRATION HUB                    │    │
│  │                                                                   │    │
│  │  ┌──────────────────┐    ┌──────────────────┐                     │    │
│  │  │  Self-Hosted     │    │  Hybrid Worker   │                     │    │
│  │  │  Gateway (APIM)  │    │  (Functions)     │                     │    │
│  │  │                  │    │                  │                     │    │
│  │  │  Exposes on-prem │    │  Executes tasks  │                     │    │
│  │  │  APIs through    │    │  requiring       │                     │    │
│  │  │  APIM governance │    │  on-prem access  │                     │    │
│  │  └────────┬─────────┘    └────────┬─────────┘                     │    │
│  │           │                       │                               │    │
│  └───────────┼───────────────────────┼───────────────────────────────┘    │
│              │                       │                                     │
│  ┌───────────▼───────────────────────▼───────────────────────────────┐    │
│  │              ON-PREMISES SYSTEMS                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │   SAP    │  │Mainframe │  │Oracle DB │  │ Legacy ERP/CRM   │   │    │
│  │  │   ECC    │  │(COBOL)   │  │          │  │                  │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### APIM Self-Hosted Gateway

Azure API Management's Self-Hosted Gateway is a containerized APIM gateway component deployed on-premises or in private environments. It extends APIM's API governance — authentication, authorization, rate limiting, policy enforcement — to APIs running in environments without public internet connectivity.

**In AIL hybrid architecture:**
- Deploy the Self-Hosted Gateway in the on-premises network
- Register on-premises system APIs through the gateway
- Cloud-based agents call the on-premises API through APIM, with the call routing transparently to the Self-Hosted Gateway
- All governance policies defined in the cloud APIM instance apply to the Self-Hosted Gateway

**Configuration requirements:**
- The Self-Hosted Gateway requires outbound connectivity to APIM in Azure for policy synchronization
- Inbound traffic from cloud agents routes through ExpressRoute or VPN, not public internet
- TLS termination occurs at the Self-Hosted Gateway; on-premises connections may use internal certificates

### Azure Functions Hybrid Worker

For integration workloads that require code execution in the on-premises environment (e.g., reading from a mainframe dataset, querying a legacy database with a proprietary driver), Azure Functions supports deployment to Azure Arc-enabled infrastructure.

**In AIL hybrid architecture:**
- Functions that require on-premises data access are deployed to Arc-enabled on-premises servers
- These Functions appear in the Azure Functions management plane alongside cloud-hosted Functions
- Event triggers (Service Bus, Event Grid) work identically whether the Function runs in cloud or on-premises

### Change Data Capture for Legacy Systems

Legacy systems that cannot publish events natively require a change data capture (CDC) mechanism to participate in AIL's event-driven architecture. Options:

- **Database CDC tools** (Debezium, SQL Server CDC): Capture row-level changes and publish them as events to Service Bus or Event Grid
- **Adapter Functions**: Poll legacy system APIs or databases on a short interval and publish change events when differences are detected
- **Message bridge**: Connect existing on-premises messaging systems (IBM MQ, MSMQ) to Azure Service Bus via bridge adapters

---

## Network Architecture

### Connectivity Options

| Option | Use case | Trade-offs |
|---|---|---|
| **Azure ExpressRoute** | Production hybrid integration with low-latency and throughput requirements | Higher cost; requires carrier provisioning |
| **Azure VPN Gateway** | Lower-volume hybrid integration or development/test environments | Higher latency than ExpressRoute; traffic traverses internet (encrypted) |
| **Azure Private Link** | Private connectivity to specific Azure PaaS services (Service Bus, APIM) without full VPN | Service-specific; does not provide general network connectivity |

### DNS Resolution

Hybrid architectures require consistent DNS resolution across cloud and on-premises environments. Azure Private DNS Zones with conditional forwarding between Azure DNS and on-premises DNS resolvers ensure that cloud resources are resolvable on-premises and vice versa.

---

## Event Flow in Hybrid Architecture

```
On-premises system state changes
          │
          ▼
    CDC adapter captures change
          │
          ▼
    Change event published to
    Azure Service Bus (via
    ExpressRoute / VPN)
          │
          ▼
    Event Grid routes to
    subscribed agents
          │
          ▼
    Agent reasons and decides
    to act on on-premises system
          │
          ▼
    Agent calls APIM endpoint
          │
          ▼
    APIM routes to Self-Hosted
    Gateway (on-premises)
    via ExpressRoute / VPN
          │
          ▼
    Self-Hosted Gateway enforces
    policy and forwards to
    on-premises system API
          │
          ▼
    Action executed on-premises
    with full governance and audit
```

---

## Security Considerations

- **No direct agent access to on-premises systems.** All agent interactions with on-premises resources route through APIM (Self-Hosted Gateway) with full policy enforcement.
- **Private connectivity only.** Cloud-to-on-premises traffic does not traverse public internet. Use ExpressRoute or VPN for all integration traffic.
- **Credential isolation.** On-premises system credentials (service accounts, database connection strings) are stored in on-premises secrets management or Azure Key Vault accessed via Private Link. They are never embedded in cloud-side integration configuration.
- **Audit continuity.** Distributed tracing correlation IDs must propagate across the network boundary so that end-to-end audit traces include both cloud and on-premises execution segments.

---

## AIL Alignment

| AIL Principle | How This Pattern Supports It |
|---|---|
| **API-first design** | On-premises systems are governed through the same APIM contract model as cloud systems |
| **Event-driven architecture** | CDC and bridge adapters bring on-premises state changes into the AIL event fabric |
| **Dynamic orchestration** | Agents are unaware of whether a system is on-premises or cloud — they interact through the same API contracts |
| **Real-time execution** | Low-latency ExpressRoute connectivity enables near-real-time on-premises integration |

---

## Considerations and Trade-offs

| Consideration | Notes |
|---|---|
| **Latency** | On-premises calls add network round-trip latency compared to cloud-native calls. Factor this into agent timeout and SLA design. |
| **Connectivity dependency** | Hybrid integration creates a dependency on the ExpressRoute/VPN circuit. Plan for circuit redundancy and define agent behavior during connectivity loss. |
| **Operational complexity** | Self-Hosted Gateways and Arc-enabled Functions require on-premises infrastructure management. Factor operational overhead into architecture decisions. |
| **CDC complexity** | Change data capture for some legacy systems (mainframes, proprietary databases) may require specialized tooling or custom development. Assess per-system before committing to event-driven on-premises integration. |

---

*See also: [AI-Triggered Execution Flows](ai-triggered-execution.md) | [Azure Reference Architecture](../architecture/azure-reference-architecture.md)*

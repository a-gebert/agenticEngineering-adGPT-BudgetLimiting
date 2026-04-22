---
name: Chat Session Audit Architecture Doc
description: Authoritative architecture overview for the Chat Session Audit system — data flows, container layout, entity model, error resilience, and comparison with Configuration Audit
type: reference
originSessionId: 9cc4b6ed-fdd3-490b-80aa-51564f170700
---
The comprehensive Chat Session Audit architecture document is maintained at:

```
/home/gebert/adgpt/agenticEngineering-adGPT-auditLog/configs/Backend/docs/chat-session-audit-architecture.md
```

**Contents:** System overview (mermaid), write-path sequence diagram, error resilience flowchart, CosmosDB container architecture ("audit" container with UserId PK), entity model (ChatSessionAuditEntry, ChatAuditData, ChatSessionAuditOptions), layer responsibilities, side-by-side comparison of Configuration Audit (interceptor) vs Chat Session Audit (MediatR command), and full file inventory.

**How to apply:** Read this document when working on any Chat Session Audit task, when needing to understand the two audit patterns, or when modifying container/collection naming.

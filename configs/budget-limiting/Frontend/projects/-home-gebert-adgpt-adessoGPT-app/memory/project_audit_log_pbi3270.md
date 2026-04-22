---
name: PBI3270 Audit Log — Project Context
description: Feature branch context, two audit types, compliance requirements, and overall system scope
type: project
---

**Branch:** `feature/PBI3270_Audit_Log`
**Scope:** Extend adessoGPT with a full audit log system — two distinct audit types.

**Why:** Compliance requirements AC-1 through AC-3 mandate tamper-resistant, append-only audit trails for both admin configuration changes and user LLM interactions.

**How to apply:** All frontend audit work targets the Control Center admin area. Two separate views/stores may be needed (one per audit type). Understand the backend API shape before building frontend.

---

## Two Audit Types

| Aspect | Configuration Audit | Chat Session Audit |
|--------|--------------------|--------------------|
| **Trigger** | Admin changes a system setting | User sends a chat message (LLM call) |
| **Volume** | Low (admin operations) | High (every LLM call) |
| **Backend pattern** | EF Core `SaveChangesInterceptor` | Explicit MediatR Command |
| **Who sees it** | ControlCenterAdmin only | ControlCenterAdmin only |
| **API** | `GET /api/control-center/audit` | TBD (not yet implemented) |

---

## Compliance Requirements

### AC-1: Required Fields per Audit Entry (Chat Session)
- User-ID, Timestamp (UTC), Used Model, Model Parameters (Temp, MaxTokens etc.), Session/Request-ID

### AC-2: Immutability
- `sealed record` with `init`-only properties on backend
- No update/delete endpoints
- HMAC-SHA256 integrity hash stored on entry (tamper resistance already implemented)

### AC-3: Optional Content Storage
- `ChatSessionAuditOptions` with `StorePromptContent` and `StoreResponseContent` (both default: `false`)
- Admin can activate via settings — affects whether prompt/response text is stored

---

## Backend API Endpoints (Configuration Audit — already implemented)

```
GET /api/control-center/audit
  Query params: entityType?, entityId?, userName?, fromDate?, toDate?, pageNumber, pageSize
  Response: GetConfigurationAuditResponse (paginated)
  Role: ControlCenterAdmin

GET /api/control-center/audit/entity-types
  Response: GetAuditEntityTypesResponse (catalog of auditable types, grouped by category)
  Role: ControlCenterAdmin
```

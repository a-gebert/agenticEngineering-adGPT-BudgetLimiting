---
name: Configuration Audit — Backend Architecture
description: EF Core interceptor-based audit for admin system setting changes — API shape, DTOs, and entity model for frontend integration
type: project
---

**Pattern:** EF Core `SaveChangesInterceptor` — audit entries created in the same transaction as the entity change.

**Why:** Configuration changes are low-volume, synchronous, and need property-level diffs (old vs new values).

**How to apply:** Frontend gets a paginated list of audit entries with property-change detail. Build filter UI around the available query params.

---

## API Shape

```
GET /api/control-center/audit
  pageNumber (int, >= 1)
  pageSize   (int, 1..100)
  entityType (string?, optional)
  entityId   (string?, optional)
  userName   (string?, optional)
  fromDate   (DateTimeOffset?, optional)
  toDate     (DateTimeOffset?, optional)
  Role: ControlCenterAdmin

GET /api/control-center/audit/entity-types
  Returns: grouped catalog of auditable entity types
  Role: ControlCenterAdmin
```

## Response DTOs

```typescript
// ConfigurationAuditEntryDto
{
  id: string
  timestamp: string          // ISO 8601 UTC
  userId: string
  userName: string
  entityType: string         // e.g. "Agent", "ModelOptions", "Theme"
  entityId: string
  operationType: 'Create' | 'Update' | 'Delete'
  changes: AuditPropertyChangeDto[]
  integrityHash: string      // HMAC-SHA256 tamper evidence
}

// AuditPropertyChangeDto
{
  propertyPath: string       // e.g. "SystemMessage.Content"
  displayTitle: string       // localized display name
  oldValue: string | null    // JSON-serialized value
  newValue: string | null
}

// GetConfigurationAuditResponse
{
  entries: ConfigurationAuditEntryDto[]
  totalCount: number
  pageNumber: number
  pageSize: number
}

// GetAuditEntityTypesResponse
{
  categories: AuditedEntityTypeCategoryDto[]
}

// AuditedEntityTypeCategoryDto
{
  categoryName: string
  entityTypes: AuditedEntityTypeInfoDto[]
}

// AuditedEntityTypeInfoDto
{
  typeName: string           // matches entityType filter param
  displayName: string
}
```

## 27 Auditable Entity Types
Agents, ModelOptions, Themes, and other ISystemSetting entities — grouped by category in the entity-types endpoint.

## Key Design Facts
- Values stored as JSON strings (serialized). May need frontend JSON parsing for display.
- `operationType`: Create, Update, Delete
- `integrityHash` is HMAC-SHA256 over the entry content — display as tamper-proof indicator
- String-based `entityType` (not enum) — use the entity-types endpoint to build filter dropdowns

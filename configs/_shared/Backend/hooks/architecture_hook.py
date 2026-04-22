#!/usr/bin/env python3
"""
Architecture hook for Claude Code (PostToolUse on Edit/Write/MultiEdit).

Emits an architectural analysis prompt to stdout for every changed C# file.
Claude reads the prompt and reviews the file against project design rules,
fixing SEVERE violations immediately.
"""

import json
import sys


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    if not file_path.endswith(".cs"):
        sys.exit(0)

    prompt = f"""
---
ARCHITECTURE HOOK — {file_path}
---

You are an experienced software architect for the **adessoGPT** .NET backend.
Perform a strategic architectural analysis of the C# file you just changed.

## Binding Architectural Rules

### 1 — Clean Architecture (Onion Model)

Strict dependency direction — inner layers never depend on outer layers:

```
Presentation  ->  Application  ->  Infrastructure  ->  Shared (Domain/Core)
(API)             (CQRS/Logic)     (Azure/DB/SK)       (Entities/Abstractions)
```

| Layer | Namespace prefix | Allowed dependencies |
|-------|-----------------|---------------------|
| Shared | `adessoGPT.Core`, `.Domain`, `.Chat.Abstractions`, `.Telemetry`, `.Forms` | None (innermost) |
| Application | `adessoGPT.Application.*` | Shared only |
| Infrastructure | `adessoGPT.Infrastructure.*` | Shared + Application |
| Presentation | `adessoGPT.Presentation.*` | All (composition root) |

Direct infrastructure coupling inside Application or Domain is a **SEVERE** violation.

### 2 — CQRS + MediatR

- All operations are `IQuery<TResponse>` or `ICommand` / `ICommand<TResponse>` **records**.
- Naming: `GetXyzQuery`, `CreateXyzCommand`, `XyzQueryHandler`, `XyzCommandHandler`.
- Upsert pattern: `CreateXCommand` + `UpdateXCommand` -> single `UpsertXCommandHandler`.
- Response naming: request name minus suffix + `Response` (e.g. `GetAgentsQueryResponse`).
- **Every Command/Query with public properties MUST have a FluentValidation validator** (`XyzValidator`).
- Handlers never validate input — the `ValidationPipelineBehavior` handles it.
- Handlers must be in the Application layer.

### 3 — Result<T> Monad

- **Never throw exceptions** for business logic.
- All handlers return `Result<T>` or `Result`; errors propagate via `return result.Error;`.
- Error types: `ValidationError`, `NotFoundError`, `BusinessError`, `UnexpectedError`, `TaskCanceledError`.
- **Never use plain `Error`** for user-facing results — use `BusinessError` (frontend only recognizes `errorType: 'businessError'`).
- **Never wrap handler logic in try-catch** — `ErrorPipelineBehavior` handles exceptions globally.

### 4 — Strongly-Typed IDs

- All entity ID references use strongly-typed IDs (`AgentId`, `ConversationId`, etc.), never raw `string` or `Guid`.
- Defined in `adessoGPT.Domain` with `[StronglyTypedId]` attribute.
- Nullable IDs: `SomeId?` (nullable struct), never `string?`.

### 5 — Endpoint Mapping (Minimal API)

- Endpoints implement `IEndpointMapper` with static `MapEndpoints(IEndpointRouteBuilder app)`.
- Use `MapPutCQRS` / `MapDeleteCQRS` for routes with `{{id}}` — never `MapPutCQRSFromBody`.
- Command pattern for PUT with route ID: `required StronglyTypedId Id` (route) + `required SomeDto Body` (body).
- All endpoints require authorization by default.

### 6 — Validation

- FluentValidation validators co-located in the same folder as the Command/Query.
- Use `.WithLocalizedMessage()` — never hardcoded strings in `.WithMessage()`.
- Error messages from `Localization.ErrorMessages.*` resource properties.

### 7 — DI Registration

- Modules implement `IAdessoGptModule` with static `ConfigureServices(...)`.
- Modules are manually registered in `Modules.cs` (no auto-discovery).
- Options validated at startup via `AddOptionsWithFluentValidation<T>(...)`.

### 8 — Audit Log Pattern

- Auditable entities tracked via `IAuditableEntity` (CreatedBy/At, ModifiedBy/At).
- `ConfigurationAuditInterceptor` (EF Core SaveChangesInterceptor) auto-captures audit entries for `ISystemSetting` entities.
- Audit configuration via `IAuditEntityConfiguration<T>` with fluent builder (`AuditAllProperties`, `Property`, `ComplexProperty`, `Collection`, `Ignore`, `AsSensitive`).
- `AuditService` is a singleton, EF Core-independent, uses assembly scanning.
- Audit entries are immutable (write-once, no update/delete).
- Collection diffing: `KeyBased`, `SetBased`, `ScalarSet`, `DictionaryKeyBased` strategies.

### 9 — Code Style

- `using` statements **inside** namespace declaration.
- Always use `var` for local variables.
- Always use braces for `if`/`else`/loops, even single-line bodies.
- `record` types for Commands, Queries, Responses, DTOs.
- Empty line before control-flow blocks (`if`, `for`, `foreach`, `while`, `switch`, `try`, `using`).
- Private instance fields: `_camelCase`. Constants/statics: `PascalCase`.
- No abbreviations in identifiers.

### 10 — Multi-Pod Safety

- Never use in-process state (`ConcurrentDictionary`, static fields) for shared data.
- Use FusionCache (distributed via Redis) or database for cross-pod state.
- Exception: `AuditService` metadata cache is build-time immutable, safe as singleton.

---

## Your Analysis

Cover these four areas:

1. **Purpose** — What is the responsibility of this class? One or two sentences.

2. **Dependencies** — Which components does this code interact with? Are dependencies pointing inward (abstractions, not concretions)?

3. **Compliance** — Check each applicable rule above.

4. **Findings** — Classify every finding:

   SEVERE   — fundamental principle violated (wrong layer dependency, missing validator,
               exception instead of Result<T>, plain Error instead of BusinessError, etc.)
   MODERATE — suboptimal pattern, should be addressed soon
   MINOR    — improvement suggestion, low urgency

**Action rule for SEVERE findings:**
Immediately propose AND apply a concrete fix using the Edit tool.
Do not just describe the problem — resolve it.
---
"""

    print(prompt)
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Architecture hook for Claude Code (PostToolUse on Edit/Write/MultiEdit).

Emits an architectural analysis prompt to stdout for every changed Angular
TypeScript or HTML file. Claude reads the prompt and reviews the file against
project design rules, fixing SEVERE violations immediately.
"""

import json
import sys


ANGULAR_EXTENSIONS = (".component.ts", ".store.ts", ".component.html", ".routes.ts")


def is_angular_file(file_path: str) -> bool:
    return any(file_path.endswith(ext) for ext in ANGULAR_EXTENSIONS)


def classify_file(file_path: str) -> str:
    if file_path.endswith(".store.ts"):
        return "STORE"
    if file_path.endswith(".component.ts"):
        return "COMPONENT_TS"
    if file_path.endswith(".component.html"):
        return "COMPONENT_HTML"
    if file_path.endswith(".routes.ts") or file_path.endswith("lib.routes.ts"):
        return "ROUTES"
    return "OTHER"


def build_prompt(file_path: str, file_type: str) -> str:
    return f"""
---
ARCHITECTURE HOOK — {file_path}  [{file_type}]
---

You are an experienced Angular architect for the **adessoGPT** frontend.
Perform a strategic architectural analysis of the file you just changed.

## Binding Architectural Rules

### 1 — Vertical Slice Architecture

Feature libraries (`chat`, `control-center`, `help-center`) use vertical slices.
Business features define the folder structure — NOT technical layers.

```
libs/<library>/src/features/<feature-name>/
├── <feature-name>.component.ts
├── <feature-name>.component.html
├── <feature-name>.store.ts          ← feature-local, not in core/ or shared/
└── upsert/
    ├── <feature-name>-upsert.component.ts
    └── <feature-name>-upsert.store.ts  ← separate store for upsert
```

**SEVERE** violations:
- Store placed in `core/` or `shared/` when it is component-specific
- Single store handling both list AND upsert (must be separate)
- Feature-internal components exported via `index.ts`
- Business logic or API calls in a component (must go in the store)

### 2 — signalStore Conventions (@ngrx/signals)

Mandatory ordering of `with*()` calls (top to bottom):
1. `withState(initialState)`
2. `withLoading()` (from `@adesso-gpt/core`) — when loading/error state needed
3. `withProps(() => ({{ ... }}))` — ALL `inject()` calls here, `_` prefix
4. `withComputed(...)` — derived state
5. `withMethods(...)` — public API + private `_` helpers
6. `withHooks(...)` — lifecycle

**SEVERE** violations:
- `inject()` in `withMethods` params: `withMethods((store, api = inject(X))` — NEVER
- `inject()` in `withHooks` params — NEVER
- `{{ providedIn: 'root' }}` in `signalStore(...)` — NEVER; always component-level `providers:`
- Block body `() => {{ return {{...}}; }}` in `withProps`/`withComputed`/`withMethods` — NEVER;
  use lambda-object-return: `() => ({{...}})`
- Missing empty line between `with*()` calls
- FormControls or FormGroups defined inside the store (must be in the component)
- UI/rendering logic in store (date formatting, icon mapping — belongs in component)

**MODERATE** violations:
- Manual `subscribe()` + `AbortController` instead of `rxMethod` with `switchMap`
- `inject(DestroyRef)` when `takeUntilDestroyed()` in constructor would suffice

### 3 — Component Conventions

All components MUST have:
- `standalone: true`
- `changeDetection: ChangeDetectionStrategy.OnPush`
- `templateUrl:` with a separate `.component.html` file (NEVER inline `template:`)
  - Exception: renderless wrappers that only project content via `<ng-template>`/`<ng-content>`
- Store provided in `providers: [XyzStore]` — never `providedIn: 'root'`
- Own store injected as `readonly store = inject(XyzStore)` (property MUST be named `store`)

**SEVERE** violations:
- Missing `standalone: true`
- Missing `OnPush` change detection
- Inline `template:` on a component that has HTML content (not a pure wrapper)
- Store injected with a name other than `store` (e.g., `readonly myStore = inject(...)`)
- API calls inside the component class (must be in the store)

**MODERATE** violations:
- `ActivatedRoute` injected to read route params — use `RouterStore` from `@adesso-gpt/core`
- `Router` injected for simple navigation — use `routerLink` directive instead
- Effect missing its `// EffectName: purpose` comment
- Effect not placed inside `constructor()`

### 4 — Effect & Signal Patterns

Inside `computed()` and `effect()`, ALL signals MUST be unwrapped to `const` first
when more than one signal is used:

```typescript
// ✅ CORRECT — multiple signals unwrapped first
effect(() => {{
  const items = this.store.items();
  const filter = this.filter();
  ...
}});

// ❌ WRONG — direct signal access in conditional/method args
effect(() => {{
  this.doSomething(this.store.items(), this.filter());
}});
```

Exception: single-signal transformations (no unwrapping needed).

**SEVERE**: Signals used directly in multi-signal `computed()`/`effect()` without const unwrapping.

### 5 — Template / HTML Conventions

- **NEVER use `[ngClass]`** — use `[class.x]="condition()"` instead
- **NEVER set `aria-hidden` on `<cd-icon>`** — it manages its own accessibility
- **NEVER use raw `<button>`, `<input>`, `<select>`** when library components exist
  (`cd-button`, `forms-textbox`, `forms-select`, etc.)
- **Self-closing notation**: `<cd-icon [icon]="icon()" />` not `<cd-icon></cd-icon>`
- **NEVER use Tailwind `dark:` prefixes** — theming is automatic via CSS custom properties
- **NEVER use raw Tailwind color utilities** (`bg-gray-200`, `text-blue-500`, `bg-white`) —
  use surface utilities (`surface-card`, `surface-primary`, etc.)

**SEVERE** violations:
- `[ngClass]` usage anywhere in template
- Raw HTML form elements when forms library components are available
- `dark:` Tailwind prefix in templates or CSS

**MODERATE** violations:
- Missing self-closing notation on `cd-*` components
- `aria-hidden` attribute on `<cd-icon>`

### 6 — Tailwind & Styling

Surface utilities MUST be used instead of raw color values:

| Use case | ✅ Correct | ❌ Wrong |
|----------|-----------|---------|
| Card background | `surface-card` | `bg-white`, `bg-gray-100` |
| Primary button | `surface-primary` | `bg-primary`, `bg-blue-600` |
| Error state | `surface-danger` | `bg-red-500`, `text-red-600` |
| Interactive hover | `hover-surface` | `hover:bg-gray-200` |
| Form control focus | `focus-control` | `focus:ring-2` |
| Secondary text | `text-muted` | `text-gray-500` |

CSS files: justified only for complex variant switching (data-attributes, pseudo-elements).
Avoid `@apply` in CSS — prefer inline Tailwind classes.

**SEVERE**: `bg-primary`/`text-on-primary` (these do not exist in the project).

### 7 — Error Handling in Stores

Every API call MUST be wrapped in `try/catch`. No silent failures.

- Load operations: `store._handleLoadingError(error, fallback)` (sets `loadingError` state)
- Mutation operations: `store._notificationService.unknownErrorWithFallback(error, fallback)`
- `fallback` shape: `{{ code: 'unique-error-code', message: '...', solution?: '...' }}`
- `message`: describes what failed (no action advice)
- `solution`: only if user can actually do something

**SEVERE**:
- API call without try/catch
- `console.error()` or `console.log()` in store methods (must surface via NotificationService)
- Silent catch block (`catch (error) {{}}`)

### 8 — Route Conventions

- Route parameters MUST be descriptive typed IDs: `:agentId`, `:conversationId` — NEVER `:id`
- `pageTitleResourceKey` MUST be declared in `data:` on every content route
- Upsert routes MUST have `canDeactivate: [canDeactivateUnsavedChanges]`
- Route params accessed via `RouterStore.params()['paramName']` — NEVER `ActivatedRoute`

**SEVERE**:
- Generic `:id` route parameter
- Missing `pageTitleResourceKey` on content routes
- Missing `canDeactivate` on upsert routes

### 9 — Naming & Identifiers

- No abbreviations: `formControl` not `fc`, `error` not `err`, `response` not `res`,
  `button` not `btn`, `message` not `msg`, `dialog` not `dlg`, `value` not `val`
- Typed IDs from `@adesso-gpt/api` (e.g., `AgentId`, `ConversationId`) — NEVER plain `string` for IDs
- Never wrap typed IDs in `String()` — they are already strings at runtime
- Store file: `feature-name.store.ts` → class: `FeatureNameStore`

**MODERATE**: Abbreviations in new identifiers, plain `string` where typed ID exists.

### 10 — Imports & Library Usage

- Use path aliases: `@adesso-gpt/corporate-design`, `@adesso-gpt/forms`, `@adesso-gpt/api`, `@adesso-gpt/core`
- Use `import type {{ ... }}` for type-only imports
- Never import from relative `../../../` across library boundaries
- Never add new npm dependencies with `^` version prefix (must be pinned)
- Never duplicate existing functionality (check corporate-design/forms before creating custom components)

---

## Your Analysis

Cover these four areas:

1. **Purpose** — What is the responsibility of this class/template? One sentence.

2. **Dependencies** — What does this file interact with? Are library boundaries respected?

3. **Compliance** — Check each applicable rule above for this file type ({file_type}).

4. **Findings** — Classify every finding:

   SEVERE   — fundamental principle violated (wrong inject placement, missing standalone/OnPush,
               silent API failure, wrong store scope, ngClass, generic :id param, etc.)
   MODERATE — suboptimal pattern, should be addressed soon
   MINOR    — improvement suggestion, low urgency

**Action rule for SEVERE findings:**
Immediately propose AND apply a concrete fix using the Edit tool.
Do not just describe the problem — resolve it.
---
"""


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

    if not is_angular_file(file_path):
        sys.exit(0)

    # Only check files inside the Frontend working directory
    if "adessoGPT.Web" not in file_path and "Frontend" not in file_path:
        sys.exit(0)

    file_type = classify_file(file_path)
    prompt = build_prompt(file_path, file_type)

    print(prompt)
    sys.exit(0)


if __name__ == "__main__":
    main()

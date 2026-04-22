---
name: Angular App Architecture
description: Library structure, key services, reusable components, and architectural patterns of the adessoGPT.Web Angular app
type: project
---

**App:** `Frontend/adessoGPT.Web/` — Angular 21, Nx 22, NgRx Signals, Tailwind CSS v4

**Why:** Understanding this avoids reinventing existing components/services and ensures correct library boundaries.

**How to apply:** Before building any UI, check which libraries provide what. Use path aliases everywhere.

---

## 9 Libraries at a Glance

| Library | Alias | Purpose |
|---------|-------|---------|
| `libs/api` | `@adesso-gpt/api` | Generated OpenAPI client, typed IDs, SSE utilities |
| `libs/corporate-design` | `@adesso-gpt/corporate-design` | 40+ UI components (`cd-*`), LayoutStore, NotificationService, ConfirmService |
| `libs/forms` | `@adesso-gpt/forms` | 14 form controls (`forms-*`), FormsFormComponent, canDeactivateUnsavedChanges |
| `libs/core` | `@adesso-gpt/core` | RouterStore, UserStore, AgentStore, LanguageStore, FeatureFlagStore, withLoading, ErrorParser |
| `libs/cross-cutting-concerns` | `@adesso-gpt/cross-cutting-concerns` | Entra ID auth, selection-page |
| `libs/control-center` | — | Admin/settings feature (lazy-loaded) |
| `libs/chat` | — | Chat feature (lazy-loaded) |
| `libs/help-center` | — | Help/docs feature (lazy-loaded) |
| `libs/prompt-library` | — | Prompt library feature (lazy-loaded) |

---

## Corporate Design — Key Components (`@adesso-gpt/corporate-design`, selector prefix `cd-*`)

### Layout & Navigation
- `cd-shell-metadata [shellTitleResourceKey]` — sets shell title; MUST be in every feature shell template
- `cd-content-page [loading] [loadingError] [container]` — page wrapper with loading state
- `cd-navigation-content` — wrapper for nav items, stacked by route depth
- `cd-navigation-item [routerLink] [ariaLabel] [icon] [text] [indent]` — nav link
- `cd-navigation-item-group [label] [groupId]` — nav group with label
- `cd-navigate-back [backRoute]` — back button; use at top of upsert pages
- `cd-page-title-only-header` — simple header rendering shell title as `<h1>`

### Interactions
- `cd-button [variant] [size] [ariaLabel] [disabled] [tooltip] (clickCallback)` — variants: `primary|secondary|tertiary|success|warning|danger|transparent|rail|card`
- `cd-icon [icon] [size] [badge] [tooltip]` — NEVER set `aria-hidden` externally
- `cd-icon-button` — icon-only variant of cd-button
- `cd-dialog [title] [actionButtons] [(open)] [confirmCallback] [cancelCallback]` — modal dialog
- `cd-menu [items]` — context menu
- `cd-alert [type] [message] [solution]` — types: `info|success|warning|error`
- `cd-business-error-alert` — for business errors from API

### Display
- `cd-card`, `cd-card-button`, `cd-card-content`, `cd-card-title` — card composition
- `cd-tabs`, `cd-tab-item [label] [icon]` — tab navigation
- `cd-chip`, `cd-chip-list-row` — badges/pills
- `cd-markdown-renderer` — renders Markdown with syntax highlighting
- `cd-spinner` — loading indicator
- `cd-breadcrumb`, `cd-breadcrumb-item` — breadcrumb
- `cd-separator` — divider
- `cd-filter-bar` — filter UI

### Services
- `NotificationService`: `.unknownErrorWithFallback(error, { code, message, solution? })`, `.info()`, `.success()`, `.warning()`, `.error()`
- `ConfirmService`: `.confirm(title, text, variant?) → Promise<boolean>`

### LayoutStore (`@adesso-gpt/corporate-design`)
- `shellTitle()`, `pageTitle()` — current page title signals
- `setPageTitleOverride(title)` — dynamic titles
- `isMobile()`, `isTablet()`, `isDesktop()` — responsive breakpoints
- `sidebarOpen`, `toggleSidebar()` — sidebar state
- `currentTheme()`, `setTheme()` — theme management

---

## Forms Library — Controls (`@adesso-gpt/forms`, selector prefix `forms-*`)

All controls extend `FormControlBase`: `[label]`, `[ariaLabel]`, `[hint]`, `[readonly]`, `[size]`, `[formControl]`

| Selector | Key extra inputs |
|----------|-----------------|
| `forms-textbox` | `[type]` (text\|number\|password\|email), `[leftIcon]`, `[rightIcon]` |
| `forms-textarea` | `[rows]`, `[placeholder]` |
| `forms-select` | `[options]` (SelectOption[]) |
| `forms-select-multi` | `[options]` |
| `forms-autocomplete` | `[options]`, `[query]` (signal) |
| `forms-checkbox` | — |
| `forms-checkbox-list` | `[options]` |
| `forms-toggle` | — |
| `forms-radio-group` | `[options]`, `[legend]` |
| `forms-date-picker` | — |
| `forms-range-slider` | `[min]`, `[max]`, `[step]` → `RangeValue {from, to}` |
| `forms-color-picker` | — |
| `forms-icon-selector` | `[options]` |
| `forms-file-upload` | `[maxSize]`, `[accept]`, `[multiple]` |
| `forms-literal-display` | Display-only (read-only) |
| `forms-localized-textbox` | Multi-language input; init FormControl with `{}` |
| `forms-localized-textarea` | Multi-language textarea; init FormControl with `{}` |

**Form wrappers:**
- `forms-form [formGroup] [saveCallback] [cancelRouterLink] [saveSuccessRouterLink]` — MANDATORY on all upsert pages; handles save/cancel routing
- `canDeactivateUnsavedChanges` guard — MANDATORY on all upsert routes

---

## Core Library — Stores & Services (`@adesso-gpt/core`)

### RouterStore
- `params()`, `queryParams()`, `url()`, `data()`, `navigationState()`
- `navigate(commands, extras?)`, `navigateRelativeByCurrent(commands)`
- **Always use instead of `ActivatedRoute`** for reading route params

### withLoading() — signalStore feature
- Adds signals: `loading()`, `loadingError()`
- Adds methods: `_setLoading(boolean)`, `_handleLoadingError(error, fallback)`
- `fallback`: `{ code: string, message: string, solution?: string }`
- Use `_handleLoadingError` for load operations, `unknownErrorWithFallback` for mutations

### Other Stores
- `UserStore`: `user()`, `roles()`, `permissions()`
- `AgentStore`: `agents()`, `selectedAgent()`
- `LanguageStore`: `currentLanguage()`, `isRtl`, `isLtr`
- `FeatureFlagStore`: `flags()`, `hasFlag(name)`

---

## API Library — Typed IDs (`@adesso-gpt/api`)

Key typed IDs (all are `type XyzId = string` brands):
`AgentId`, `AgentCategoryId`, `ConversationId`, `ChatMessageId`, `ModelOptionsId`,
`ConfigurationAuditEntryId`, `SharedConversationId`, `CommunityPromptId`, `AppAlertId`, `ApplicationFeatureId`

**Rules:**
- Always use typed IDs instead of `string` for entity references
- Never wrap in `String()` — already strings at runtime
- Use directly in comparisons, Maps, API path/query params

---

## Control Center — Routing Pattern

Routes in `libs/control-center/src/lib.routes.ts`:
- Shell wraps all features: `ControlCenterShellComponent`
- Feature route structure: `{ path: 'feature', children: [ { path: '', component: ListComponent }, { path: 'create', component: UpsertComponent, canDeactivate: [...] }, { path: ':featureItemId', component: UpsertComponent, canDeactivate: [...] } ] }`
- Every content route MUST have `data: { pageTitleResourceKey: 'scope.key' }`
- Route params MUST be descriptive: `:agentId`, `:modelOptionsId` — NEVER `:id`

---

## Reference Implementations (Gold Standard)

| Pattern | Location |
|---------|----------|
| Simple upsert | `libs/control-center/src/features/custom-instructions/upsert/` |
| Complex upsert (tabbed) | `libs/control-center/src/features/agents/upsert/` |
| List with delete | `libs/control-center/src/features/agents/` |

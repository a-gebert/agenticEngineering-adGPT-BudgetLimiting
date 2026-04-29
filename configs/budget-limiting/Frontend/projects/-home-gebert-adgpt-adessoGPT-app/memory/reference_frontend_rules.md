---
name: Frontend Implementation Rules
description: 9 rule files in Frontend/adessoGPT.Web/.claude/rules/ — mandatory conventions for Angular components, signals, stores, styling, library APIs, and rule-sync workflow
type: reference
originSessionId: 877f247a-099c-4e66-95fb-147c4be7234b
---
The responsible developers have defined comprehensive implementation rules in `Frontend/adessoGPT.Web/.claude/rules/`. These auto-load via `paths:` frontmatter when working on `libs/**` or `apps/adessoGPT/src/**`.

## Rule files and their scope

| File | Key rules |
|------|-----------|
| `angular-architecture.md` | Standalone+OnPush, signals, separate HTML templates, store injection as `store`, no `providedIn: 'root'`, RouterStore only, Route.title as Transloco key, error message/solution pattern, WCAG 2.1 AA |
| `angular-gotchas.md` | ngMenuItem needs `[value]`, Transloco scope in project.json, signalStore DI error, effect loops, forms-select disabled via FormControl, color tokens without suffix, Tailwind v4 suffix `gap-2!`, API enums lowercase |
| `angular-signals-ngrx.md` | Unwrap signals to const in computed/effect, effects in constructor with comment, store ordering withState→withProps→withComputed→withMethods→withHooks, lambda-object-return mandatory, all deps in withProps with `_` prefix, API errors via try/catch + NotificationService |
| `angular-styling.md` | Tailwind v4 mandatory, HTML-first, surface-utilities first, no default Tailwind colors, hover-surface/active-surface/focus-surface, z-index system, no `dark:` prefixes |
| `library-core.md` | RouterStore, PageTitle pipeline, UserStore, LanguageStore, AgentStore, FeatureFlagStore, ErrorParser, withLoading, InitializerRegistry |
| `library-corporate-design.md` | Full input tables for all cd-* components, ConfirmService, NotificationService, LayoutStore, SidebarStore |
| `library-forms.md` | Reactive Forms mandatory, ControlMap<TDto>, no ReactiveFormsModule import, forms-form UnsavedChangesGuard |
| `library-cross-cutting-concerns.md` | AuthenticationService (not AuthStore), authGuard + requiresUserRole, init order, SelectionPage |
| `library-rules-sync.md` | Every library public API change must update the matching rule file in the same commit |

**How to apply:** Always consult and follow these rules during planning and implementation. When modifying library public APIs, update the corresponding rule file in the same PR.

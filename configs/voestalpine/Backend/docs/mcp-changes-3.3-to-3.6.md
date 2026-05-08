# MCP-Server-Änderungen Backend: 3.3 → 3.6

**Erstellt:** 2026-05-04
**Repo:** `adessoGPT-app`
**Vergleichsbasis:** `origin/customer/voestalpine/3.3` (Tip `796ef5de7`) → `customer/voestalpine/3.6` (Tip `d136289a6`)
**Diff-Scope:** `Backend/` — 127 commits insgesamt, davon Auszug der MCP-relevanten unten.

> **Hinweis:** In `voestalpine/3.3` lag das Backend noch unter `app/Backend/`. Der Repo-Layout-Wechsel (Wegfall des `app/`-Prefix) erfolgte zwischen 3.3 und 3.6. Pfade in diesem Dokument verwenden die heutige Struktur.

---

## 1. Elicitation-Support — Status: bereits seit 3.3 implementiert

**Wichtig:** Elicitation ist **kein** Neufeature von 3.6. Die komplette Handler-Architektur lag bereits in `voestalpine/3.3`:

```
Backend/Application/adessoGPT.Application.MCP/Business/Elicitation/
  Dependencies/
    IElicitationHandler.cs
    DefaultElicitationHandler.cs
    ChatElicitationEvents.cs
  HandleElicitation/
    HandleElicitationResponseCommand.cs
    HandleElicitationResponseCommandHandler.cs
    HandleElicitationResponseCommandValidator.cs
  ElicitationEndpoints.cs
Backend/Shared/adessoGPT.Domain/PersistedEntities/SystemSettings/McpServer/ElicitationOptions.cs
```

Verifiziert via `git ls-tree -r origin/customer/voestalpine/3.3` — alle obigen Pfade existieren dort bereits.

### Was sich an Elicitation in 3.3→3.6 geändert hat

Drei Files, 14 Insertions / 6 Deletions — kleine Anpassungen:

| Commit | Datei | Änderung |
|---|---|---|
| `1bdc01066` (PR 1410) | `IElicitationHandler.cs`, `DefaultElicitationHandler.cs` | Parameter-Reorder von `HandleAsync` — `ChatStreamContext` als erster Parameter, `ElicitRequestParams?`/`CancellationToken` danach |
| `71954eb25` (PR 1646) | `DefaultElicitationHandler.cs` | Timeout-Fehlermeldung lokalisiert (`LocalizedString.For(ErrorMessages.ElicitationTimeout_Message)` statt Hardcoded-Englisch) |
| `d63eb4429` (PR 1661) | `ChatElicitationEvents.cs` | SDK-Adaption: `EnumSchema` → `UntitledSingleSelectEnumSchema`, neuer Branch für `TitledSingleSelectEnumSchema` (mit `OneOf`-basierten Const-Werten) |

### Architektur-Mechanik (Stand 3.6, unverändert seit 3.3)

- **Interface:** `IElicitationHandler` (DI: scoped, registriert in `McpApplicationModule.cs`)
- **Endpoint:** `POST /api/elicitations/response` (`ElicitationEndpoints.cs`)
- **Datenfluss:** MCP-Server → `ElicitRequestParams` → `DefaultElicitationHandler.HandleAsync` → `ChatElicitationResponse` an Frontend via `ChatStreamContext` → Frontend antwortet → `HandleElicitationResponseCommand` → MemoryCache-Key `elicitation:{id}` → `TaskCompletionSource` resolved → `ElicitResult` zurück an MCP-Server
- **Timeout:** 5 Minuten, danach lokalisierter `BusinessError`
- **Schema-Mapping:** Boolean / String / Enum (mit/ohne `Title`) → `ElicitationFieldDefinition`

---

## 2. Andere MCP-Änderungen 3.3 → 3.6 (thematisch gruppiert)

> Quelle: `git log --oneline origin/customer/voestalpine/3.3..HEAD -- Backend/Application/adessoGPT.Application.MCP Backend/Infrastructure/adessoGPT.Infrastructure.Mcp Backend/Application/adessoGPT.Application.ConfigurationManager/Business/McpServers Backend/Infrastructure/adessoGPT.Infrastructure.ConfigurationDbImport/McpServers Backend/Tests/Application/adessoGPT.Application.MCP.Tests`

### Connection & Transport

| Commit | PR | Inhalt |
|---|---|---|
| `0fb317542` | 1570 | HTTP-Transport-Rewrite mit Resilience (Retry, Timeout); `HttpClientTransport` mit `HttpTransportMode.AutoDetect`; semaphore-basierte Thread-Safety |
| `7a0d48c2c` | 1525 | Bugfix: `Avoid semaphore release after disposal` (Concurrency-Issue) |
| `0d10179c7` | 1564 | Filter & Warnung für zu lange MCP-Tool-Namen |

### Auth & Callback-Headers

| Commit | PR | Inhalt |
|---|---|---|
| `c5d8be8bf` | 1706 | `EnableCallback`-Flag; Injection von `X-Callback-BaseUrl` / `X-Callback-Scope`; External-OAuth2-Support für Per-User-Credentials; `RequiredScope` im McpServer-Model |
| `bae11ab27` | — | Per-User-MCP-Credentials via Basic Auth (`BasicAuthConfig`) |
| `073660fee` | — | Per-User-Credentials auf External-OAuth2-Infrastruktur umgestellt; Application/OnBehalfOf-Scope-Modi |

### Progress Reporting

| Commit | PR | Inhalt |
|---|---|---|
| `d63eb4429` | 1661 | MCP Progress Reporting (Issue #2855): `IProgressToChatStreamReporterFactory`, `ChatProgressResponse`-Events ans Frontend, lokalisierte Progress-Meldungen (Step / Percentage mit/ohne Message) |

### Persistence & Domain Model

| Commit | PR | Inhalt |
|---|---|---|
| `1b3522785` | 1514 | Bool-Flag `PersistToolCallResult` ersetzt durch Enum `ToolCallPersistenceMode` (`Arguments`, `Results`, `None`); `ChatStreamPersistingWrapper` angepasst |
| `28be8573d` | 1476 | `PluginName` für Features eingeführt; Normalisierung (max. 12 Zeichen, `[a-z0-9_]`) |
| `a2b79783f` | 1675 | Icon-Typ `string?` → `Icon?` (strukturierter Domain-Type) |

### Access Control

| Commit | PR | Inhalt |
|---|---|---|
| `5036dc9f6` | 1590 | `AllowedUserGroupIds` an McpServer-Entity; User-Group-basierte Zugriffskontrolle für Datasources & Features |

### Generated Files

| Commit | PR | Inhalt |
|---|---|---|
| `38ce8a2a4` | 1729 | Rework Generated-File-Handling; `RemainingFilesToUploadCallback`; verbesserte Concurrency |

---

## 3. Feature-Inventar (Stand 3.6)

### Transports

| Transport | Unterstützt | Detail |
|---|---|---|
| HTTP / SSE | ✅ | `HttpClientTransport` mit `HttpTransportMode.AutoDetect` |
| Stdio | ❌ | nicht implementiert |

### Authentifizierung

| Methode | Detail |
|---|---|
| API Key | `ApiKeyAuthConfig` (Header-Name + Value aus Secrets) |
| Basic Auth | `BasicAuthConfig` (Username/Password, base64) |
| OAuth 2.0 | `OAuthV2Config`; Scope-basiert, Application- + OnBehalfOf-Modi, External-OAuth-Integration |
| mTLS | ❌ |

### Callbacks (Server → Backend)

| Callback | Status |
|---|---|
| Elicitation | ✅ (`DefaultElicitationHandler`, TaskCompletionSource-Polling, 5-min Timeout) |
| Progress | ✅ (`IProgress<ProgressNotificationValue>`, Frontend via `ChatProgressResponse`) |
| Logging | ✅ (`ILogger<McpServerConnection>`) |
| Generated Files | ✅ (`RemainingFilesToUploadCallback`) |
| Roots | ❌ |
| Notifications | ❌ |
| Sampling | ❌ |

### Header-Injection

- **Auth:** `Authorization: Bearer/Basic`, sowie konfigurierbare Custom-Header
- **Callback:** `X-Callback-ConversationId`, `X-Callback-ReferenceUserMessageId` (`McpCallbackHeaderHandler`)
- **Scope-Routing (bei `EnableCallback=true`):** `X-Callback-BaseUrl`, `X-Callback-Scope`

### Konfiguration & Persistenz

- **Quellen:** `appsettings.json`, Control-Center-UI (CQRS), `McpServersImporter` (YAML/JSON-Bootstrap)
- **DB:** McpServer-Entity in CosmosDB / MongoDB / InMemory
- **Validation:** FluentValidation (`ElicitationOptionsValidator`, `McpServerEndpointOptionsValidator`)

### Tool-Management

- **Discovery:** `McpServerConnectionFactory.GetFunctionsAsync()`
- **Filter:** Tool-Namen-Längen-Validierung, FunctionGroup-Prefix
- **Persistence-Mode:** `None` / `Arguments` / `Results` (im `ChatStreamPersistingWrapper`)
- **Invocation:** `McpFunctionInvocationFilter` (Context-Passing, RequiredScope-Enforcement)

---

## 4. NuGet-Paket-Versionen

Quelle: `Directory.Packages.props` (Central Package Management). Stand 2026-05-04.

### Aktueller Stand über alle relevanten Branches

| Branch | `ModelContextProtocol` | Tip-Datum | SDK-Release |
|---|---|---|---|
| `release/3.3` | `0.4.0-preview.3` (unpinned) | 2026-02-05 | 2025-10-20 |
| `customer/voestalpine/3.3` | `0.4.0-preview.3` (unpinned) | 2026-02-11 | 2025-10-20 |
| `customer/ZOKA/release/3.3` | `0.4.0-preview.3` (unpinned) | 2026-01-05 | 2025-10-20 |
| `customer/voestalpine/3.6` (unser Branch) | `[0.7.0-preview.1]` (pinned) | 2026-04 | 2026-01-28 |
| `release/3.6.2` | `[1.1.0]` (pinned) | 2026-04-22 | 2026-03-06 |
| `dev` | `[1.2.0]` (pinned) | 2026-04-29 | 2026-03-27 |

### Bump-Historie auf `release/3.6.2`

| PR | Commit | Bump |
|---|---|---|
| 1768 — *Update ModelContextProtocol to version 1.0.0* | `4040db3e3` | `0.9.0-preview.1` → `1.0.0` (Sprung über die Stable-Schwelle) |
| 1845 — *Refactor MCP elicitation: dynamic forms, validation, tests* | `8e69ead83` | `1.0.0` → `1.1.0` (Elicitation-Refactor mit dynamischen Formularen + Tests) |

PR 1845 ist nicht nur ein NuGet-Bump — der Titel verspricht einen größeren Elicitation-Umbau (dynamische Formulare, Validierung, Tests). Wer auf 3.6.2 ist, hat also nicht nur die SDK-Version, sondern auch ein neueres Elicitation-Design.

### Lücken-Übersicht (bzgl. Latest auf nuget.org = `1.2.0`)

| Branch | Hinter Latest | SDK-Alter |
|---|---|---|
| 3.3 | 11 Releases | ~6,5 Monate |
| voestalpine/3.6 | 8 Releases | ~3 Monate |
| release/3.6.2 | 1 Release (`1.2.0`) | ~2 Monate |
| dev | 0 (aktuell) | ~5 Wochen |

### SDK-Auswirkungen 0.4 → 0.7 (für unseren Branch relevant)

- Elicitation-Schema-Klassen umbenannt: `EnumSchema` → `UntitledSingleSelectEnumSchema`, plus neuer Typ `TitledSingleSelectEnumSchema` (siehe Abschnitt 1)
- `HttpTransportMode.AutoDetect` für SSE/HTTP-Streaming verfügbar
- Progress-Notifications via `ProgressNotificationValue`

### Risiko: ungepinnte 3.3-Version

3.3 nutzt `Version="0.4.0-preview.3"` ohne eckige Klammern. Bei einem `dotnet restore` ohne Lock-File könnte ein Floating-Resolve theoretisch eine inkompatible Preview ziehen. Im konkreten Fall ist das risikoarm (nach `0.4.0-preview.3` kam nur noch `0.4.1-preview.1` im 0.4er-Range), aber bei 3.6/3.6.2/dev ist das Pinning konsequent durchgezogen.

---

## 5. Breaking Changes & Migrations-Notizen (3.3 → 3.6)

| Change | Auswirkung |
|---|---|
| `HandleAsync(ElicitRequestParams, CancellationToken, ChatStreamContext)` → `HandleAsync(ChatStreamContext, ElicitRequestParams, CancellationToken)` | Signatur-Reorder am `IElicitationHandler` — eigene Implementierungen müssen Parameter-Reihenfolge anpassen |
| `EnumSchema` → `UntitledSingleSelectEnumSchema` (+ `TitledSingleSelectEnumSchema`) | Code, der gegen `ChatElicitationEvents.cs` o. ä. patternmatcht, muss SDK-Update mitziehen |
| `PersistToolCallResult: bool` → `PersistenceMode: ToolCallPersistenceMode` | Konfigurations-Schema-Bruch (Bool → Enum); Bestandskonfigurationen müssen migriert werden |
| `Icon: string?` → `Icon?` (strukturiert) | Control-Center-UI / API-Konsumenten brauchen Anpassung |
| `CreateMcpServerCommand` entfernt | Funktional aufgegangen in `UpsertMcpServerCommand` |
| `AllowedUserGroupIds: List<UserGroupMappingId>` neu | Optional, Default leer = kein Filter |
| `EnableCallback: bool` neu | Default `false` — Callback-Header werden nur bei aktivem Flag injiziert |
| `RequiredScope` neu am McpServer-Model | OAuth-Scope-Voraussetzung pro Server konfigurierbar |
| `PluginName`-Normalisierung (max. 12 chars, `[a-z0-9_]`) | Bestehende Plugin-Namen werden ggf. abgelehnt |
| `ModelContextProtocol` auf `[0.7.0-preview.1]` gepinnt | Update kann nicht implizit über NuGet-Restore erfolgen |

---

## Methodischer Hinweis

Das Dokument basiert auf:

1. Diff-Range: `git diff origin/customer/voestalpine/3.3..HEAD -- Backend/<MCP-Pfade>` (für Inventar der geänderten Files)
2. Commit-Inspektion via `git log --oneline` und PR-Titel
3. Verifikation der Elicitation-Existenz via `git ls-tree -r origin/customer/voestalpine/3.3`
4. NuGet-Versionen aus `Directory.Packages.props` der jeweiligen Branch-Tips

Nicht im Scope dieses Dokuments: Frontend-Änderungen (React `adessoGPT.UI/` und Angular `Frontend/adessoGPT.Web/`) — wurden bewusst ausgespart.

---

## Anhang A: Vollständige Release-Historie `ModelContextProtocol`

Quelle: NuGet Registration API (`https://api.nuget.org/v3/registration5-gz-semver2/modelcontextprotocol/index.json`), abgefragt am 2026-05-04.

| Datum | Version | Marker |
|---|---|---|
| (unlisted) | `0.1.0-preview.1.25171.12` | unlisted/zurückgezogen |
| 2025-03-27 | `0.1.0-preview.2` | |
| 2025-03-31 | `0.1.0-preview.3` | |
| 2025-03-31 | `0.1.0-preview.4` | |
| 2025-04-03 | `0.1.0-preview.5` | |
| 2025-04-04 | `0.1.0-preview.6` | |
| 2025-04-09 | `0.1.0-preview.7` | |
| 2025-04-11 | `0.1.0-preview.8` | |
| 2025-04-15 | `0.1.0-preview.9` | |
| 2025-04-19 | `0.1.0-preview.10` | |
| 2025-04-24 | `0.1.0-preview.11` | |
| 2025-05-05 | `0.1.0-preview.12` | |
| 2025-05-10 | `0.1.0-preview.13` | |
| 2025-05-15 | `0.1.0-preview.14` | |
| 2025-05-16 | `0.2.0-preview.1` | |
| 2025-05-29 | `0.2.0-preview.2` | |
| 2025-06-03 | `0.2.0-preview.3` | |
| 2025-06-20 | `0.3.0-preview.1` | |
| 2025-07-03 | `0.3.0-preview.2` | |
| 2025-07-16 | `0.3.0-preview.3` | |
| 2025-08-20 | `0.3.0-preview.4` | |
| (unlisted) | `0.3.0-preview.5` | unlisted/zurückgezogen |
| 2025-09-25 | `0.4.0-preview.1` | |
| 2025-10-08 | `0.4.0-preview.2` | |
| **2025-10-20** | **`0.4.0-preview.3`** | ← **3.3** (release/3.3, voest/3.3, ZOKA/3.3) |
| 2025-11-25 | `0.4.1-preview.1` | |
| 2025-12-05 | `0.5.0-preview.1` | |
| 2026-01-14 | `0.6.0-preview.1` | |
| **2026-01-28** | **`0.7.0-preview.1`** | ← **voestalpine/3.6** (dieser Branch) |
| 2026-02-05 | `0.8.0-preview.1` | |
| 2026-02-20 | `0.9.0-preview.1` | |
| 2026-02-21 | `0.9.0-preview.2` | |
| 2026-02-24 | `1.0.0-rc.1` | |
| 2026-02-25 | `1.0.0` | erste Stable |
| **2026-03-06** | **`1.1.0`** | ← **release/3.6.2** |
| **2026-03-27** | **`1.2.0`** | ← **dev** (aktuellster Stable) |

### Beobachtungen zur Release-Kadenz

- ~33 Releases in 13 Monaten (`0.1.0-preview.2` 2025-03-27 → `1.2.0` 2026-03-27) — im Schnitt alle 12 Tage.
- Hochfrequenz-Phase `0.1` – `0.4` (Mär 2025 – Okt 2025): Preview alle ~10 Tage.
- Konsolidierungs-Phase ab `0.5` (Dez 2025): rund alle 5 Wochen ein Release.
- API-Stabilisierung am 2026-02-25 mit `1.0.0`. Danach reguläre Minor-Releases (`1.0` → `1.1` nach 9 Tagen, `1.1` → `1.2` nach 21 Tagen).
- Konsequenz für 3.3: SDK-Version stammt aus der Hochfrequenz-Preview-Phase — Backports von neueren Features tragen das Risiko, Schema-Renames zwischen Preview-Versionen mitnehmen zu müssen.

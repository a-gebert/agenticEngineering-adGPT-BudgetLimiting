# Konzept: Usage-Limits und Budgetierung für adessoGPT (v2.1)

**Version:** 2.1
**Status:** Entwurf zur Abstimmung
**Zielgruppe:** Product Owner, Architektur, Entwicklungsteam, Claude Code (Implementierung)
**Änderungen gegenüber v1:** Tier-Modell via bestehende Entra-ID-Gruppen und Gruppen-Tier-Mapping statt Policy/Assignment-System, Budget-State als Dokument im bestehenden `user`-Container statt Bucketed Counters, Audit-Log-Erweiterung statt separatem Usage-Records-Container, kein Change Feed Processor, keine neuen Cosmos-Container.
**Änderungen gegenüber v2.0:** Entra-ID-Gruppen ohne Rollen/Permissions klargestellt, Admin-UI für Tier-Definitionen in Scope gezogen (statt Non-Goal), BudgetTier/BudgetTierMapping/ModelPricing als `ISystemSetting` im Control-Center-Pattern.

---

## 1. Management-Summary

adessoGPT soll Administratoren ermöglichen, über Budget-Tiers die Plattformnutzung kontrolliert und kosteneffizient zu steuern. Tiers definieren Token-Budgets pro Zeitraum, monetäre Kosten-Obergrenzen (Hard Caps in USD) und Rate-Limits (Anfragen pro Minute). Die Zuordnung von Nutzern zu Tiers erfolgt über die bestehenden Entra-ID-Gruppen, die bereits im adessoGPT Control Center verwaltet werden. IT-Admins pflegen Gruppenmitgliedschaften wie gewohnt im Azure Portal – ein Gruppen-Tier-Mapping ordnet jeder Gruppe einen Budget-Tier zu.

Die Umsetzung nutzt ausschließlich bestehende Infrastruktur: das .NET-10-Backend mit MediatR, die bestehenden Cosmos-DB-Container `user` und `system`, und die bestehende Entra-ID-App-Registration. Es werden keine neuen Azure-Services, Container oder Infrastrukturkomponenten eingeführt.

Überschreitungsverhalten ist zweistufig: Ab 80 % Budget-Verbrauch erscheint ein Warn-Banner in der UI, ab 100 % werden weitere Anfragen blockiert.

---

## 2. Scope und Non-Goals

### In Scope

- Budget-Tiers mit konfigurierbaren Limits für Tokens, Kosten (USD) und Rate
- Tier-Zuordnung über Entra-ID-Gruppen (Pflege durch IT-Admins), ohne zusätzliche Rollen oder Permissions
- Default-Tier für User ohne explizite Zuweisung
- Admin-UI für Budget-Tier-Definitionen und Gruppen-Tier-Mapping im Control Center (`ISystemSetting`-Pattern)
- `BudgetTier`, `BudgetTierMapping` und `ModelPricing` als `ISystemSetting` mit CRUD, Caching und automatischem Audit-Log
- Budget-Enforcement vor jedem Azure-OpenAI-Call im Backend
- Atomare Verbrauchsbuchung per Cosmos Patch-Increment
- Tracking von Prompt-Tokens, Cached-Prompt-Tokens, Completion-Tokens und Reasoning-Tokens
- Kosten-Tracking primär in USD, mit EUR-Snapshot zum Buchungstag
- Soft-Warning-Banner ab konfigurierbarem Schwellwert
- Hard-Block bei 100 % Budget-Erreichen
- Fixed-Window-Rate-Limiting pro Minute

### Non-Goals

- E-Mail-Notifications (nur In-App-Banner)
- Azure API Management als Gateway-Layer
- Shared Budgets auf Abteilungs-/Projektebene
- Echtzeit-EUR-Enforcement (EUR nur als Report-Anzeige)
- Neue Cosmos-DB-Container oder Azure-Services

---

## 3. Geklärte Entscheidungen

| # | Thema | Entscheidung |
|---|---|---|
| 1 | Enforcement-Punkt | Backend, kein Gateway-Layer |
| 2 | Persistenz | Bestehende Cosmos-Container `user` und `system` |
| 3 | Abstraktionsschicht | MediatR Command/Query Handlers |
| 4 | Budget-Konfigurationsmodell | Tier-Modell (wenige vordefinierte Stufen) |
| 4a | Tier-Verwaltung | Admin-UI im Control Center (`ISystemSetting`-Pattern mit CRUD, Caching, Audit-Log) |
| 5 | Tier-Zuordnung | Bestehende Entra-ID-Gruppen aus Control Center → Tier-Mapping |
| 5a | Entra-ID-Gruppen | Reine Gruppenmitgliedschaft, keine zusätzlichen Rollen oder Permissions |
| 6 | User ohne gemappte Gruppe | Default-Tier greift automatisch |
| 6a | Konflikt bei mehreren Gruppen | Niedrigster (restriktivster) Tier gewinnt |
| 7 | Hard-Cap-Verhalten | Soft-Warning ab 80 %, Hard-Block bei 100 % |
| 8 | Primärwährung für Caps | USD |
| 9 | EUR-Anzeige | Ja, als Snapshot zum Buchungstag (EZB-Kurs) |
| 10 | Notifications | In-App-Banner, keine E-Mails |
| 11 | Counter-Strategie | Direkter Patch-Increment auf `UserBudgetState`-Dokument |
| 12 | Rate-Limiting | Fixed-Window pro Minute, TTL-basierte Dokumente |
| 13 | Tokenizer | `Microsoft.ML.Tokenizers` v2.0 |
| 14 | LLM-Anbindung | Direkter Azure-OpenAI-Call |
| 15 | Overspend-Toleranz | 1–3 Requests bei Parallelität akzeptabel |

---

## 4. Architektur-Übersicht

### 4.1 Request-Flow

Jeder Chat-Request durchläuft drei Phasen:

**Phase 1 – PreCheck:** Das User-Dokument wird ohnehin bei jedem Request gelesen. Der `PreCheckBudgetHandler` liest dabei das `UserBudgetState`-Dokument (Point-Read, ~1 RU) aus demselben Container und derselben Partition. Parallel wird der Budget-Tier des Users über die GroupId-Claims im JWT und das Gruppen-Tier-Mapping aufgelöst (Cache-Hit, kein DB-Call). Aus Tier-Limits und aktuellem Verbrauch wird die Entscheidung berechnet.

**Phase 2 – Azure-OpenAI-Call:** Nur bei Allow-Decision. Der `BudgetStatus` (WarningLevel in Prozent, verbleibendes Budget) wird in die Response an das Frontend geschrieben.

**Phase 3 – Record:** Nach erfolgreichem Call werden die tatsächlichen Token-Werte aus dem `usage`-Objekt des Azure-OpenAI-Responses gelesen. Die Kosten werden aus Token-Counts × `ModelPricing` berechnet. Zwei Cosmos-Patch-Operationen erfolgen:
1. Patch auf den bestehenden Audit-Log-Eintrag: `Set` der tatsächlichen Token-Felder (keine Kosten — diese sind aus den Rohdaten berechenbar)
2. Patch auf das `UserBudgetState`-Dokument: `Increment` der Counter-Felder (inkl. `CostUsd`)

### 4.2 Tier-Resolution

Der Tier-Resolver liest die Gruppen-Claims aus dem JWT, schlägt für jede Gruppe den gemappten Tier nach und wendet die Konflikt-Regel an:

```
GroupIds aus JWT extrahieren
  → Für jede GroupId: Mapping auf Tier nachschlagen (Cache-Hit)
  → Mehrere Tiers gefunden? → Niedrigster (restriktivster) gewinnt
  → Keine gemappte Gruppe? → Default-Tier
```

Kein DB-Call pro Request. Tier-Wechsel wird wirksam, sobald der User einen neuen Token erhält (Entra Token-Refresh, typischerweise 1 Stunde) oder die Gruppenzugehörigkeit in Entra ID geändert wird.

### 4.3 Streaming-Sonderfall

Bei Streaming-Responses sind tatsächliche Token-Counts erst im finalen Chunk verfügbar (`stream_options.include_usage=true`). Bei Client-Abbruch bucht der Handler geschätzte Werte mit `IsEstimate=true`. Schätzung basiert auf bekanntem Prompt plus bis zum Abbruch gestreamter Completion-Länge.

### 4.4 Periodische Aufgaben

**Reconciliation-Job (täglich):** Gleicht die `UserBudgetState`-Summen gegen die Audit-Log-Summen ab und korrigiert Differenzen (Sicherheitsnetz für fehlgeschlagene Patch-Operationen).

**FX-Worker (täglich):** Pullt den EZB-Referenzkurs USD→EUR und persistiert ihn als `FxRate`-Dokument.

**Perioden-Reset:** Neue `UserBudgetState`-Dokumente werden beim ersten Request einer neuen Periode lazy angelegt (kein Batch-Job nötig). Abgelaufene Dokumente bleiben als historische Snapshots erhalten.

---

## 5. Gruppen- und Tier-Zuordnung

### 5.1 Bestehende Gruppen aus dem Control Center

Die Budget-Tier-Zuordnung nutzt die bestehenden Entra-ID-Gruppen, die bereits im adessoGPT Control Center verwaltet werden. Die Gruppen haben keine zusätzlichen Rollen oder Permissions — die Zuordnung basiert ausschließlich auf der Gruppenmitgliedschaft. Es werden keine neuen Gruppen oder App Roles angelegt.

Die GroupIds sind im JWT-Token als `"groups"`-Claims verfügbar. Das Backend extrahiert diese über `UserAccessor.GetUserGroups()` als `UserGroupId[]` und matcht sie gegen das Gruppen-Tier-Mapping.

### 5.2 Gruppen-Tier-Mapping (`ISystemSetting`)

Ein Konfigurationsdokument in Cosmos (`BudgetConfiguration`-Partition) definiert, welche Gruppe zu welchem Tier gehört. Implementiert `ISystemSetting` und ist über das Control Center verwaltbar (CRUD, Caching, Audit-Log):

```json
{
  "id": "tier-mapping",
  "$type": "BudgetTierMapping",
  "SystemScope": "BudgetConfiguration",
  "Mappings": {
    "group-id-consulting": "tier-power",
    "group-id-alle-mitarbeiter": "tier-standard",
    "group-id-externe": "tier-restricted"
  }
}
```

Gruppen ohne Eintrag im Mapping werden ignoriert. User, deren Gruppen alle nicht gemappt sind, bekommen den Default-Tier.

### 5.3 Konfliktauflösung bei mehreren Gruppen

Tiers haben eine explizite Rangordnung (aufsteigend):

```
Restricted (1) < Standard (2) < Power (3)
```

Wenn ein User über mehrere Gruppen in verschiedenen Tiers landet, **gewinnt der niedrigste (restriktivste) Tier**. Beispiel:

- User ist in "Consulting" (→ Power, Rang 3) und "Alle Mitarbeiter" (→ Standard, Rang 2)
- Ergebnis: Standard (Rang 2) gewinnt

### 5.4 Workflow für IT-Admins

Tier-Zuweisung erfolgt ausschließlich über die Gruppenmitgliedschaft in Entra ID. Kein separates Budget-Admin-UI nötig. Der Ablauf:

1. IT-Admin fügt User zur Entra-Gruppe "Consulting" hinzu
2. Beim nächsten Token-Refresh enthält der JWT die neue GroupId
3. Das Backend matcht die GroupId gegen das Tier-Mapping
4. Der User bekommt den entsprechenden Tier

Änderung der Tier-Definitionen selbst (Limits, Modelle) erfolgt über die `BudgetTier`-Dokumente in Cosmos.

---

## 6. Cosmos DB Datenmodell

Es werden keine neuen Container angelegt. Alle neuen Dokumente werden über den `$type`-Discriminator in die bestehenden Container `user` und `system` integriert.

### 6.1 Container `user` (bestehend, PK: `/UserId`)

#### Neuer Dokumenttyp: `UserBudgetState`

Ein Dokument pro User pro Periode. Wird bei jedem Request gelesen (Point-Read, ~1 RU) und nach jedem erfolgreichen Azure-OpenAI-Call per Patch-Increment aktualisiert (~6 RU).

```json
{
  "id": "budget-1d840b51-a3d9-4477-8344-ffacdefa97e5-2026-04",
  "$type": "UserBudgetState",
  "UserId": "1d840b51-a3d9-4477-8344-ffacdefa97e5",
  "Period": "Monthly",
  "PeriodStart": "2026-04-01T00:00:00Z",
  "PeriodEnd": "2026-05-01T00:00:00Z",
  "TokensUsed": 125432,
  "CostUsd": 8.42,
  "RequestCount": 467,
  "LastRecordedAt": "2026-04-20T10:46:41.003Z"
}
```

**ID-Konvention:** `budget-{userId}-{YYYY-MM}` (bei monatlichen Perioden). Ermöglicht deterministische Point-Reads ohne vorherige Query.

**Lazy Creation:** Beim ersten Request einer neuen Periode wird das Dokument automatisch mit Nullwerten angelegt. Kein Batch-Job für Perioden-Reset nötig.

**Patch-Operation im RecordUsageHandler:**

```
PatchOperations:
  - Increment("/TokensUsed", actualTotalTokens)
  - Increment("/CostUsd", costUsd)
  - Increment("/RequestCount", 1)
  - Set("/LastRecordedAt", timestamp)
```

#### Neuer Dokumenttyp: `RateLimitWindow`

Fixed-Window-Counter pro User pro Minute. TTL von 120 Sekunden sorgt für automatische Bereinigung.

```json
{
  "id": "rl-1d840b51-2026-04-20T10-46",
  "$type": "RateLimitWindow",
  "UserId": "1d840b51-a3d9-4477-8344-ffacdefa97e5",
  "Minute": "2026-04-20T10:46",
  "Count": 7,
  "ttl": 120
}
```

**Check+Increment:** Per Patch-Operation `Increment("/Count", 1)`. Rückgabewert wird gegen das konfigurierte RPM-Limit geprüft.

**Bewusste Akzeptanz:** An Minutengrenzen kann das RPM-Limit kurzzeitig überschritten werden (Boundary-Burst). Für die Anforderung tragbar.

### 6.2 Container `system` (bestehend, PK: `/SystemScope`)

#### Erweiterung des bestehenden `ChatSessionAuditEntry`

Folgende Felder werden am bestehenden Audit-Eintrag ergänzt. Bestehende Felder bleiben unangetastet. Kosten-Felder (`CostUsd`, `CostEurSnapshot`, `FxRateUsdToEur`) werden bewusst **nicht** auf dem Audit-Eintrag gespeichert — sie sind aus den Token-Rohdaten, `ModelPricing` und `FxRate` jederzeit berechenbar. Das operative Kosten-Tracking erfolgt auf dem `UserBudgetState`.

```json
{
  "$type": "ChatSessionAuditEntry",
  "EstimatedPromptTokens": 4,
  "EstimatedResponseTokens": 59,

  "ActualPromptTokens": 1847,
  "ActualCompletionTokens": 312,
  "ActualCachedPromptTokens": 1024,
  "ActualReasoningTokens": 0,
  "ActualTotalTokens": 2159,
  "IsEstimate": false,
  "UsageRecordedAt": "2026-04-20T10:46:41.003Z"
}
```

**Zweistufiger Schreibprozess:**
1. Beim Absenden des Requests wird der Audit-Eintrag wie heute geschrieben (mit Estimated-Feldern, Actual-Felder sind `null`, `IsEstimate=true`).
2. Nach Empfang der Response werden die Actual-Token-Felder per Cosmos Patch-Operation gesetzt.

#### Neuer Dokumenttyp: `BudgetTier` (`ISystemSetting`)

Wenige Dokumente (3–5), über das Control Center verwaltbar. Implementiert `ISystemSetting<BudgetTierId>` und nutzt das bestehende `SystemSettingCachedRepositoryBase`-Pattern mit `IFusionCache` und automatischer Cache-Invalidierung bei Änderungen. Änderungen werden automatisch im Configuration Audit Log erfasst. Jeder Tier hat einen `Priority`-Wert für die Konfliktauflösung (niedrigerer Wert = restriktiver = gewinnt bei Mehrfach-Gruppenmitgliedschaft):

```json
{
  "id": "tier-restricted",
  "$type": "BudgetTier",
  "SystemScope": "BudgetConfiguration",
  "Name": "Restricted",
  "Priority": 1,
  "IsDefault": false,
  "TokenLimit": 50000,
  "TokenPeriod": "Monthly",
  "CostLimitUsd": 5.00,
  "CostPeriod": "Monthly",
  "RequestsPerMinute": 10,
  "SoftWarningPercent": 80,
  "AllowedModels": ["gpt-4.1-nano"]
}
```

```json
{
  "id": "tier-standard",
  "$type": "BudgetTier",
  "SystemScope": "BudgetConfiguration",
  "Name": "Standard",
  "Priority": 2,
  "IsDefault": true,
  "TokenLimit": 500000,
  "TokenPeriod": "Monthly",
  "CostLimitUsd": 25.00,
  "CostPeriod": "Monthly",
  "RequestsPerMinute": 30,
  "SoftWarningPercent": 80,
  "AllowedModels": ["gpt-5-mini", "gpt-4o-mini", "gpt-4.1-nano"]
}
```

```json
{
  "id": "tier-power",
  "$type": "BudgetTier",
  "SystemScope": "BudgetConfiguration",
  "Name": "Power User",
  "Priority": 3,
  "IsDefault": false,
  "TokenLimit": 2000000,
  "TokenPeriod": "Monthly",
  "CostLimitUsd": 100.00,
  "CostPeriod": "Monthly",
  "RequestsPerMinute": 60,
  "SoftWarningPercent": 80,
  "AllowedModels": ["gpt-5", "gpt-5-mini", "gpt-4o", "gpt-4o-mini"]
}
```

`Priority` bestimmt die Hierarchie: bei Mehrfach-Gruppenmitgliedschaft gewinnt der Tier mit dem niedrigsten Priority-Wert. `SystemScope` = "BudgetConfiguration" gruppiert alle Budget-bezogenen Konfigurationsdokumente in einer eigenen Logical Partition.

#### Neuer Dokumenttyp: `ModelPricing` (`ISystemSetting`)

Versionierte Preistabelle, über das Control Center verwaltbar. Implementiert `ISystemSetting<ModelPricingId>` mit CRUD, Caching und automatischem Audit-Log:

```json
{
  "id": "pricing-gpt-5-Global-2026-01",
  "$type": "ModelPricing",
  "SystemScope": "BudgetConfiguration",
  "ModelFamily": "gpt-5",
  "DeploymentType": "Global",
  "InputPricePer1MUsd": 1.25,
  "CachedInputPricePer1MUsd": 0.125,
  "OutputPricePer1MUsd": 10.00,
  "ValidFrom": "2026-01-01T00:00:00Z",
  "ValidUntil": null
}
```

#### Neuer Dokumenttyp: `FxRate`

Vom FX-Worker täglich befüllt:

```json
{
  "id": "fx-USD-EUR-2026-04-20",
  "$type": "FxRate",
  "SystemScope": "BudgetConfiguration",
  "BaseCurrency": "USD",
  "QuoteCurrency": "EUR",
  "Rate": 0.9189,
  "Date": "2026-04-20",
  "Source": "ECB",
  "FetchedAt": "2026-04-20T06:00:00Z"
}
```

---

## 7. MediatR Handler-Landkarte

### 7.1 Commands

| Command | Zweck |
|---|---|
| `PreCheckBudgetCommand` | Prüft alle Budget-Dimensionen vor Azure-OpenAI-Call |
| `RecordUsageCommand` | Patcht Audit-Log (Actual-Werte) + Patcht UserBudgetState (Increment) |
| `RecordEstimatedUsageCommand` | Variante für Streaming-Abbrüche |
| `ReconcileBudgetStatesCommand` | Täglicher Job: gleicht Views gegen Audit-Log ab |
| `IngestFxRateCommand` | Täglicher Job: EZB-Kurs pullen und speichern |

### 7.2 Queries

| Query | Zweck |
|---|---|
| `GetCurrentBudgetStatusQuery` | Liefert aktuellen Verbrauch + Rest-Budget für UI-Anzeige |
| `GetUsageReportQuery` | Admin-Reporting: Verbrauch nach Zeitraum/Modell/User |
| `GetTopConsumersQuery` | Admin-Reporting: Top-N Nutzer einer Periode |

### 7.3 Domain-Services

| Service | Verantwortung |
|---|---|
| `IBudgetTierResolver` | GroupId-Claims aus JWT → Mapping nachschlagen → niedrigster Tier |
| `ITokenEstimator` | `Microsoft.ML.Tokenizers` inkl. Chat-Message-Overhead |
| `ICostCalculator` | Token-Counts × Pricing → USD-Betrag |
| `IFxRateProvider` | Aktueller USD→EUR-Kurs mit Caching |

---

## 8. Token- und Kostenberechnung

### 8.1 Token-Schätzung vor dem Call (PreCheck)

Prompt-Tokens werden über `Microsoft.ML.Tokenizers` v2.0 geschätzt. Pro Chat-Message fallen zusätzlich ca. 3–4 Tokens Overhead an (Role-Marker, Meta-Tags), plus 3 Tokens für den Assistant-Reply-Start. Completion-Tokens werden als `MaxOutputTokens` des Requests angenommen (Worst-Case).

### 8.2 Tatsächliche Werte nach dem Call

Aus dem Azure-OpenAI-Response-`usage`-Objekt:

- `prompt_tokens` – gesamte Input-Tokens
- `prompt_tokens_details.cached_tokens` – davon aus Cache (separate Preislogik)
- `completion_tokens` – Output-Tokens
- `completion_tokens_details.reasoning_tokens` – bei o-Serie/GPT-5 separat

### 8.3 Kostenformel

```
costUsd = (nonCachedPromptTokens / 1_000_000) × inputPrice
        + (cachedPromptTokens    / 1_000_000) × cachedInputPrice
        + (completionTokens      / 1_000_000) × outputPrice
```

Wobei `nonCachedPromptTokens = prompt_tokens - cached_prompt_tokens`.

### 8.4 Worst-Case-Schätzung im PreCheck

```
worstCaseCost = estimatedPromptTokens × inputPrice + maxCompletionTokens × outputPrice
```

Cached-Token-Rabatt wird nicht angenommen, um sicher zu sein.

---

## 9. Frontend-Vertrag

Der `BudgetStatus` wird in jeder Chat-Response mitgeliefert:

```json
{
  "budgetStatus": {
    "warningLevelPercent": 82,
    "tokensRemaining": 74568,
    "costRemainingUsd": 4.16,
    "tierName": "Standard"
  }
}
```

| WarningLevel | UI-Verhalten |
|---|---|
| 0–79 % | Nichts anzeigen |
| 80–94 % | Gelbes Banner: "Sie haben 82 % Ihres Monatsbudgets verbraucht" |
| 95–99 % | Rotes Banner: "Bei Erreichen des Limits werden weitere Anfragen blockiert" |
| 100 % | HTTP 403 + Fehlermeldung: "Budget erreicht. Bitte wenden Sie sich an Ihren Administrator." |

---

## 10. Edge Cases und Risiken

### 10.1 Race Condition bei parallelen Requests

Zwischen PreCheck-Read und Record-Patch können parallele Requests desselben Users weitere Tokens verbrauchen. Overspend von 1–3 Requests ist akzeptiert. Der PreCheck rechnet mit Worst-Case-Tokens, was die Wahrscheinlichkeit verringert.

### 10.2 Fehlgeschlagener Patch auf UserBudgetState

Audit-Log hat den korrekten Eintrag, Budget-State ist zu niedrig. Der tägliche Reconciliation-Job korrigiert die Differenz.

### 10.3 Boundary-Burst beim Rate-Limit

An Minutengrenzen theoretisch 2×RPM möglich. Akzeptiert als Kompromiss.

### 10.4 Tier-Wechsel-Latenz

Nach Änderung der Gruppenmitgliedschaft in Entra ID wird der neue Tier erst wirksam, wenn der User einen neuen Token erhält (Entra Token-Refresh, typischerweise ≤ 1 Stunde). In der Zwischenzeit gilt der alte Tier. Zusätzlich wird das Gruppen-Tier-Mapping im Backend für 5 Minuten gecacht – Änderungen am Mapping selbst brauchen bis zu 5 Minuten bis zur Wirksamkeit.

### 10.5 Streaming-Abbruch

Bei Netzwerkfehler vor finalem Chunk: geschätzte Werte mit `IsEstimate=true`. Reconciliation-Job kann diese nachträglich korrigieren.

### 10.6 Preisänderungen durch Microsoft

`ModelPricing`-Dokumente müssen manuell aktualisiert werden. Monitoring-Job vergleicht monatlich berechnete Kosten mit Azure-Billing-Export.

### 10.7 DSGVO

Audit-Log enthält UserId und ConversationId. Bestehende Retention-Policies gelten. Bei User-Offboarding werden `UserBudgetState`-Dokumente mit gelöscht (gleiche Partition wie andere User-Daten).

---

## 11. Offene Punkte vor Implementierungsstart

| # | Punkt | Zu klären mit |
|---|---|---|
| 1 | Konkrete Default-Werte für Standard-Tier (Tokens, USD, RPM) | Product Owner |
| 2 | Soll `ConversationId` ein eigenes Budget haben (Per-Conversation-Cap)? | Product Owner, Architektur |
| 3 | Braucht es mehr als drei Tiers? | Product Owner |
| 4 | Composite-Index auf `system`-Container für `(UserId, CreatedAt)` anlegen (für Reconciliation und Reports) | Ops / DBA |
| 5 | TTL-Strategie für abgelaufene `UserBudgetState`-Dokumente (behalten vs. löschen) | Product Owner |
| 6 | Monitoring-Dashboards (Application Insights / Power BI) | Ops |
| 7 | Zeitzonen: UTC (geplant) oder Europe/Berlin für Periodengrenzen? | Product Owner |

---

## 12. Umsetzungsplan

### Etappe 1: Walking Skeleton (1–2 Wochen)

- `BudgetTier`, `BudgetTierMapping` und `ModelPricing` als `ISystemSetting` im `system`-Container mit CRUD-Endpoints, `SystemSettingCachedRepositoryBase`, Audit-Konfiguration und Seed-Daten
- Control-Center-Endpoints für Tier-Verwaltung und Gruppen-Tier-Mapping
- `BudgetTierResolver` implementieren (GroupId-Claims aus JWT → Tier-Mapping → niedrigster Tier, mit IFusionCache)
- `UserBudgetState`-Dokumenttyp im `user`-Container
- `PreCheckBudgetCommand` mit Token-Limit-Check gegen `UserBudgetState`
- `RecordUsageCommand` mit Patch-Increment auf `UserBudgetState`
- Test-Endpoint `/api/chat/mock` ohne echten Azure-OpenAI-Call
- `.http`-Datei für manuelles Durchspielen

### Etappe 2: MVP (2–3 Wochen)

- `TokenEstimator` mit `Microsoft.ML.Tokenizers` inkl. Chat-Message-Overhead
- `CostCalculator` mit Cached/Non-Cached/Reasoning-Unterscheidung
- Rate-Limiting via `RateLimitWindow`-Dokumente
- Audit-Log-Erweiterung (Actual-Token-Felder, CostUsd, Patch nach Response)
- Integration in realen Chat-Endpoint mit Azure-OpenAI-SDK
- Streaming-Handling mit `RecordEstimatedUsageCommand`
- Composite-Index auf `system`-Container für Reporting-Queries
- `BudgetStatus` in Chat-Response für Frontend-Banner

### Etappe 3: Production-Ready (2 Wochen)

- FX-Worker mit EZB-Feed
- Täglicher Reconciliation-Job
- Application-Insights-Telemetrie für Budget-Entscheidungen
- Load-Tests mit parallelen Requests
- Feature-Flag-Gate für kontrollierten Rollout
- Dokumentation: Runbook, Monitoring-Queries, Troubleshooting

### Etappe 4: Reporting (separates Feature)

- Reporting-Dashboard mit Top-Verbrauchern, Trend-Analysen
- Export-Funktion für Controlling (CSV/Excel mit EUR-Spalte)

---

## 13. Container- und Dokumentübersicht

### Container `user` (bestehend, PK: `/UserId`)

| `$type` | Neu? | Zweck |
|---|---|---|
| `UserChatMessage` | Bestehend | Chat-Nachrichten |
| `UserBudgetState` | **Neu** | Budget-Counter pro User/Periode |
| `RateLimitWindow` | **Neu** | Fixed-Window RPM-Counter mit TTL |
| (weitere bestehende Typen) | Bestehend | — |

### Container `system` (bestehend, PK: `/SystemScope`)

Der `system`-Container enthält verschiedene Dokumenttypen, die über den `SystemScope`-Wert in **getrennte Logical Partitions** fallen. Die neuen Budget-Dokumente berühren den bestehenden Audit-Log nicht – sie leben in einer eigenen Partition.

**Logical Partition `UserChatAudit`** (bestehend):

| `$type` | Änderung | Zweck |
|---|---|---|
| `ChatSessionAuditEntry` | **Erweitert** um Actual-Token- und Kosten-Felder | Audit-Trail pro Chat-Turn |
| (weitere bestehende Typen) | Keine | — |

**Logical Partition `BudgetConfiguration`** (neu):

| `$type` | Zweck | Anzahl Dokumente |
|---|---|---|
| `BudgetTier` (`ISystemSetting`) | Tier-Definitionen (Restricted, Standard, Power) mit Priority, über Control Center verwaltbar | 3–5, per UI pflegbar |
| `BudgetTierMapping` (`ISystemSetting`) | Zuordnung Entra-GroupId → TierId, über Control Center verwaltbar | 1 Dokument, per UI pflegbar |
| `ModelPricing` (`ISystemSetting`) | Preistabelle pro Modell und Deployment-Typ, über Control Center verwaltbar | ~10–20, per UI pflegbar |
| `FxRate` | Tageskurse USD→EUR vom EZB-Feed | 1 pro Tag, mit TTL |

Die Trennung in eigene Logical Partitions bedeutet: Budget-Konfigurationsdaten und Audit-Einträge teilen keine RU-Kapazität und beeinflussen sich gegenseitig nicht.

---

## 14. Glossar

| Begriff | Bedeutung |
|---|---|
| **Tier** | Vordefinierte Budget-Stufe (Restricted, Standard, Power) mit expliziter Rangordnung |
| **Priority** | Rang eines Tiers (1 = restriktivster). Bei Mehrfach-Gruppenmitgliedschaft gewinnt der niedrigste Wert |
| **Gruppen-Tier-Mapping** | Konfigurationsdokument, das Entra-GroupIds auf TierIds abbildet |
| **UserBudgetState** | Cosmos-Dokument mit akkumuliertem Verbrauch pro User/Periode |
| **Patch-Increment** | Cosmos-DB-Operation, die einen Zahlenwert serverseitig atomar erhöht |
| **Point-Read** | Cosmos-DB-Lesevorgang per `id` + Partition-Key (~1 RU, < 5ms) |
| **Soft Warning** | Prozentwert, ab dem UI-Banner erscheint (Default: 80 %) |
| **Hard Cap** | Harte Obergrenze, bei deren Erreichen Requests blockiert werden |
| **Reconciliation** | Täglicher Abgleich der Budget-State-Summen gegen Audit-Log |
| **Cached Tokens** | Prompt-Tokens aus Azure-OpenAI-Prompt-Cache (ca. 90 % Preisrabatt) |
| **Reasoning Tokens** | Bei o-Serie/GPT-5: interne Denk-Tokens, separat ausgewiesen |

---

*Ende des Konzept-Dokuments v2*

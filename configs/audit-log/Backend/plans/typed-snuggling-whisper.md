# Plan: Rückbau Download Service — Einstufiger Audit Export

## Context

PR-Feedback: Der dreistufige Export-Ansatz (Start → Status-Polling → Download via Blob Storage) soll durch einen einstufigen ersetzt werden. Azure Blob Storage Upload entfällt. Stattdessen: ein einziger GET-Endpoint, der die Daten direkt aus der DB streamt und als FileStream-Response zurückgibt.

## Betroffene Dateien

### Löschen (14 Dateien + 3 Testdateien)

**Background Service Infrastruktur:**
- `Export/ChatAuditExportBackgroundService.cs`
- `Export/ChatAuditExportJob.cs`
- `Export/ChatAuditExportStatus.cs`

**Stage 1 — Start Command (gesamter Ordner):**
- `Export/StartChatAuditExport/StartChatAuditExportCommand.cs`
- `Export/StartChatAuditExport/StartChatAuditExportCommandHandler.cs`
- `Export/StartChatAuditExport/StartChatAuditExportCommandValidator.cs`
- `Export/StartChatAuditExport/StartChatAuditExportCommandResponse.cs`

**Stage 2 — Status-Polling (gesamter Ordner):**
- `Export/GetChatAuditExportStatus/GetChatAuditExportStatusQuery.cs`
- `Export/GetChatAuditExportStatus/GetChatAuditExportStatusQueryHandler.cs`
- `Export/GetChatAuditExportStatus/GetChatAuditExportStatusQueryValidator.cs`
- `Export/GetChatAuditExportStatus/GetChatAuditExportStatusQueryResponse.cs`

**Stage 3 — Download (gesamter Ordner):**
- `Export/DownloadChatAuditExport/DownloadChatAuditExportQuery.cs`
- `Export/DownloadChatAuditExport/DownloadChatAuditExportQueryHandler.cs`
- `Export/DownloadChatAuditExport/DownloadChatAuditExportQueryValidator.cs`
- `Export/DownloadChatAuditExport/IChatAuditExportDownloadStrategy.cs`
- `Export/DownloadChatAuditExport/StreamingChatAuditExportDownloadStrategy.cs`

**Tests:**
- `Tests/.../Audit/ControlCenter/StartChatAuditExportCommandHandlerTests.cs`
- `Tests/.../Audit/ControlCenter/GetChatAuditExportStatusQueryHandlerTests.cs`
- `Tests/.../Audit/ControlCenter/DownloadChatAuditExportQueryHandlerTests.cs`

### Beibehalten (3 Dateien — wiederverwendbar)

- `Export/ChatAuditExportEntry.cs` — DTO-Mapping Entity → Export-Format
- `Export/IChatAuditExportFormatter.cs` — Strategy-Interface für Formate
- `Export/JsonChatAuditExportFormatter.cs` — JSON-Formatter (System.Text.Json, camelCase, streamed)

### Anpassen (2 Dateien)

- `ChatSessionAudit/ChatSessionAuditEndpoints.cs` — 3 Export-Endpoints → 1
- `ControlCenterModule.cs` — DI-Registrierungen bereinigen

### Neu erstellen (3 Dateien + 1 Testdatei)

- `Export/ExportChatAudit/ExportChatAuditQuery.cs`
- `Export/ExportChatAudit/ExportChatAuditQueryHandler.cs`
- `Export/ExportChatAudit/ExportChatAuditQueryValidator.cs`
- `Tests/.../Audit/ControlCenter/ExportChatAuditQueryHandlerTests.cs`

---

## Implementierungsschritte

### Schritt 1: Neue Query + Handler + Validator erstellen

**`ExportChatAuditQuery.cs`** — Ersetzt den alten StartChatAuditExportCommand:
```csharp
public record ExportChatAuditQuery : IQuery<IResult>
{
    public Guid? UserId { get; init; }
    public ModelOptionsId? ModelOptionsId { get; init; }
    public DateTimeOffset? FromDate { get; init; }
    public DateTimeOffset? ToDate { get; init; }
    public required string Format { get; init; }
}
```

**`ExportChatAuditQueryHandler.cs`** — Vereint Logik aus BackgroundService + DownloadHandler:
- Prüft Audit-Feature enabled (aus `ISingleSettingsRepository<ChatAuditLogSettings>`)
- Findet passenden Formatter via `IEnumerable<IChatAuditExportFormatter>`
- Baut DB-Query mit Filtern (Logik aus `ChatAuditExportBackgroundService.QueryAuditEntriesAsync` übernehmen)
- Schreibt via Formatter in MemoryStream
- Gibt `TypedResults.Stream(stream, contentType, fileName)` zurück

Kernlogik des Handlers:
```csharp
// 1. Feature-Gate
var settings = await settingsRepository.GetAsync(cancellationToken);
if (settings is null || !settings.IsEnabled)
    return BusinessError.Conflict(...);

// 2. Formatter finden
var formatter = formatters.FirstOrDefault(f => string.Equals(f.Format, request.Format, ...));
if (formatter is null)
    return BusinessError.Conflict(...);

// 3. DB-Query mit Filtern (aus BackgroundService übernommen)
var entries = QueryAuditEntries(dbContext, request);
var exportData = entries.Select(ChatAuditExportEntry.FromEntity);

// 4. In MemoryStream schreiben und als FileStream zurückgeben
var stream = new MemoryStream();
await formatter.WriteAsync(exportData, stream, cancellationToken);
stream.Position = 0;

var fileName = BuildFileName(request, formatter);
return TypedResults.Stream(stream, formatter.ContentType, fileName);
```

Die Filter-Logik (`QueryAuditEntries`) und `BuildFileName` werden als private Methoden aus dem BackgroundService 1:1 übernommen.

**`ExportChatAuditQueryValidator.cs`** — Validierung aus StartChatAuditExportCommandValidator übernehmen:
- Format nicht leer, muss in `["json"]` sein
- FromDate <= ToDate (wenn beide vorhanden)

### Schritt 2: Endpoints anpassen

**`ChatSessionAuditEndpoints.cs`** — 3 Export-Endpoints durch 1 ersetzen:
```csharp
// Vorher:
group.MapPostCQRSFromBody<StartChatAuditExportCommand, ...>("export")...;
group.MapGetCQRS<GetChatAuditExportStatusQuery, ...>("export/{exportId}/status");
group.MapGetCQRS<DownloadChatAuditExportQuery, IResult>("export/{exportId}/download", ...);

// Nachher:
group.MapGetCQRS<ExportChatAuditQuery, IResult>("export", (_, result) => result);
```

### Schritt 3: DI-Registrierungen bereinigen

**`ControlCenterModule.cs`** — Entfernen:
```csharp
// ENTFERNEN:
services.AddSingleton<ChatAuditExportBackgroundService>();
services.AddHostedService(sp => sp.GetRequiredService<ChatAuditExportBackgroundService>());
services.AddScoped<IChatAuditExportDownloadStrategy, StreamingChatAuditExportDownloadStrategy>();

// BEIBEHALTEN:
services.AddSingleton<IChatAuditExportFormatter, JsonChatAuditExportFormatter>();
```

### Schritt 4: Alte Dateien löschen

Alle 14 Dateien + 3 Ordner aus der "Löschen"-Liste oben entfernen.

### Schritt 5: Tests schreiben

**`ExportChatAuditQueryHandlerTests.cs`** — Testfälle:
1. Audit-Feature deaktiviert → BusinessError
2. Unbekanntes Format → BusinessError
3. Erfolgreich → gibt IResult (Stream) zurück
4. Mit Filtern (UserId, ModelOptionsId, DateRange) → korrekte DB-Filterung
5. Validator: leeres Format, ungültiger Datumsbereich

### Schritt 6: Build + Formatter

```bash
dotnet build
dotnet csharpier format .
```

---

## Ergebnis-Architektur

```
Vorher (3-stufig):
  POST /export → BackgroundService → Blob Storage → Poll → Download

Nachher (1-stufig):  
  GET /export?format=json&fromDate=...&toDate=... → DB-Query → Formatter → FileStream Response
```

**Entfallene Abhängigkeiten:**
- `IFileStorageRepository` (kein Blob Storage mehr)
- `IFusionCache` (kein Status-Caching mehr)
- `Channel<T>` / `BackgroundService` (keine asynchrone Verarbeitung)
- `IChatAuditExportDownloadStrategy` (kein Strategy-Pattern mehr nötig)

**Beibehaltene Abstraktionen:**
- `IChatAuditExportFormatter` — weiterhin erweiterbar für CSV/Excel etc.
- `ChatAuditExportEntry` — sauberes DTO-Mapping

# MCP Elicitation: zweiter Dialog verschwindet ohne User-Antwort

## Symptom

Bei einem MCP-Tool-Call, der **zwei aufeinanderfolgende Elicitations** auslöst:

1. Der erste Elicitation-Dialog erscheint, der User beantwortet ihn — funktioniert.
2. Der zweite Elicitation-Dialog erscheint **nur ganz kurz** (~500 ms), der User kann nicht klicken.
3. Etwa **5 Minuten später** erscheint ein Toast mit „Verbindungsproblemen".

Im Backend-Log (Datum: 2026-05-05, vor dem Fix sichtbar):

```
machine_maintainer transport message parsing failed.
System.Text.Json.JsonException: The input does not contain any JSON tokens.
   at ModelContextProtocol.Client.StreamableHttpClientSessionTransport.ProcessMessageAsync(...)
...
Elicitation timeout or cancelled for ID: <Guid>
```

## Zwei unabhängige Root Causes

Das Symptom hat zwei separate Ursachen. Bei einem Tool-Call, der nur **eine** Elicitation auslöst, war der Bug nicht reproduzierbar — er manifestiert sich erst bei der zweiten ELI. Vor dem Fix wirkte (1) als Multiplikator für (2).

### Root Cause #1 — MCP C# SDK: `JsonException` auf 202+leerer-Body

**Wo:** `ModelContextProtocol.Client.StreamableHttpClientSessionTransport.ProcessMessageAsync(string data, …)`
**Versionen:** mindestens 0.3-preview.4 bis **1.1.0** (offen bestätigt).
**Upstream-Issue:** [csharp-sdk #1132](https://github.com/modelcontextprotocol/csharp-sdk/issues/1132) — offen, kein PR gemerged.

Der MCP-Server (hier `machine_maintainer`) antwortet auf eine ausgehende JSON-RPC-Notification oder -Response mit `HTTP 202 Accepted`, `Content-Type: application/json` und **leerem Body** — laut [MCP Streamable-HTTP-Spec](https://modelcontextprotocol.io/specification) zulässig. Der SDK-Client versucht trotzdem, den leeren Body zu deserialisieren:

```csharp
private async Task<JsonRpcMessageWithId?> ProcessMessageAsync(string data, …)
{
    LogTransportReceivedMessageSensitive(Name, data);
    try
    {
        var message = JsonSerializer.Deserialize(data, McpJsonUtilities.JsonContext.Default.JsonRpcMessage);
        …
    }
    catch (JsonException ex)
    {
        LogJsonException(ex, data);   // wird nur geloggt, nicht propagiert
    }
    return null;
}
```

Die Exception wird **gefangen und nur geloggt** — sieht harmlos aus, ist es nicht: durch das `return null` aus dem Catch-Block kommt die interne Stream-State-Verwaltung in einen Zustand, in dem **der `CancellationToken` für den nächsten ausstehenden Server-zu-Client-Request gecancelt wird**. Bei der zweiten Elicitation (Server schickt `elicitation/create`) cancelt das SDK den Token, den es an den Client-Handler übergibt.

### Root Cause #2 — Frontend: Race in `closeElicitationDialog`

**Wo:** `adessoGPT.UI/src/store/slices/elicitationDialogSlice.ts` und `adessoGPT.UI/src/components/Chat/Dialogs/ElicitationDialog.tsx`
**Verhalten:** unabhängig vom SDK-Bug; existiert auch nach Fix #1.

Im Submit-Handler des Dialogs steht (gekürzt):

```ts
await conversationsService.submitElicitationResponse(elicitationData.elicitationId, 'accept', submissionData)

// add 300ms delay to show the submitting state a bit longer for UX
await new Promise((resolve) => setTimeout(resolve, 500))

dispatch(closeElicitationDialog())
```

**Race-Fenster:** während des `await submitElicitationResponse(...)` plus der nachgelagerten 500-ms-Pause kann der MCP-Server bereits die nächste Elicitation an den Client schicken, das Backend pusht sie via `PublishResponseToChatStream` → der Reducer ruft `openElicitationDialog(eli2)` auf → der Redux-State zeigt jetzt **ELI #2**. Dann läuft der `dispatch(closeElicitationDialog())`-Aufruf, dessen Reducer `isOpen = false` und `elicitationData = null` **ohne ID-Prüfung** setzt — die zweite Elicitation wird dadurch fälschlich geschlossen.

Im Backend ist nichts beantwortet, der Backend-Handler wartet 5 Minuten (`timeoutCts.CancelAfter(TimeSpan.FromMinutes(5))` in `DefaultElicitationHandler`), läuft dann in `OperationCanceledException` → setzt `BusinessError` → Toast.

## Diagnose-Vorgehen (für andere Release-Stände)

### Schritt 1 — Symptom verifizieren

Reproduziere mit einem MCP-Tool, das **mindestens zwei Elicitations** in Folge auslöst (wie `machine_maintainer.get_solutions` im voestalpine-Setup).

### Schritt 2 — File-Logging aktivieren

Per Default loggt der API-Server nur in die Console (Buffer-Limit). Für saubere Diagnose persistent loggen — additiv in `appsettings.Local.json`:

```json
"Serilog": {
    "WriteTo": [
        {
            "Name": "File",
            "Args": {
                "path": "logs/adessoGPT-.log",
                "rollingInterval": "Day",
                "retainedFileCountLimit": 7,
                "outputTemplate": "[{Timestamp:HH:mm:ss.fff} {Level:u3}] {SourceContext}: {Message:lj}{NewLine}{Exception}"
            }
        }
    ]
}
```

Voraussetzung: `Serilog.Sinks.File` muss Package-Referenz sein (im Telemetry-Projekt). Mindestversion `7.0.0` (sonst Konflikt mit `Serilog.AspNetCore 10`). Eintrag in `Directory.Packages.props`.

### Schritt 3 — Pattern-Counts prüfen

```bash
LOG=Backend/Presentation/adessoGPT.Presentation.Api/logs/adessoGPT-<datum>.log
grep -c "transport message parsing failed" $LOG          # Indiz für Root Cause #1
grep -c "Elicitation timeout or cancelled" $LOG          # Indiz Backend-Cancel (#1) ODER 5-min-Timeout (#2)
grep -c "elicitation/create' request handler called"     # wie viele ELIs kamen rein
grep -c "elicitation/create' request handler completed"  # wie viele wurden abgeschlossen
```

**Vor Fix #1:** `transport message parsing failed` ≥ 2; `Elicitation timeout or cancelled` mit Dauer **wenige Sekunden** (nicht 300 s) → Root Cause #1 aktiv.

**Nach Fix #1, vor Fix #2:** `transport message parsing failed` = 0; `Elicitation timeout or cancelled` mit Dauer **~300 042 ms (= 5 Min)** → Root Cause #2 aktiv (Frontend-Race, Backend-Handler hat fachlichen 5-Min-Timeout gezogen).

**Nach beiden Fixes:** Beide Patterns leer (außer User antwortet bewusst nicht innerhalb 5 Min).

## Fix #1 — Backend: DelegatingHandler für 202+leerer-Body

**Idee:** Den leeren Body durch das JSON-Literal `null` (4 Bytes) ersetzen, **bevor** das SDK ihn sieht. Das deserialisiert sauber zu `null`, der SDK-Pfad `if (message is null) { LogTransportMessageParseUnexpectedTypeSensitive(...); return null; }` läuft schadlos durch — kein Stream-State-Schaden, kein CT-Cancel.

### Neue Datei: `Backend/Infrastructure/adessoGPT.Infrastructure.Mcp/Connection/McpEmpty202BodyHandler.cs`

```csharp
namespace adessoGPT.Infrastructure.Mcp.Connection;

using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

// Workaround for ModelContextProtocol C# SDK issue #1132:
// https://github.com/modelcontextprotocol/csharp-sdk/issues/1132
//
// SDK throws JsonException on empty 202 body, swallows it, but state corruption
// causes the next inbound server-to-client request token to be cancelled —
// killing e.g. a second elicitation/create dialog before the user can answer.
internal class McpEmpty202BodyHandler : DelegatingHandler
{
    private readonly ILogger<McpEmpty202BodyHandler> _logger;

    public McpEmpty202BodyHandler(ILogger<McpEmpty202BodyHandler> logger)
    {
        _logger = logger;
    }

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken
    )
    {
        var response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);

        if (response.StatusCode != HttpStatusCode.Accepted)
        {
            return response;
        }
        if (response.Content.Headers.ContentType?.MediaType is not "application/json")
        {
            return response;
        }

        var bytes = await response.Content.ReadAsByteArrayAsync(cancellationToken).ConfigureAwait(false);
        if (bytes.Length > 0)
        {
            response.Content = new ByteArrayContent(bytes);
            response.Content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/json");
            return response;
        }

        _logger.LogDebug(
            "Empty 202 body from MCP server; injecting 'null' to bypass csharp-sdk #1132 (URL: {Url})",
            request.RequestUri
        );

        response.Content.Dispose();
        response.Content = new StringContent("null", Encoding.UTF8, "application/json");
        return response;
    }
}
```

### Registrierung in `McpInfrastructureModule.cs`

Direkt nach `services.AddTransient<McpCallbackHeaderHandler>();`:

```csharp
// Workaround for ModelContextProtocol csharp-sdk #1132: rewrite empty-body 202 responses
// so the SDK does not throw JsonException and corrupt stream state.
services.AddTransient<McpEmpty202BodyHandler>();
```

In der HttpClient-Pipeline, **nach** dem CallbackHeader-Handler:

```csharp
.AddHttpMessageHandler<McpCallbackHeaderHandler>()
.AddHttpMessageHandler<McpEmpty202BodyHandler>()      // ← neu
.RemoveAllResilienceHandlers()
```

## Fix #2 — Frontend: ID-checked Close

**Idee:** `closeElicitationDialog` nimmt optional eine `elicitationId`. Wenn der State zwischenzeitlich auf eine **andere** ELI gewechselt hat, ist der Close ein No-op.

### `adessoGPT.UI/src/store/slices/elicitationDialogSlice.ts`

```ts
closeElicitationDialog: (state, action: PayloadAction<string | undefined>) => {
    const targetId = action.payload
    // If a newer elicitation has arrived in the meantime, do not dismiss it.
    if (targetId !== undefined && state.elicitationData?.elicitationId !== targetId) {
        return
    }
    state.isOpen = false
    state.elicitationData = null
    state.isSubmitting = false
},
```

### `adessoGPT.UI/src/components/Chat/Dialogs/ElicitationDialog.tsx`

In `handleSubmit`, `handleDecline`, `handleCancel` jeweils die ID **vor** dem await capturen und an `closeElicitationDialog` übergeben:

```ts
const handleSubmit = async () => {
    if (!elicitationData) return

    const submittedId = elicitationData.elicitationId   // capture before await
    dispatch(setElicitationSubmitting(true))

    try {
        const submissionData = { ...formData }
        Object.entries(elicitationData.schema).forEach(([key, field]) => {
            if (field.type === 'boolean' && !(key in submissionData)) {
                submissionData[key] = false
            }
        })

        await conversationsService.submitElicitationResponse(submittedId, 'accept', submissionData)

        await new Promise((resolve) => setTimeout(resolve, 500))

        dispatch(closeElicitationDialog(submittedId))   // ← only close if state still shows this ELI
        setFormData({})
    } catch (error) {
        console.error('Failed to submit elicitation response:', error)
        errorHandlerService.toastError(error)
    } finally {
        dispatch(setElicitationSubmitting(false))
    }
}

const handleDecline = () => {
    if (!elicitationData) return
    const id = elicitationData.elicitationId
    dispatch(closeElicitationDialog(id))
    setFormData({})
    conversationsService.submitElicitationResponse(id, 'decline')
}

const handleCancel = () => {
    if (!elicitationData) return
    const id = elicitationData.elicitationId
    dispatch(closeElicitationDialog(id))
    setFormData({})
    conversationsService.submitElicitationResponse(id, 'cancel')
}
```

> Hinweis: `handleDecline` und `handleCancel` haben das gleiche Race-Risiko (wenn auch mit kleinerem Fenster, weil sie kein `await` vor dem dispatch haben). Sicherheitshalber ebenfalls ID-basiert schließen.

## Verifikation

1. Backend neu bauen und starten — `npm run build` für das React-Frontend.
2. Reproduzieren: Tool mit zwei Elicitations triggern.
3. **Erwartet:**
   - Erste ELI funktioniert wie zuvor.
   - Zweite ELI bleibt offen, User kann antworten, Tool läuft normal weiter.
   - Im Log: `transport message parsing failed` = 0; `Elicitation timeout or cancelled` nur wenn User bewusst ≥ 5 Min nicht antwortet.
   - DEBUG (falls aktiviert): `Empty 202 body from MCP server; injecting 'null' …` → Beweis, dass der Workaround tatsächlich greift.

## Cleanup wenn upstream gefixt

Sobald [csharp-sdk #1132](https://github.com/modelcontextprotocol/csharp-sdk/issues/1132) gefixt und auf eine ModelContextProtocol-Version mit dem Fix gehoben wurde:

1. `McpEmpty202BodyHandler.cs` löschen.
2. Registrierung in `McpInfrastructureModule.cs` entfernen.
3. Reproduktion einmal ohne Workaround durchspielen — Bug muss weg sein, sonst Workaround behalten.

Fix #2 (Frontend) sollte **bestehen bleiben** — die Race ist unabhängig vom SDK und kann auch durch andere Latenzen (Netzwerk, anderer MCP-Server) ausgelöst werden.

## Portierung auf andere Release-Stände

- Code-Stellen sind über **Symbole/Datei-Pfade** identifiziert, nicht über Zeilennummern.
- Der `DefaultElicitationHandler` mit `LogWarning("Elicitation timeout or cancelled for ID: …")` ist die zentrale Anlaufstelle für die Backend-Diagnose.
- Wenn der Frontend-Stack auf einen Branch ohne `elicitationDialogSlice` portiert wird (z.B. Angular-Frontend unter `Frontend/adessoGPT.Web`), muss die ID-checked-Logik dort analog umgesetzt werden — gleicher Bauplan, nur mit Signals statt Redux.

## Referenzen

- [MCP C# SDK Issue #1132 — Streamable HTTP transport doesn't correctly handle empty response](https://github.com/modelcontextprotocol/csharp-sdk/issues/1132)
- [MCP Python SDK Issue #1661 — Streamable HTTP Transport Doesn't Handle 202 Accepted Responses](https://github.com/modelcontextprotocol/python-sdk/issues/1661)
- [MCP Python SDK Issue #1144 — call_tool hangs when receiving invalid JSONRPCMessage](https://github.com/modelcontextprotocol/python-sdk/issues/1144)
- [MCP Streamable HTTP Spec](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)

---
name: Async Action Patterns — Upload / Download / Export
description: Two loading concepts in stores (withLoading vs. action flags), cd-button built-in async spinner, and Blob download pattern
type: project
originSessionId: 3bff5d6b-a565-4691-b7d9-ff321da9f1b9
---
Gelernt beim Studium von `data-source-files` als Vorbereitung auf das Audit-Log-Export-Feature.

**Why:** Verhindert falsche Verwendung von `withLoading()` für Button-Actions und falsches `[loading]`-Binding.

**How to apply:** Immer wenn ein async Button-Action (Upload, Download, Export) implementiert wird.

---

## Zwei getrennte Loading-Konzepte

| Konzept | Zustand | UI-Consumer | Wann |
|---------|---------|-------------|------|
| Seiten-Laden | `withLoading()` → `loading()` + `loadingError()` | `<cd-content-page [loading]>` | Initiales Laden der Seite |
| Aktion läuft | eigenes Flag z.B. `uploading`, `exporting` | Button-Callback / Zone-Komponente | Asynchrone Benutzeraktion |

---

## `cd-button` — kein `[loading]`-Input

`cd-button` hat `loading` als **internes Signal** (kein Input). Es wird automatisch durch `executeMaybeAsync` gesetzt, sobald `clickCallback` ein async Promise zurückgibt. Während das Promise pending ist: Button zeigt Spinner, ist disabled.

```html
<!-- Button verwaltet seinen Spinner selbst -->
<cd-button [clickCallback]="onExportClick" ...>Export</cd-button>
```

```typescript
readonly onExportClick = async (): Promise<void> => {
  await this.store.exportData(); // async → Button zeigt Spinner automatisch
};
```

---

## Wann explizites Action-Flag im Store

Nur wenn **mehrere UI-Elemente** auf dieselbe Aktion reagieren müssen (z.B. `UploadZoneComponent` zeigt anderen Text während Upload). Beispiel aus `data-source-files-detail.store.ts`:

```typescript
patchState(store, { uploading: true });
// ... API call ...
patchState(store, { uploading: false });
```

Für einfache Buttons (Download, Export) reicht der `async clickCallback` — kein Store-Flag nötig.

---

## Blob-Download Pattern

Für API-Endpoints die eine Datei zurückgeben (CSV, PDF, etc.):

```typescript
const blob = new Blob([response.data], { type: 'text/csv' });
const url = URL.createObjectURL(blob);
const anchor = document.createElement('a');
anchor.href = url;
anchor.download = 'filename.csv';
anchor.click();
URL.revokeObjectURL(url);
```

**Niemals** `window.open()` oder `window.location.href` — immer über den API-Client fetchen (Authentication Header werden mitgeschickt).

---

## Referenz-Implementierung

`libs/control-center/src/features/data-source-files/data-source-files-detail.store.ts` — `uploadFiles()` Methode als Template für async Actions mit explizitem State-Flag.

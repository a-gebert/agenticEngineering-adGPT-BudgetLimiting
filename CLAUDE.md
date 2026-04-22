# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Was ist dieses Repository?

Dies ist ein **Konfigurations-Satelliten-Repository** für die adessoGPT-Plattform. Es hält AI-Tooling-Konfigurationen (Settings, Hooks, Skills, Docs, Memory) aus dem Hauptprojekt heraus, um dessen Git-Verlauf sauber zu halten. Der eigentliche Quellcode liegt in:

```
/home/gebert/adgpt/PBI3270_Audit_Log/app/
```

## Startpunkt: claude.sh

```bash
cd /home/gebert/adgpt/PBI3270_Audit_Log/app/Backend
/home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/claude.sh <scope>
```

| Parameter | Wirkung |
|-----------|---------|
| `claude.sh budget-limiting` | Budget-Limiting Feature (PBI 3271) |
| `claude.sh audit-log` | Audit-Log Feature (PBI 3270) |
| `claude.sh --help` | Zeigt alle verfügbaren Scopes |

**Layer-Auswahl:** Der Layer (Backend/Frontend) wird automatisch aus `basename "$PWD"` abgeleitet. Aus `.../Backend` aufgerufen → Backend-Konfiguration, aus `.../Frontend` → Frontend-Konfiguration.

**Umgebungsvariablen:** Das Skript setzt `CLAUDE_CONFIG_DIR` (Scope+Layer-spezifisch) und `AGPT_ENGINEERING_DIR` (Repo-Root, für Hook-Pfade in settings.json).

## Verzeichnisstruktur

```
configs/
  _shared/              Gemeinsame Hooks, Skills, CLAUDE.md, policy-limits.json
    Backend/
    Frontend/
  budget-limiting/      Feature-Scope: PBI 3271
    Backend/            settings.json, worktree_guard.sh, docs/, plans/, projects/
    Frontend/           settings.json, projects/
  audit-log/            Feature-Scope: PBI 3270
    Backend/            settings.json, worktree_guard.sh, docs/, plans/, projects/
    Frontend/           settings.json, projects/
```

Scope-Verzeichnisse enthalten Symlinks auf `_shared/` für gemeinsame Ressourcen (Skills, policy-limits.json, CLAUDE.md).

## Konfiguration pro Layer

| Layer | Modell | Hooks |
|-------|--------|-------|
| Backend | Claude Opus | Worktree-Guard (PreToolUse), Architektur-Hook + CSharpier-Check (PostToolUse) |
| Frontend | Claude Sonnet | Angular-Architektur-Check (PostToolUse) |

### Hooks

- **Worktree-Guard** (`PreToolUse`): Verhindert Edits außerhalb des erwarteten Feature-Worktrees. Branch ist scope-spezifisch.
- **Architektur-Hook** (`PostToolUse`): Analysiert jede geänderte `.cs`-Datei gegen Clean-Architecture-Regeln. SEVERE-Verstöße werden sofort gefixt.
- **CSharpier-Check** (`PostToolUse`): Prüft C#-Formatierung nach jeder Dateiänderung.
- **Angular-Architektur-Check** (`PostToolUse`): Prüft Angular-Architekturregeln (Vertical Slices, signalStore, Components).

## Neuen Scope hinzufügen

1. `mkdir -p configs/<scope>/Backend/hooks configs/<scope>/Backend/docs configs/<scope>/Frontend`
2. `worktree_guard.sh` mit dem Feature-Branch-Namen erstellen
3. `settings.json` für Backend und Frontend erstellen (Hook-Pfade auf `$AGPT_ENGINEERING_DIR/configs/_shared/...`)
4. Symlinks: `ln -s ../../_shared/Backend/skills skills` usw.
5. Feature-Docs unter `docs/` ablegen

## Pflichtlektüre vor jeder Aufgabe

1. `/home/gebert/adgpt/PBI3270_Audit_Log/app/CLAUDE.md` — Autoritative Projekt-Instruktionen
2. `/home/gebert/adgpt/PBI3270_Audit_Log/app/CLAUDE-MEMORY.md` — Gesammelte Erkenntnisse
3. `/home/gebert/adgpt/PBI3270_Audit_Log/app/ai-docs/architecture.md` — Systemarchitektur

Zusätzlich je nach Layer:
- **Backend:** `ai-docs/backend.md`, `ai-docs/backend-testing.md`
- **Frontend:** `Frontend/adessoGPT.Web/CLAUDE.md`, `Frontend/adessoGPT.Web/CLAUDE.Styling.md`

## Entwicklungskommandos

### Backend (.NET 10)

```bash
dotnet build                                                    # Debug-Build
dotnet test                                                     # Alle Tests
dotnet test --filter "FullyQualifiedName~ClassName"              # Einzelner Testfilter
dotnet test --filter "Name=MethodName"                           # Nach Methodenname
dotnet csharpier format .                                        # Code formatieren
dotnet run --project Backend/Presentation/adessoGPT.Presentation.Api  # API starten
```

### Frontend (Angular 21 / Nx 22)

```bash
cd Frontend/adessoGPT.Web
npm install && npm run dev                                       # Dev-Server auf https://localhost:5174
npm run build && npm run lint && npm run prettier                # Quality Checks
npm run generate:api                                             # API-Client (Backend auf https://localhost:7039)
```

## Architektur-Überblick

### Backend — Clean Architecture

```
Presentation  →  Application  →  Infrastructure  →  Shared (Domain/Core)
(Minimal API)    (CQRS/MediatR)  (Azure/DB/SK)      (Entities/Abstractions)
```

CQRS + MediatR, Result<T> Monad, FluentValidation, Strongly-Typed IDs, Multi-Pod-Safe.

### Frontend — Angular + Nx

Standalone Components mit Signals, NgRx signalStore(), auto-generierter API-Client (@hey-api/openapi-ts), Angular Material + Tailwind CSS 4.

## Source Control

Hauptprojekt: **Azure DevOps** (kein `gh` CLI). Dieses Konfigurations-Repo: GitHub (`a-gebert/agenticEngineering-adGPT-BudgetLimiting`).

## Suchscope

Alle Dateisuchen müssen innerhalb von `/home/gebert/adgpt/PBI3270_Audit_Log/app/` bleiben.

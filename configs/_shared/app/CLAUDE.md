# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this configuration context.

This is the **app (root) layer**: work spans both the .NET backend and the Angular/React frontends from the repository root. Consult the backend- and frontend-specific instructions below as the task requires.

## Project Instructions

The authoritative project instructions are maintained in the repository at:

```
/home/gebert/adgpt/PBI3270_Audit_Log/app/CLAUDE.md
```

**Always read that file first** before starting any task. It contains naming conventions, required context files, coding principles, workflow rules, and backend/frontend-specific rules.

Also read at the start of every task:

```
/home/gebert/adgpt/PBI3270_Audit_Log/app/CLAUDE-MEMORY.md
```

## Supplements to the Project CLAUDE.md

The following are additions and corrections not yet reflected in the project CLAUDE.md.

### Working Directory & Search Scope

```
/home/gebert/adgpt/PBI3270_Audit_Log/app
```

All file searches must stay within `/home/gebert/adgpt/PBI3270_Audit_Log/app/`.

### Two Frontends Exist

The project has two frontend clients:

| Frontend | Path | Stack | Status |
|---|---|---|---|
| React (legacy) | `adessoGPT.UI/` | React 18 + Redux + Vite | Production |
| Angular (replacement) | `Frontend/adessoGPT.Web/` | Angular 21 + Nx + signals | Active migration |

The Angular frontend is a **1:1 replacement** of the React app. It has its own authoritative instructions at:

```
/home/gebert/adgpt/PBI3270_Audit_Log/app/Frontend/adessoGPT.Web/CLAUDE.md
/home/gebert/adgpt/PBI3270_Audit_Log/app/Frontend/adessoGPT.Web/CLAUDE.Styling.md
```

**Always read these files for Angular frontend tasks.** When implementing features in the Angular app, check the React app for existing business logic and UI designs to ensure feature parity.

**Angular API client generation** requires the backend running at `https://localhost:7039` (not `5522`):

```bash
cd Frontend/adessoGPT.Web
npm run generate:api
```

### Running a Single Test

**Backend** — filter by class or method name:

```bash
# By class name (partial match)
dotnet test --filter "FullyQualifiedName~GetConversationQueryHandlerTests"

# By method name
dotnet test --filter "Name=WhenConversationExists_ReturnsConversation"

# By project
dotnet test Backend/Tests/adessoGPT.Application.Tests
```

**React frontend** — filter by file or test name:

```bash
cd adessoGPT.UI

# Run a specific test file
npm run test -- ConversationList.test.tsx

# Run tests matching a name pattern
npm run test -- --testNamePattern="renders conversation"
```

### Corrected Build Command

The project CLAUDE.md shows `dotnet build --configuration Release`. For day-to-day development, use the default (Debug) configuration:

```bash
dotnet build
```

Use `--configuration Release` only when verifying a production build.

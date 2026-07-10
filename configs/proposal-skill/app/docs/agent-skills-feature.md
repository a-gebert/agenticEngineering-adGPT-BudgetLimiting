# Agent Skills — Feature-Zusammenfassung

**Branch:** `feat/agent-skills` (gegenüber `dev`)
**Herkunft:** PBI #3414 · Feature #3412 · Epic #3281
**Status:** Vollständig im Branch vorhanden, aber hinter dem **`Skills`-Feature-Flag (Default AUS)** — auf `dev` existiert nichts davon (dark-shipped).

## Kernidee

Anthropic-artige **Agent Skills** — wiederverwendbare, **vom Modell selbst aufgerufene**
Instruktionspakete, die einen Agenten für eine Aufgabe spezialisieren. Direktes Geschwister der
bestehenden *Dynamic Tool Discovery*: dasselbe „Progressive-Disclosure"-Muster, nur für
**Instruktionen** statt für **Tools**. Kein Code-Execution-VM nötig — alles ist Text, der bei
Bedarf in den Kontext gestreamt wird.

### Progressive Disclosure (3 Ebenen)

| Ebene | Inhalt | Wann geladen |
|-------|--------|--------------|
| **Level 1** | Nur `name` + `description` (Katalog-Manifest) | Immer im System-Prompt, wenn Kandidaten existieren |
| **Level 2** | Voller `Body` (die eigentlichen Instruktionen) | Wenn das Modell `load_skill(name)` aufruft |
| **Level 3** | Gebündelte Ressourcen / Skripte | On demand via `read_skill_resource` / `run_skill_script` |

→ Eine Skill kostet fast nichts, bis sie tatsächlich gebraucht wird.

## Laufzeit (Backend)

1. **Meta-Tools** — ein Core-Feature `skill_search` (`SkillDiscoveryPlugin`) mit vier Tools:
   `search_skills`, `load_skill`, `read_skill_resource`, `run_skill_script`. Rein
   infrastrukturell, in jeder User-Feature-Liste versteckt.
2. **Kandidaten-Auflösung** (pro Konversation, in `CreateChatStreamContextQueryHandler`):
   ```
   Kandidaten = globale Skills ∪ agent-eigene (agent.SupportedSkillIds)
              ∪ persönliche Skills des Users (auf diesen Agent zugewiesen)
   ```
   **Smarte Restriktion:** Ein Kandidat wird verworfen, wenn nicht alle seine `RequiredFeatureIds`
   in den erlaubten Features des Users für diesen Agenten sind — verborgene Skills werden nie
   beworben. Kein eigenes User-Group-Feld; Sichtbarkeit wird von den verknüpften Features/MCP geerbt.
3. **Suche** — nutzt den vorhandenen BM25-Sucher (`Bm25DeferredToolSearch`) wieder, keine zweite
   Implementierung.
4. **Registry** — `ISkillRegistry`, **eine Instanz pro Stream**, in beiden Runtime-Factories
   gebrückt (AgentFramework **und** Realtime).

## Scopes, Ownership, Versionierung

- **Scopes:** global (jeder Agent) · pro-Agent · persönlich (user-eigene Skills, Agenten zugewiesen
  über `UserSettings.PersonalSkillAssignments`).
- **Ownership** hängt an der **Flag-Variante:** `AdminOnly` (Default) → nur Admins/AgentEditor
  pflegen globale/agent-Skills und verdrahten Features; `Everyone` → normale User dürfen zusätzlich
  **persönliche** Skills anlegen (Feature-Verdrahtung bleibt admin-only).
- Zentraler Enforcement-Punkt: `ISkillAuthoringResolver` — jeder Schreibpfad läuft darüber.
- **Versionierung:** Bei Update wird der alte Stand in `Skill.Versions` gesnapshottet;
  `POST /skills/{id}/restore/{version}` spielt zurück (Snapshot-first, also selbst rückgängig
  machbar). Ressourcen werden nicht versioniert.

## Verknüpfte Features / MCP + Skripte

- `RequiredFeatureIds` einer Skill (Features/MCP-Server) **aktivieren sich**, sobald die Skill
  Kandidat ist — das ist die „Verknüpfung mit MCP/Features".
- **Skripte** laufen nur, wenn ein Admin `CodeInterpreterFeatureId` konfiguriert hat *und* dieses
  MCP-Feature für den User aktiv ist — sonst klare „Code execution is not available"-Meldung
  (kein Throw).

## Frontend-Oberfläche

- **Control-Center:** Skills-Verwaltung (Liste, ZIP-Import/Export, CRUD + Restore, KI-Autoring-
  Helfer `/assist`) und eine Admin-Settings-Seite.
- **„My Skills":** user-eigene Seite unter `/my-skills` (nur bei Variante `Everyone`), erreichbar
  über das Avatar-Menü.
- **Agent-Upsert:** Skills-Multiselect im „Models & Data"-Tab.
- **Chat:**
  - **`/`-Slash-Picker** zum manuellen Erzwingen einer Skill (Geschwister des `@`-Mention-Pickers)
    — fügt ein `/skill-name`-Token ein; das Token wird beim Senden aus dem Text gestrippt, die
    Skill via `forcedSkillName` übergeben.
  - **Inline-Highlight-Overlay** zeichnet farbige Pills hinter dem Textarea für `/skill`- und
    `@`-Tokens.
  - **Aktiv-Skill-Indikator:** dezentes Buch-Icon (`mgc_book_6_line`) in der Message-Actionbar,
    wenn `loadedSkillNames` gefüllt ist; live während des Streamings über das `skill_loaded`-SSE-Event.

## API-Oberfläche (Auszug)

- `/api/control-center/skills` — CRUD + Restore, ZIP-Import/Export, `/assist`
  (`RequireRole(AgentEditor)` + `WithApplicationFeatureGate(Skills)`).
- `/api/control-center/skills-settings` — Admin-Settings (`ControlCenterAdmin`).
- `/api/skills/personal-assignments` — User weist persönliche Skills Agenten zu (nur Variante `Everyone`).
- `GET /api/skills/available?agentId={id}` — Kandidaten-Skills für den `/`-Picker im Composer.

## Noch NICHT gebaut (separat getrackt)

**Advanced Skills Sharing** (PBI #5735): echter user-group-geteilter Scope
(`AllowedUserGroupIds` auf der Skill). Aktuell wird Sichtbarkeit nur über die required Features/MCP
gegated.

## Referenzen im Hauptprojekt

- Backend-Rule: `app/Backend/.claude/rules/skills.md`
- Frontend-Rule: `app/Frontend/adessoGPT.Web/.claude/rules/skills-feature.md`
- Interne Doku: `app/docs/internal/content/skills/index.md`
- Public Doku: `app/docs/public/content/overview/skills.md`

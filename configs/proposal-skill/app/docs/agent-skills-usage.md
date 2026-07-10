# Agent Skills — Doku zur Verwendung

Praktische Anleitung, wie Agent Skills genutzt werden — für Admins (Anlegen/Pflegen) und für
Endanwender (Aufrufen im Chat). Feature-Überblick: siehe `agent-skills-feature.md`.

> **Voraussetzung:** Das `Skills`-Feature-Flag muss aktiv sein (Default AUS). Die Flag-**Variante**
> steuert, wer Skills anlegen darf:
> - **`AdminOnly`** (Default) — nur Admins / `AgentEditor` pflegen globale & agent-Skills.
> - **`Everyone`** — zusätzlich dürfen normale User **persönliche** Skills anlegen.

---

## 1. Skills anlegen & pflegen (Admin, Control-Center)

**Wo:** Control-Center → Agent-Management → **Skills**.

- **Neu anlegen / bearbeiten:** Tabs
  1. **Identity** — Name, Titel, Beschreibung (der Name + die Beschreibung landen als Level-1-Katalog
     im System-Prompt; kurz und aussagekräftig halten).
  2. **Instructions** — der `Body` (Level 2): die eigentlichen Anweisungen, die das Modell bei
     `load_skill` erhält.
  3. **Linked capabilities** *(nur Admin)* — required Features / MCP-Server verknüpfen. Diese werden
     aktiviert, sobald die Skill Kandidat ist, und dienen zugleich als Sichtbarkeits-Gate.
  4. **Resources** — zusätzliche Dateien (Level 3), optional als **Skript** markiert.
  5. **Access** — Scope: global (jeder Agent) oder per-Agent.
- **KI-Autoring-Helfer:** Button „Assist" (`/assist`) generiert einen Entwurf aus einem Prompt.
- **Import/Export:** ZIP-Import (`SKILL.md` mit YAML-Frontmatter + Geschwisterdateien → Ressourcen;
  Secrets/zu große Dateien werden abgelehnt) und per-Zeile-Export als ZIP.
- **Versionierung:** Jede Änderung snapshottet den alten Stand; über „Restore" lässt sich eine
  frühere Version zurückholen (der aktuelle Stand wird dabei zuerst gesnapshottet → jederzeit
  umkehrbar). Ressourcen werden nicht versioniert.

**Skill einem Agenten zuordnen:** Agent-Upsert → Tab **Models & Data** → Multiselect **Skills**
(nur sichtbar bei aktivem Flag).

**Skill-Settings (Admin):** Control-Center → Administration → **Skills-Settings**:
`CodeInterpreterFeatureId`, `SearchResultLimit` (10), `InjectCatalogManifest` (an),
`MaxBodyCharacters` (50000), `MaxResourceCharacters` (100000).

---

## 2. Persönliche Skills (Endanwender, nur Variante `Everyone`)

**Wo:** Avatar-Menü → **My Skills** (`/my-skills`).

- Eigene Skills anlegen/bearbeiten (wie oben, aber ohne Feature-Verdrahtung — die bleibt admin-only;
  `IsGlobal` ist fix aus).
- Pro Skill festlegen, **welchen Agenten** sie zugewiesen wird (Multiselect).

---

## 3. Skills im Chat nutzen (Endanwender)

Es gibt zwei Wege, wie eine Skill zum Einsatz kommt:

**a) Automatisch (modell-getrieben).** Sind für den gewählten Agenten Skills verfügbar, stehen
Name + Beschreibung im System-Prompt. Das Modell entscheidet selbst, ob es eine Skill via
`search_skills` / `load_skill` nachlädt — der Anwender muss nichts tun.

**b) Manuell erzwingen — der `/`-Slash-Picker.**
1. Im Chat-Eingabefeld `/` am Wortanfang tippen → Picker öffnet sich (Geschwister des `@`-Pickers).
2. Skill wählen → ein `/skill-name`-Token wird eingefügt (farblich hinterlegt).
3. Beim Senden wird das Token aus dem Text entfernt; die Skill wird erzwungen geladen und ihr `Body`
   sofort in den Prompt injiziert (ohne Umweg über die Suche).
4. Token wieder löschen = Skill nicht mehr erzwungen.

**Aktiv-Skill-Indikator:** Wurde in einer Antwort eine Skill geladen, erscheint in der Message-
Actionbar ein dezentes Buch-Icon; der Tooltip listet die Skill-Namen, ein Klick öffnet den
Message-Info-Dialog („Skills used"). Während des Streamings zeigt eine Inline-Zeile live an, welche
Skills geladen wurden.

---

## 4. Sichtbarkeits-Regeln (wichtig zu wissen)

- Eine Skill wird einem Anwender **nur angeboten, wenn er alle ihre required Features/MCP nutzen
  darf**. Fehlt eine Berechtigung, ist die Skill für ihn unsichtbar (kein User-Group-Feld an der
  Skill selbst — die Sichtbarkeit erbt sich von den verknüpften Features/MCP).
- **Skripte** laufen nur, wenn ein Admin `CodeInterpreterFeatureId` gesetzt hat und das zugehörige
  MCP-Feature für den Anwender aktiv ist — sonst kommt eine klare „Code execution is not
  available"-Meldung.

---

## Referenzen (Hauptprojekt)

- Backend-Rule: `app/Backend/.claude/rules/skills.md`
- Frontend-Rule: `app/Frontend/adessoGPT.Web/.claude/rules/skills-feature.md`
- Interne Doku: `app/docs/internal/content/skills/index.md`
- Public Doku: `app/docs/public/content/overview/skills.md`

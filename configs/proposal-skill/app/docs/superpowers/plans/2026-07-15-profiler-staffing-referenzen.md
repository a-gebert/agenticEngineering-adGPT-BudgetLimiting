# Profiler-Integration (Staffing + Referenzen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zwei neue Kettenschritte (`StaffingCatalog`, `ProfilerMatch`) in Phase `Solution` bringen reale, anonymisierte adesso-Profile und Referenzprojekte aus dem Profiler-MCP ins Angebot und ersetzen die erfundenen Team-/Profil-/Referenz-Passagen in `proposal.md` (Gap G2).

**Architecture:** Deterministisches Katalog-→-Tool-Muster analog `SolutionCatalog → SolutionProposal`. `StaffingCatalog` leitet aus Lösungsvorschlag + Anforderungen die benötigten Rollen/Skills und Referenz-Such-Briefs ab (kein externes Wissen, schema-validiert). `ProfilerMatch` ruft als einziger Schritt den Profiler-MCP auf, matcht real, anonymisiert und schreibt ein schema-validiertes Artefakt, das `proposal.md` (Kap. 2.5 + Annex A) konsumiert.

**Tech Stack:** JSON Schema (Draft 2020-12), Markdown-Prompts, `plan.json`-Chain-Definition, `validate_json.py` (Python-3-stdlib-Validator), Code Interpreter (Laufzeit-Validierung in den Skills), Profiler-MCP.

## Global Constraints

- Schema-Dialekt: `"$schema": "https://json-schema.org/draft/2020-12/schema"`, `additionalProperties: false` auf jedem Objekt, `$id`, `title`, `description` gesetzt — exakt wie `schema/solution_catalog.json`.
- Alle menschlich lesbaren Feldwerte (`title`, `description`, `note`, `scope`, `relevance`, `message`, …) in `output_language`; Default `de` für die Solution-/Proposal-Ausgabe.
- **Anonymisiert / rollenbasiert** im kundengerichteten Output: keine Klarnamen von Personen, keine Kundenklarnamen bei Referenzen. Standort/Verfügbarkeit nur zum Matching, nie im Angebotstext.
- **Kein Erfinden:** Fehlt ein Treffer, `matched: false` + Platzhalter/Hinweis — niemals fabrizieren.
- Profiler-MCP-Aufruf ausschließlich im Schritt `ProfilerMatch`; sonst nirgends in der Chain.
- ID-Formate: Rollen `R-01`, Referenz-Briefs `REF-01`, Referenzen `REF-01` (im Match-Ergebnis 1:1 aus dem Brief übernommen).
- Seniority-Enum überall identisch: `["junior", "regular", "senior", "lead"]`.
- Prompt-Aufbau folgt dem bestehenden Muster (`solution_catalog.md`): Abschnitte `Context / Role / Emotion-Tone / Action / Output & Validation (Code Interpreter) / Tweak`.
- Skill-Namen (Kebab, Präfix `proposal-`): `proposal-staffing-catalog`, `proposal-profiler-match`.
- Repo-Root für Kommandos: `/home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app`. Validator: `validate_json.py` in diesem Root. Schema-Pfade absolut angeben.
- Design-Spec: `docs/superpowers/specs/2026-07-15-profiler-staffing-referenzen-design.md`.

---

## File Structure

- Create: `docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json` — Schema Schritt A1.
- Create: `docs/.adesso/skills/proposalgenerator/schema/profiler_match.json` — Schema Schritt A2.
- Create: `docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json` — valide Beispielinstanz (Fixture/Test A1).
- Create: `docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json` — valide Beispielinstanz (Fixture/Test A2).
- Create: `docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md` — Prompt A1.
- Create: `docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md` — Prompt A2.
- Modify: `docs/.adesso/skills/proposalgenerator/plan.json` — Solution-Array um 2 Schritte, `Proposal.batch` erweitern.
- Modify: `docs/.adesso/skills/proposalgenerator/AGENT.md` — Workflow/Chain, Dependency Rule, Profiler-MCP-Tool-Restriktion, HITL-Gate.
- Modify: `docs/.adesso/skills/proposalgenerator/prompts/proposal.md` — Kap. 2.5 + Annex A auf Artefakt-Konsum umstellen (G2-Cleanup).

Reihenfolge: erst Schemata (mit Fixtures), dann Prompts, dann Verdrahtung (`plan.json`, `AGENT.md`), zuletzt `proposal.md`. Jede Task endet mit einem eigenständig prüfbaren Deliverable und einem Commit.

---

### Task 1: Schema `staffing_catalog.json` (+ Fixture)

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json`
- Create: `docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json`

**Interfaces:**
- Produces: Schema `StaffingCatalog` mit Top-Level `roles[]`, `reference_briefs[]`, optional `document_id`, `errors[]`. Downstream (`profiler_match.md`, `proposal.md`) liest `roles[].{role_id,title,seniority,required_skills,addressed_requirements,profiler_query}` und `reference_briefs[].{brief_id,domain,technologies,search_skills,relevance_rationale}`.

- [ ] **Step 1: Beispielinstanz (Test) schreiben**

Create `docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json`:

```json
{
  "document_id": "TENDER-2025-POS",
  "roles": [
    {
      "role_id": "R-01",
      "title": "Integrationsarchitekt:in",
      "seniority": "senior",
      "required_skills": ["Azure Integration Services", "Event-Driven Architecture", "REST/OpenAPI"],
      "rationale": "Leitet sich aus den Integrationsanforderungen FR-001/FR-004 und dem Lösungsbaustein Systemintegration ab.",
      "addressed_requirements": ["FR-001", "FR-004", "NFR-002"],
      "profiler_query": {
        "skills": ["Azure Integration Services", "Event-Driven Architecture"],
        "location": "DACH",
        "availability": "ab Q4 2025"
      }
    },
    {
      "role_id": "R-02",
      "title": "Projektleiter:in",
      "seniority": "lead",
      "required_skills": ["Projektleitung", "Hybrides Vorgehen"],
      "rationale": "Erforderlich für Steuerung und Governance gemäß organisatorischen Rahmenbedingungen.",
      "addressed_requirements": ["FR-001"],
      "profiler_query": {
        "skills": ["Projektleitung"]
      }
    }
  ],
  "reference_briefs": [
    {
      "brief_id": "REF-01",
      "domain": "Retail / POS-Modernisierung",
      "technologies": ["Cloud-Migration", "Offline-Sync"],
      "search_skills": ["POS", "Offline-First", "Cloud-Migration"],
      "relevance_rationale": "Vergleichbare POS-Modernisierung im Handel mit Offline-Fähigkeit."
    }
  ],
  "errors": []
}
```

- [ ] **Step 2: Validierung gegen (noch fehlendes) Schema — muss fehlschlagen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 validate_json.py "$PWD/docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json" \
  --instance-file "$PWD/docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json"; echo "exit=$?"
```
Expected: `Schema file not found: ...` auf stderr, `exit=2` (Schema existiert noch nicht).

- [ ] **Step 3: Schema schreiben**

Create `docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/schemas/staffing-catalog.schema.json",
    "title": "StaffingCatalog",
    "description": "Deterministic catalogue of the roles/skills a proposal needs plus reference-search briefs, derived from the solution proposal, requirements and constraints. Bridges requirements to the Profiler match step. No external knowledge, no Profiler calls.",
    "type": "object",
    "additionalProperties": false,
    "properties": {
        "document_id": { "type": "string", "description": "Optional ID of the source document." },
        "roles": {
            "type": "array",
            "description": "Roles required to staff the proposed solution.",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "role_id": { "type": "string", "description": "Unique role ID (e.g. R-01)." },
                    "title": { "type": "string", "description": "Role title, in output_language." },
                    "seniority": {
                        "type": "string",
                        "enum": ["junior", "regular", "senior", "lead"],
                        "description": "Required seniority level."
                    },
                    "required_skills": {
                        "type": "array",
                        "description": "Skills the role must cover.",
                        "items": { "type": "string" },
                        "minItems": 1
                    },
                    "rationale": { "type": "string", "description": "Why this role is needed, traced to requirements/solution, in output_language." },
                    "addressed_requirements": {
                        "type": "array",
                        "description": "FR/NFR IDs this role helps deliver.",
                        "items": { "type": "string" },
                        "minItems": 1
                    },
                    "profiler_query": {
                        "type": "object",
                        "additionalProperties": false,
                        "description": "Search brief for the Profiler MCP (used only for matching, never rendered in the proposal).",
                        "properties": {
                            "skills": { "type": "array", "items": { "type": "string" }, "minItems": 1, "description": "Skills to search for." },
                            "location": { "type": "string", "description": "Optional location filter (from constraints.organisational)." },
                            "availability": { "type": "string", "description": "Optional availability filter (from constraints.timeline)." }
                        },
                        "required": ["skills"]
                    }
                },
                "required": ["role_id", "title", "seniority", "required_skills", "addressed_requirements", "profiler_query"]
            }
        },
        "reference_briefs": {
            "type": "array",
            "description": "Search briefs to surface comparable past projects via colleagues' project experience (double purpose). May be empty if no relevant domain is derivable.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "brief_id": { "type": "string", "description": "Unique brief ID (e.g. REF-01)." },
                    "domain": { "type": "string", "description": "Domain/industry to search comparable projects in, in output_language." },
                    "technologies": { "type": "array", "items": { "type": "string" }, "description": "Relevant technologies for comparability." },
                    "search_skills": {
                        "type": "array",
                        "description": "Skills through which comparable project experience is found in profiles.",
                        "items": { "type": "string" },
                        "minItems": 1
                    },
                    "relevance_rationale": { "type": "string", "description": "Why such a reference is relevant, in output_language." }
                },
                "required": ["brief_id", "domain", "search_skills", "relevance_rationale"]
            }
        },
        "errors": {
            "type": "array",
            "description": "Error block for validation or processing errors.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "code": { "type": "string" },
                    "message": { "type": "string" },
                    "severity": { "type": "string", "enum": ["info", "warning", "error"] },
                    "reference": {
                        "type": "object",
                        "additionalProperties": false,
                        "properties": {
                            "role_id": { "type": "string" },
                            "brief_id": { "type": "string" }
                        }
                    }
                },
                "required": ["code", "message"]
            }
        }
    },
    "required": ["roles", "reference_briefs"]
}
```

- [ ] **Step 4: Validierung — muss bestehen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 validate_json.py "$PWD/docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json" \
  --instance-file "$PWD/docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json"; echo "exit=$?"
```
Expected: `VALID: the JSON object conforms to the schema.`, `exit=0`.

- [ ] **Step 5: Negativprobe — Pflichtfeld entfernen, muss fehlschlagen**

Run (entfernt `title` aus der ersten Rolle in-memory):
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 -c "import json,sys; d=json.load(open('docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json')); d['roles'][0].pop('title'); print(json.dumps(d))" \
  | python3 validate_json.py "$PWD/docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json"; echo "exit=$?"
```
Expected: `INVALID: 1 error(s) found.` mit `missing required property 'title'`, `exit=1`.

- [ ] **Step 6: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/schema/staffing_catalog.json docs/.adesso/skills/proposalgenerator/schema/examples/staffing_catalog.example.json
git commit -m "ENH proposalgenerator: add staffing_catalog JSON schema"
```

---

### Task 2: Prompt `staffing_catalog.md`

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md`

**Interfaces:**
- Consumes (Laufzeit-Inputs): `SolutionProposalResult.md`, `FunctionalResult.json`, `ConstraintsResult.json`.
- Produces: Anweisung, `StaffingCatalogResult.json` (konform zu `staffing_catalog.json`) via Code Interpreter zu erzeugen.

- [ ] **Step 1: Prompt schreiben**

Create `docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md`:

```markdown
Context:
You receive the schema-validated artifacts of the preceding chain steps as input files. Read every field directly from them — do NOT retrieve the tender document and do NOT use external/general knowledge in this step. Do NOT call the Profiler in this step (that happens in the downstream ProfilerMatch step).

- `SolutionProposalResult.md` — the single, consolidated solution proposal (target architecture, recommended technologies per solution block).
- `FunctionalResult.json` — functional (`functional_requirements[]`) and non-functional (`non_functional_requirements[]`) requirements plus `aspects[]`. Conforms to `functional_requirements.json`.
- `ConstraintsResult.json` — `constraints.timeline` (`go_live`, `key_milestones`), `constraints.organisational[]`, `constraints.technical[]`. Conforms to `constraints.json`.

Your task is to derive a **staffing catalogue**: (1) the roles and skills needed to deliver the proposed solution, each with a concrete Profiler search brief, and (2) reference-search briefs that let the downstream step surface comparable past projects via colleagues' project experience. This step is a deterministic bridge — it names role NEEDS and search criteria, never concrete persons or projects.

All labels, titles, descriptions, and messages in your output must be written in the language specified by the `output_language` parameter. If `output_language` is not provided, default to German.

Role:
Act as an experienced staffing lead / delivery manager who translates a target architecture and requirement set into the concrete role mix an IT consulting project needs. You justify every role from the requirements/solution and scope precise search criteria; you never invent people.

Emotion/Tone:
Neutral, systematic, exact. Prioritise correctness over completeness — only derive roles the solution/requirements actually support.

Action:
Produce a JSON object conforming to `staffing_catalog.json` with the following structure:

1. **roles**: One entry per role required to staff the proposed solution. For each role:
   - `role_id`: unique ID in the format `"R-01"`, `"R-02"`, ...
   - `title`: role title, in `output_language`.
   - `seniority`: one of `"junior"`, `"regular"`, `"senior"`, `"lead"`.
   - `required_skills`: the skills the role must cover, derived from the solution's technologies and the requirements.
   - `rationale`: one to two sentences why this role is needed, traced to requirements/solution, in `output_language`.
   - `addressed_requirements`: the FR/NFR IDs this role helps deliver (from `FunctionalResult.json`).
   - `profiler_query`: the search brief for the Profiler MCP — `skills` (required), optional `location` (derive from `constraints.organisational`, e.g. on-site/language/location rules), optional `availability` (derive from `constraints.timeline`). These fields are used only for matching downstream and must never appear in the client-facing proposal.

2. **reference_briefs**: Search briefs to surface comparable past projects (double purpose). For each brief:
   - `brief_id`: unique ID in the format `"REF-01"`, ...
   - `domain`: the domain/industry to look for comparable projects in (derive from client context/solution), in `output_language`.
   - `technologies`: relevant technologies for comparability.
   - `search_skills`: skills through which comparable project experience is found in profiles.
   - `relevance_rationale`: why such a reference is relevant to this bid, in `output_language`.
   If no relevant domain is derivable, return an empty array.

3. **errors**: report structural problems (e.g. no requirements/solution in input) using `code`, `message` (in `output_language`), optional `severity` and `reference.role_id`/`reference.brief_id`. Empty array if none.

4. **document_id**: copy from an input `document_id` if present, otherwise omit.

Output & Validation (Code Interpreter):
Produce the final result as a schema-validated file using the Code Interpreter — do NOT return the JSON inline in the chat.

1. Draft the catalogue JSON in memory following all field rules above.
2. Use the Code Interpreter to load the JSON Schema from `staffing_catalog.json` and validate your draft with the `jsonschema` library (draft 2020-12).
3. If validation fails, inspect the violations, correct the draft, and re-validate. Repeat until it validates cleanly.
4. If a violation cannot be resolved from the input content, add an `errors` entry with `code: "SCHEMA_VALIDATION_FAILED"`, `severity: "error"`, and a `message` in `output_language`, then keep the object otherwise schema-conformant.
5. Write the final validated object to a file named `StaffingCatalogResult.json` (UTF-8, pretty-printed) and upload it back into the context so downstream steps can consume it.

Tweak:
- Use `output_language` for all `title`, `rationale`, `domain`, `relevance_rationale`, and `message` values.
- Every role must trace to at least one requirement via `addressed_requirements`; do NOT invent roles unsupported by the solution/requirements.
- Do NOT name concrete persons, CVs, vendors, or concrete past projects anywhere — only role needs and search criteria.
- `profiler_query.skills` must be non-empty for every role.
- Keep the role set lean and realistic for the solution's scope — no speculative roles.
- The authoritative deliverable is `StaffingCatalogResult.json`, validated against `staffing_catalog.json`. The file content must be valid JSON only — no markdown fences, no commentary.
```

- [ ] **Step 2: Struktur-Verifikation**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
grep -cE '^(Context:|Role:|Emotion/Tone:|Action:|Output & Validation \(Code Interpreter\):|Tweak:)' docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md
grep -c 'StaffingCatalogResult.json' docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md
grep -ci 'Profiler' docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md
```
Expected: erste Zeile `6` (alle sechs Abschnitte vorhanden), zweite `>=2`, dritte `>=1` (Profiler-Bezug für die Query-Briefs).

- [ ] **Step 3: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/prompts/staffing_catalog.md
git commit -m "ENH proposalgenerator: add staffing_catalog prompt"
```

---

### Task 3: Schema `profiler_match.json` (+ Fixture)

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/schema/profiler_match.json`
- Create: `docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json`

**Interfaces:**
- Consumes: konzeptuell `StaffingCatalogResult.json` (`role_id`, `brief_id`).
- Produces: Schema `ProfilerMatch` mit Top-Level `team[]`, `references[]`, `coverage`, optional `document_id`, `errors[]`. Downstream (`proposal.md`) liest `team[].{role_id,role_title,seniority,skills,certifications,years_experience,allocation_pct,matched,note}` und `references[].{reference_id,industry,scope,duration,relevance,matched}`.

- [ ] **Step 1: Beispielinstanz (Test) schreiben**

Create `docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json`:

```json
{
  "document_id": "TENDER-2025-POS",
  "team": [
    {
      "role_id": "R-01",
      "role_title": "Integrationsarchitekt:in",
      "seniority": "senior",
      "skills": ["Azure Integration Services", "Event-Driven Architecture", "REST/OpenAPI"],
      "certifications": ["Azure Solutions Architect Expert"],
      "years_experience": 12,
      "allocation_pct": 60,
      "matched": true,
      "note": ""
    },
    {
      "role_id": "R-02",
      "role_title": "Projektleiter:in",
      "seniority": "lead",
      "skills": ["Projektleitung", "Hybrides Vorgehen"],
      "certifications": [],
      "years_experience": 0,
      "allocation_pct": 40,
      "matched": false,
      "note": "Kein passendes Profil im Profiler gefunden — bitte im Profiler recherchieren."
    }
  ],
  "references": [
    {
      "reference_id": "REF-01",
      "industry": "Handel",
      "scope": "Modernisierung einer Kassenlösung mit Offline-Fähigkeit und Cloud-Anbindung.",
      "duration": "8 Monate",
      "relevance": "Vergleichbare POS-Modernisierung mit denselben Integrationsherausforderungen.",
      "matched": true
    }
  ],
  "coverage": {
    "roles_total": 2,
    "roles_matched": 1,
    "references_total": 1,
    "references_matched": 1
  },
  "errors": []
}
```

- [ ] **Step 2: Validierung gegen (noch fehlendes) Schema — muss fehlschlagen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 validate_json.py "$PWD/docs/.adesso/skills/proposalgenerator/schema/profiler_match.json" \
  --instance-file "$PWD/docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json"; echo "exit=$?"
```
Expected: `Schema file not found: ...`, `exit=2`.

- [ ] **Step 3: Schema schreiben**

Create `docs/.adesso/skills/proposalgenerator/schema/profiler_match.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/schemas/profiler-match.schema.json",
    "title": "ProfilerMatch",
    "description": "Anonymised, role-based team profiles and anonymised reference projects matched from the adesso Profiler MCP against the staffing catalogue. Feeds proposal chapters 2.5 and Annex A. No client-facing person names, no client names on references.",
    "type": "object",
    "additionalProperties": false,
    "properties": {
        "document_id": { "type": "string", "description": "Optional ID of the source document." },
        "team": {
            "type": "array",
            "description": "One entry per role from the staffing catalogue, filled from real Profiler hits (anonymised) or flagged as unmatched.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "role_id": { "type": "string", "description": "Role ID from the staffing catalogue (e.g. R-01)." },
                    "role_title": { "type": "string", "description": "Role title, in output_language." },
                    "seniority": { "type": "string", "enum": ["junior", "regular", "senior", "lead"] },
                    "skills": { "type": "array", "items": { "type": "string" }, "description": "Anonymised skills of the matched profile.", "minItems": 1 },
                    "certifications": { "type": "array", "items": { "type": "string" }, "description": "Relevant certifications (may be empty)." },
                    "years_experience": { "type": "integer", "minimum": 0, "description": "Years of relevant experience; 0 when unmatched." },
                    "allocation_pct": { "type": "integer", "minimum": 0, "maximum": 100, "description": "Optional planned allocation in percent." },
                    "matched": { "type": "boolean", "description": "True if a real profile was matched; false means placeholder." },
                    "note": { "type": "string", "description": "Optional note; for unmatched entries the placeholder/hint text, in output_language." }
                },
                "required": ["role_id", "role_title", "seniority", "skills", "matched"]
            }
        },
        "references": {
            "type": "array",
            "description": "Anonymised reference projects derived from colleagues' project experience. No client names.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "reference_id": { "type": "string", "description": "Reference ID, carried over from the brief (e.g. REF-01)." },
                    "industry": { "type": "string", "description": "Industry/sector of the reference, in output_language." },
                    "scope": { "type": "string", "description": "Anonymised scope description, in output_language." },
                    "duration": { "type": "string", "description": "Approximate duration (e.g. '8 Monate')." },
                    "relevance": { "type": "string", "description": "Why comparable to this bid, in output_language." },
                    "matched": { "type": "boolean", "description": "True if backed by real project experience; false means placeholder." }
                },
                "required": ["reference_id", "industry", "scope", "relevance", "matched"]
            }
        },
        "coverage": {
            "type": "object",
            "additionalProperties": false,
            "description": "Match statistics.",
            "properties": {
                "roles_total": { "type": "integer", "minimum": 0 },
                "roles_matched": { "type": "integer", "minimum": 0 },
                "references_total": { "type": "integer", "minimum": 0 },
                "references_matched": { "type": "integer", "minimum": 0 }
            },
            "required": ["roles_total", "roles_matched", "references_total", "references_matched"]
        },
        "errors": {
            "type": "array",
            "description": "Error block for validation or processing errors.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "code": { "type": "string" },
                    "message": { "type": "string" },
                    "severity": { "type": "string", "enum": ["info", "warning", "error"] },
                    "reference": {
                        "type": "object",
                        "additionalProperties": false,
                        "properties": {
                            "role_id": { "type": "string" },
                            "reference_id": { "type": "string" }
                        }
                    }
                },
                "required": ["code", "message"]
            }
        }
    },
    "required": ["team", "references", "coverage"]
}
```

- [ ] **Step 4: Validierung — muss bestehen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 validate_json.py "$PWD/docs/.adesso/skills/proposalgenerator/schema/profiler_match.json" \
  --instance-file "$PWD/docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json"; echo "exit=$?"
```
Expected: `VALID: the JSON object conforms to the schema.`, `exit=0`.

- [ ] **Step 5: Negativprobe — allocation_pct über Maximum, muss fehlschlagen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 -c "import json; d=json.load(open('docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json')); d['team'][0]['allocation_pct']=150; print(json.dumps(d))" \
  | python3 validate_json.py "$PWD/docs/.adesso/skills/proposalgenerator/schema/profiler_match.json"; echo "exit=$?"
```
Expected: `INVALID: 1 error(s) found.` mit `greater than maximum 100`, `exit=1`.

- [ ] **Step 6: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/schema/profiler_match.json docs/.adesso/skills/proposalgenerator/schema/examples/profiler_match.example.json
git commit -m "ENH proposalgenerator: add profiler_match JSON schema"
```

---

### Task 4: Prompt `profiler_match.md`

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md`

**Interfaces:**
- Consumes: `StaffingCatalogResult.json`; Profiler-MCP als externes Tool.
- Produces: Anweisung, `ProfilerMatchResult.json` (konform zu `profiler_match.json`) via Code Interpreter zu erzeugen; mandatory HITL-Gate; Anonymisierung; Fallback ohne Erfinden.

- [ ] **Step 1: Prompt schreiben**

Create `docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md`:

```markdown
Context:
You receive `StaffingCatalogResult.json` (conforming to `staffing_catalog.json`) as your main input. It contains `roles[]` (each with `role_id`, `title`, `seniority`, `required_skills`, `addressed_requirements`, `profiler_query`) and `reference_briefs[]` (each with `brief_id`, `domain`, `technologies`, `search_skills`, `relevance_rationale`).

Your task is to match real adesso colleagues and comparable past projects using the **Profiler MCP tool**, then condense the hits into anonymised, role-based team entries and anonymised reference projects. In this step — and only this step of the whole chain — the Profiler MCP is used. The tender document is never analysed here, and no external web research is done here.

The output must be written in the language specified by the `output_language` parameter. If `output_language` is not provided, default to German.

Role:
Act as a staffing lead who queries the adesso Profiler to find fitting colleagues and comparable project experience. You are precise, privacy-conscious, and honest: you anonymise, you never invent people or projects, and you flag gaps clearly.

Emotion/Tone:
Professional, factual, privacy-conscious. Every team entry and reference is backed by a real Profiler hit or explicitly marked as an unmatched placeholder.

Action — follow these steps in order:

0. **Read the catalogue.** Load `StaffingCatalogResult.json`.

1. **Clarification gate (mandatory Human-in-the-Loop).** Determine whether user input is needed BEFORE querying: e.g. a role whose `profiler_query` is too broad to disambiguate, conflicting location/availability constraints, or a `reference_briefs` domain that is ambiguous. If at least one such case exists:
   - Present a single, consolidated set of questions to the user, naming the affected role(s)/brief(s) and the concrete choice or missing information.
   - STOP and WAIT for the user's answer. Do NOT query the Profiler before the user has responded.
   If nothing needs clarification, skip this gate.

2. **Match team.** For each `roles[]` entry, invoke the Profiler MCP with its `profiler_query` (skills, and location/availability if present). Select the best-fitting profile. Use `location`/`availability` ONLY to filter — never carry them into the output.

3. **Match references.** For each `reference_briefs[]` entry, use `search_skills`/`technologies` to surface comparable project experience from colleagues' profiles. Aggregate into an anonymised reference (industry, scope, duration, relevance) — never expose a client's name.

4. **Anonymise & condense.** Convert hits into role-based, anonymous entries: role title, seniority, skills, certifications, years of experience. NO person names anywhere.

5. **Fallback.** If the Profiler returns nothing usable for a role, still emit a `team[]` entry with `matched: false`, `years_experience: 0`, and a `note` (in `output_language`) instructing to research the profile in the Profiler. Likewise emit an unmatched `references[]` entry with `matched: false` if a brief yields nothing. NEVER fabricate a person or a project.

6. **Coverage.** Fill `coverage`: `roles_total` = number of catalogue roles, `roles_matched` = matched team entries, `references_total` = number of briefs, `references_matched` = matched references.

Output & Validation (Code Interpreter):
Produce the final result as a schema-validated file using the Code Interpreter — do NOT return the JSON inline in the chat.

1. Draft the match JSON in memory following all field rules above.
2. Use the Code Interpreter to load the JSON Schema from `profiler_match.json` and validate your draft with the `jsonschema` library (draft 2020-12).
3. If validation fails, inspect the violations, correct the draft, and re-validate. Repeat until it validates cleanly.
4. If a violation cannot be resolved, add an `errors` entry with `code: "SCHEMA_VALIDATION_FAILED"`, `severity: "error"`, and a `message` in `output_language`, then keep the object otherwise schema-conformant.
5. Write the final validated object to a file named `ProfilerMatchResult.json` (UTF-8, pretty-printed) and upload it back into the context so downstream steps can consume it.

Tweak:
- REMINDER: The clarification gate in step 1 is mandatory whenever matching is ambiguous. Never query the Profiler before the user answers such a question.
- CRITICAL — anonymisation: NO person names, NO client names on references. Standort/Verfügbarkeit steer matching only and must never appear in the output.
- CRITICAL — no fabrication: every matched entry is backed by a real Profiler hit; unmatched needs are `matched: false` placeholders, never invented.
- The Profiler MCP is the only external tool used here; do NOT analyse the tender and do NOT do web research.
- Use `output_language` for all human-readable values (`role_title`, `note`, `industry`, `scope`, `relevance`, `message`).
- Carry `reference_id` over from the corresponding `brief_id`.
- The authoritative deliverable is `ProfilerMatchResult.json`, validated against `profiler_match.json`. The file content must be valid JSON only — no markdown fences, no commentary.
```

- [ ] **Step 2: Struktur-Verifikation**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
grep -cE '^(Context:|Role:|Emotion/Tone:|Action|Output & Validation \(Code Interpreter\):|Tweak:)' docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md
grep -c 'ProfilerMatchResult.json' docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md
grep -ciE 'clarification gate|anonymis|matched: false' docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md
```
Expected: erste Zeile `6`, zweite `>=2`, dritte `>=3` (HITL-Gate, Anonymisierung, Fallback vorhanden).

- [ ] **Step 3: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/prompts/profiler_match.md
git commit -m "ENH proposalgenerator: add profiler_match prompt with Profiler MCP + HITL gate"
```

---

### Task 5: `plan.json` verdrahten

**Files:**
- Modify: `docs/.adesso/skills/proposalgenerator/plan.json`

**Interfaces:**
- Consumes: die in Task 1–4 erzeugten Prompts/Schemata.
- Produces: Chain-Kette `SolutionProposal → StaffingCatalog → ProfilerMatch`; `Proposal.batch` enthält `/solution/StaffingCatalog.json` und `/solution/ProfilerMatch.json`.

- [ ] **Step 1: `SolutionProposal.next` von `null` auf `"StaffingCatalog"` setzen**

In `docs/.adesso/skills/proposalgenerator/plan.json`, im `Solution`-Array beim Objekt mit `"name": "SolutionProposal"`, die Zeile
```json
        "next": null,
```
ersetzen durch
```json
        "next": "StaffingCatalog",
```
(Es ist die `next`-Zeile innerhalb des `SolutionProposal`-Objekts — direkt unter dessen `"depends_on": "Solution",`.)

- [ ] **Step 2: Zwei neue Schritte in das `Solution`-Array einfügen**

Im `Solution`-Array direkt **nach** dem schließenden `}` des `SolutionProposal`-Objekts (vor dem `]`, das das `Solution`-Array beendet) einfügen — führendes Komma nach dem `SolutionProposal`-`}` nicht vergessen:

```json
      ,
      {
        "step": 3,
        "name": "StaffingCatalog",
        "description": "Derive the roles/skills the proposed solution needs (each with a Profiler search brief) plus reference-search briefs. Deterministic, no external knowledge, no Profiler calls.",
        "depends_on": "Solution",
        "next": "ProfilerMatch",
        "resources": {
          "prompt": "/prompts/staffing_catalog.md",
          "output": "/schema/staffing_catalog.json",
          "scripts": [],
          "assets": [],
          "references": [
            "/schema/staffing_catalog.json"
          ],
          "batch": [
            "/solution/SolutionProposal.md",
            "/preprocessing/Functional.json",
            "/preprocessing/Constraints.json"
          ],
          "artifacts": {}
        }
      },
      {
        "step": 4,
        "name": "ProfilerMatch",
        "description": "Match real adesso colleagues and comparable projects via the Profiler MCP against the staffing catalogue; produce anonymised, role-based team entries and anonymised references. Mandatory clarification gate when matching is ambiguous.",
        "depends_on": "Solution",
        "next": null,
        "resources": {
          "prompt": "/prompts/profiler_match.md",
          "output": "/schema/profiler_match.json",
          "scripts": [],
          "assets": [],
          "references": [
            "/schema/profiler_match.json"
          ],
          "batch": [
            "/solution/StaffingCatalog.json"
          ],
          "artifacts": {}
        }
      }
```

- [ ] **Step 3: `Proposal.batch` erweitern**

Im `Consolidation`-Array beim Objekt mit `"name": "Proposal"`, im `batch`-Array die letzte Zeile
```json
            "/solution/SolutionProposal.md"
```
ersetzen durch
```json
            "/solution/SolutionProposal.md",
            "/solution/StaffingCatalog.json",
            "/solution/ProfilerMatch.json"
```

- [ ] **Step 4: JSON-Gültigkeit + Chain-Konsistenz prüfen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
python3 - <<'PY'
import json, os
root = "docs/.adesso/skills/proposalgenerator"
plan = json.load(open(f"{root}/plan.json"))
chain = plan["chain"]
# 1) JSON parses (implicit). 2) Solution chain links resolve.
sol = {s["name"]: s for s in chain["Solution"]}
assert sol["SolutionProposal"]["next"] == "StaffingCatalog", sol["SolutionProposal"]["next"]
assert sol["StaffingCatalog"]["next"] == "ProfilerMatch"
assert sol["ProfilerMatch"]["next"] is None
# 3) Every referenced prompt/output/schema path exists on disk.
missing = []
for phase in chain.values():
    for step in phase:
        res = step.get("resources", {})
        for key in ("prompt", "output"):
            p = res.get(key)
            if p and not os.path.isfile(root + p):
                missing.append(root + p)
        for p in res.get("references", []):
            if not os.path.isfile(root + p):
                missing.append(root + p)
assert not missing, f"missing files: {missing}"
# 4) Proposal consumes the two new artifacts.
prop = {s["name"]: s for s in chain["Consolidation"]}["Proposal"]
b = prop["resources"]["batch"]
assert "/solution/StaffingCatalog.json" in b and "/solution/ProfilerMatch.json" in b
print("PLAN OK")
PY
echo "exit=$?"
```
Expected: `PLAN OK`, `exit=0`. (Prüft: valides JSON, korrekte `next`-Kette, alle referenzierten Dateien existieren, Proposal konsumiert die neuen Artefakte.)

- [ ] **Step 5: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/plan.json
git commit -m "ENH proposalgenerator: wire StaffingCatalog + ProfilerMatch into plan.json"
```

---

### Task 6: `AGENT.md` verdrahten

**Files:**
- Modify: `docs/.adesso/skills/proposalgenerator/AGENT.md`

**Interfaces:**
- Consumes: die Chain-Struktur aus Task 5.
- Produces: Orchestrator kennt beide Schritte in Phase 2 (Solution), ihre Abhängigkeiten, die Profiler-MCP-Tool-Restriktion und das HITL-Gate.

- [ ] **Step 1: Workflow/Chain — zwei Schritte in Phase 2 ergänzen und Phase 3 neu nummerieren**

Im Abschnitt `# Workflow / Chain` den Block `Phase 2 — Solution` ersetzen:

Von:
```
Phase 2 — Solution
6. SolutionCatalog → skill `proposal-solution-catalog` → `SolutionCatalogResult.json`
7. SolutionProposal → skill `proposal-solution-proposal` → `SolutionProposalResult.md`
```
Zu:
```
Phase 2 — Solution
6. SolutionCatalog → skill `proposal-solution-catalog` → `SolutionCatalogResult.json`
7. SolutionProposal → skill `proposal-solution-proposal` → `SolutionProposalResult.md`
8. StaffingCatalog → skill `proposal-staffing-catalog` → `StaffingCatalogResult.json`
9. ProfilerMatch → skill `proposal-profiler-match` → `ProfilerMatchResult.json`
```

Und den Block `Phase 3 — Consolidation` von:
```
Phase 3 — Consolidation
8. OpenPoints → skill `proposal-open-points` → `OpenPointsResult.json`
9. Report → skill `proposal-report` → `ReportResult.md`
10. Proposal → skill `proposal-proposal` → `ProposalResult.md`
```
Zu:
```
Phase 3 — Consolidation
10. OpenPoints → skill `proposal-open-points` → `OpenPointsResult.json`
11. Report → skill `proposal-report` → `ReportResult.md`
12. Proposal → skill `proposal-proposal` → `ProposalResult.md`
```

- [ ] **Step 2: Dependency Rule ergänzen**

Im Abschnitt `# Dependency Rule`, direkt nach der Zeile
```
- `proposal-solution-proposal` may only run after `SolutionCatalogResult.json` exists.
```
diese zwei Zeilen einfügen:
```
- `proposal-staffing-catalog` may only run after `SolutionProposalResult.md`, `FunctionalResult.json`, and `ConstraintsResult.json` exist.
- `proposal-profiler-match` may only run after `StaffingCatalogResult.json` exists.
```

Und die Zeile
```
- `proposal-proposal` additionally consumes `SolutionCatalogResult.json` and `SolutionProposalResult.md`.
```
ersetzen durch:
```
- `proposal-proposal` additionally consumes `SolutionCatalogResult.json`, `SolutionProposalResult.md`, `StaffingCatalogResult.json`, and `ProfilerMatchResult.json`.
```

- [ ] **Step 3: Consolidation-Voraussetzung (`proposal-proposal`) um die neuen Artefakte erweitern**

Die Zeile (im Dependency-/Consolidation-Voraussetzungsblock)
```
  - all files above plus `OpenPointsResult.json`, `SolutionCatalogResult.json`, and `SolutionProposalResult.md`
```
ersetzen durch:
```
  - all files above plus `OpenPointsResult.json`, `SolutionCatalogResult.json`, `SolutionProposalResult.md`, `StaffingCatalogResult.json`, and `ProfilerMatchResult.json`
```

- [ ] **Step 4: Profiler-MCP-Tool-Restriktion + HITL-Gate dokumentieren**

Im Abschnitt zur DeepResearch-Erlaubnis, nach der Zeile (ca. Zeile 47)
```
External research via the DeepResearch tool is permitted **only** in the `proposal-solution-proposal` step, and only for technology and best-practice research — never for analysing the tender document. All tender content remains RAG-only.
```
diese Zeile einfügen:
```
The Profiler MCP is permitted **only** in the `proposal-profiler-match` step, and only to match colleagues/skills and comparable project experience — never for analysing the tender document. All Profiler output is anonymised (no person names, no client names).
```

Und im Abschnitt `# User Interaction Rule` bei der Klärungs-Ausnahme (nach dem `proposal-solution-proposal`-Gate-Absatz, ca. Zeile 193) diesen Satz ergänzen:
```
The same applies to the `proposal-profiler-match` step: when Profiler matching is ambiguous (over-broad query, conflicting location/availability, ambiguous reference domain), you MUST ask the user before querying the Profiler and wait for the answer.
```

- [ ] **Step 5: Verifikation**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
F=docs/.adesso/skills/proposalgenerator/AGENT.md
grep -c 'proposal-staffing-catalog' $F      # expect >=2
grep -c 'proposal-profiler-match' $F         # expect >=3
grep -c '12. Proposal' $F                    # expect 1 (renumbered)
grep -c 'Profiler MCP is permitted' $F       # expect 1
! grep -qE '^8\. OpenPoints' $F && echo "old numbering gone OK"   # old "8. OpenPoints" must be gone
```
Expected: `>=2`, `>=3`, `1`, `1`, `old numbering gone OK`.

- [ ] **Step 6: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/AGENT.md
git commit -m "ENH proposalgenerator: orchestrate StaffingCatalog + ProfilerMatch in AGENT.md"
```

---

### Task 7: `proposal.md` an Profiler-Artefakt anbinden (G2-Cleanup)

**Files:**
- Modify: `docs/.adesso/skills/proposalgenerator/prompts/proposal.md`

**Interfaces:**
- Consumes: `ProfilerMatchResult.json` (`team[]`, `references[]`).
- Produces: Kap. 2.5 (Team) und Annex A (Profile + Referenzen) werden aus dem Artefakt gespeist statt erfunden.

- [ ] **Step 1: Input-Liste im Context erweitern**

Im `Context:`-Abschnitt, nach der Zeile, die `OpenPointsResult.json` beschreibt (die mit `- \`OpenPointsResult.json\` — gap analysis: ...` beginnt), diese Zeile einfügen:
```
- `ProfilerMatchResult.json` — anonymised, role-based team profiles (`team[]`) and anonymised reference projects (`references[]`) matched from the adesso Profiler. Conforms to `profiler_match.json`.
```

- [ ] **Step 2: Kap. 2.5 — erfundene Team-Zusammensetzung durch Artefakt-Konsum ersetzen**

Die Zeile
```
- Describe adesso's proposed project team composition — list each role with a brief profile (seniority, key competence, allocation in %)
```
ersetzen durch:
```
- Populate the project team from `ProfilerMatchResult.json` `team[]` (anonymised, role-based) — one row per entry with role, seniority, key skills, and allocation. Do NOT invent team members. For entries with `matched: false`, insert the row as a placeholder and add its `note` (e.g. "im Profiler recherchieren"). Never output person names, locations, or availability.
```

- [ ] **Step 3: Annex A — erfundene Referenzen und Profile durch Artefakt-Konsum ersetzen**

Den Block
```
- Present 2–3 reference projects in a structured format (if derivable from formal eligibility requirements):
  ```
  **Reference Project: [Title]**
  Client: [Industry/anonymised] | Duration: [X months] | Team Size: [N]
  Scope: [Brief description]
  Relevance: [Why this project is comparable]
  ```
- Describe the proposed team's key qualifications — list each key role with seniority, relevant experience, and certifications
```
ersetzen durch:
```
- Present the reference projects from `ProfilerMatchResult.json` `references[]` — anonymised, one block per entry. Never output a client name:
  ```
  **Referenzprojekt: [industry]**
  Branche: [industry] | Dauer: [duration]
  Umfang: [scope]
  Relevanz: [relevance]
  ```
  For entries with `matched: false`, mark the reference as a placeholder ("Referenz im Fachbereich zu bestätigen"). If `references[]` is empty, write one placeholder line and do NOT invent references.
- Describe the proposed team's key qualifications from `ProfilerMatchResult.json` `team[]` — per role: seniority, key skills, certifications, years of experience (anonymised, no names). For `matched: false` roles, note that the profile must be sourced from the Profiler.
```

- [ ] **Step 4: Tweak — Anti-Halluzinations-Regel ergänzen**

Im `Tweak:`-Abschnitt am Ende eine Zeile ergänzen:
```
- Team members (Kap. 2.5), key profiles and reference projects (Annex A) come EXCLUSIVELY from `ProfilerMatchResult.json` — never invent persons, CVs, client names, or reference projects. Unmatched needs (`matched: false`) become placeholders with a Profiler/Fachbereich hint.
```

- [ ] **Step 5: Verifikation**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
F=docs/.adesso/skills/proposalgenerator/prompts/proposal.md
grep -c 'ProfilerMatchResult.json' $F                       # expect >=4
! grep -q 'Present 2–3 reference projects' $F && echo "invented-references removed OK"
! grep -q 'list each role with a brief profile' $F && echo "invented-team removed OK"
```
Expected: `>=4`, `invented-references removed OK`, `invented-team removed OK`.

- [ ] **Step 6: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app
git add docs/.adesso/skills/proposalgenerator/prompts/proposal.md
git commit -m "ENH proposalgenerator: consume ProfilerMatch profiles/references in proposal (fix G2 hallucination)"
```

---

## Self-Review

**1. Spec coverage:**
- Design „Schritt A1 — StaffingCatalog" (Schema + Prompt + Inputs `SolutionProposalResult.md`/`FunctionalResult.json`/`ConstraintsResult.json`) → Task 1, 2. ✓
- Design „Schritt A2 — ProfilerMatch" (Profiler-MCP, HITL, Anonymisierung, Fallback, doppelter Zweck Team+Referenzen) → Task 3, 4. ✓
- Design „Chain-Einordnung nach SolutionProposal, vor Consolidation/Proposal" → Task 5 (plan.json), Task 6 (AGENT.md). ✓
- Design „Anbindung an proposal.md (löst G2)" — Kap. 2.5 + Annex A Profile + Annex A Referenzen, Halluzinations-Anweisungen entfernen → Task 7. ✓
- Design „Anonymisiert/rollenbasiert, keine Klarnamen, Standort/Verfügbarkeit nur Matching" → Global Constraints + Schema (kein name-Feld) + profiler_match.md Tweak + proposal.md Step 2/3. ✓
- Design „SLAs bleiben unberührt" → keine Task fasst Kap. 2.7 an. ✓ (bewusst)
- Design „Annahme: Profiler liefert Projekterfahrung; sonst references leer" → `reference_briefs`/`references` ohne minItems, Fallback in profiler_match.md Step 5. ✓

**2. Placeholder scan:** Keine `TBD`/`TODO`/„handle appropriately". Alle Code-/JSON-/Prompt-Inhalte sind vollständig ausgeschrieben; jeder Test hat konkrete Kommandos + erwartete Ausgabe. ✓

**3. Type consistency:**
- Seniority-Enum `["junior","regular","senior","lead"]` identisch in `staffing_catalog.json` (`roles[].seniority`) und `profiler_match.json` (`team[].seniority`) und in den Beispielinstanzen. ✓
- `role_id` (R-01) fließt von `staffing_catalog.roles[].role_id` → `profiler_match.team[].role_id`. ✓
- `brief_id` (REF-01) → `references[].reference_id` (in profiler_match.md Step „Carry reference_id over from brief_id"). ✓
- Artefaktnamen konsistent: `StaffingCatalogResult.json`, `ProfilerMatchResult.json` in Prompts, plan.json-Outputs (`/schema/...`), AGENT.md und proposal.md. ✓
- plan.json-Batch-Pfade `/solution/StaffingCatalog.json`, `/solution/ProfilerMatch.json` entsprechen dem bestehenden Muster (`/solution/SolutionCatalog.json`). ✓

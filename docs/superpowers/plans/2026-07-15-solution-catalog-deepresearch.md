# Lösungskatalog + DeepResearch-Lösungsvorschlag — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zwei neue `proposalgenerator`-Kettenschritte ergänzen — ein deterministischer Lösungskatalog (JSON) und ein DeepResearch-gestützter, auf genau eine Lösung konvergierender Lösungsvorschlag (Markdown) mit Human-in-the-Loop-Rückfrage bei Recherche-Unsicherheit.

**Architecture:** Neue Phase `Solution` zwischen `PreProcessing` und dem `Proposal`-Schritt. `SolutionCatalog` clustert FR/NFR aus `FunctionalResult.json` (+ `ConstraintsResult.json`, `ClientContextResult.json`) zu Lösungsbausteinen und markiert Unsicherheit. `SolutionProposal` fragt bei geflaggten Bausteinen zuerst den User, recherchiert dann pro Baustein via DeepResearch-Tool und verdichtet zu einer eindeutigen Gesamtlösung. Beide Artefakte fließen in den `Proposal`-Schritt (Kap. 2.3).

**Tech Stack:** Markdown-Prompts, JSON Schema (Draft 2020-12), Python `jsonschema` 4.10.3 (bereits installiert) zur Validierung, Skill-Runtime mit Code Interpreter + DeepResearch-Agent-Tool.

## Global Constraints

- Zielverzeichnis aller Skill-Dateien: `docs/.adesso/skills/proposalgenerator/` (relativ zu `/home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/`).
- Alle User-sichtbaren Strings (`title`, `description`, `label`, `message`, Kapitelüberschriften, Rückfragen) werden in der `output_language` erzeugt; Default `en` sofern nicht anders bestimmt.
- JSON Schemas: `"$schema": "https://json-schema.org/draft/2020-12/schema"`, `additionalProperties: false` auf jeder Objektebene, `errors`-Block-Muster identisch zu `schema/functional_requirements.json`.
- ID-Konventionen: Lösungsbausteine `SB-01`, `SB-02`, …; referenzierte Anforderungen nutzen bestehende `FR-NNN` / `NFR-NNN`.
- Tender-Analyse bleibt **RAG-only**; das DeepResearch-Tool ist **ausschließlich** im Schritt `SolutionProposal` erlaubt.
- Der finale Lösungsvorschlag ist **eindeutig**: genau eine Empfehlung je Baustein, keine offene Technologie-Wahl für den Kunden.
- Datei-Namenskonvention (bestehende Inkonsistenz beibehalten): `plan.json`-`batch`-Pfade nutzen `/<phase>/<StepName>.json`; `AGENT.md` und Prompts nutzen `<StepName>Result.json` / `<StepName>Result.md`.
- Commits erfolgen auf Branch `feat/proposal-solution-catalog`.
- Arbeitsverzeichnis für alle Kommandos: `cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator`.

---

### Task 1: Lösungskatalog-JSON-Schema

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/schema/solution_catalog.json`
- Test (Fixtures, temporär): `/tmp/claude-1000/-home-gebert-adgpt-agenticEngineering-adGPT-BudgetLimiting-configs-proposal-skill-app/78249cc7-af18-4593-a7af-131c140bc59c/scratchpad/sc_valid.json`, `.../scratchpad/sc_invalid.json`

**Interfaces:**
- Produces: Schema `solution_catalog.json` mit Top-Level `solution_blocks[]`, `coverage{}`, `errors[]`, optional `document_id`. `solution_blocks[]`-Item-Felder (Namen, die Task 2 im Prompt referenziert): `block_id`, `title`, `description`, `addressed_requirements[]`, `aspect_ids[]`, `solution_type`, `priority` (`must|should|nice-to-have`), `constraints[]`, `evaluation_criteria[]`, `candidate_directions[]` (`{label, rationale}`), `research_questions[]`, `needs_clarification` (bool), `clarification_reason` (`multiple_directions|low_confidence|insufficient_constraints`), `clarification_question` (string), `confidence` (0..1). `coverage`: `total_requirements`, `covered_requirements`, `uncovered_requirement_ids[]`.

- [ ] **Step 1: Gültige Beispiel-Instanz als Fixture schreiben (Spec-by-Example)**

Schreibe nach `.../scratchpad/sc_valid.json`:

```json
{
  "document_id": "CloudRetail-POS-2025",
  "solution_blocks": [
    {
      "block_id": "SB-01",
      "title": "Offline-fähige Kassentransaktionen",
      "description": "Kassenvorgänge müssen bei Netzausfall lokal weiterlaufen und nach Reconnect synchronisieren. Deckt die Ausfallsicherheit der Filialkassen ab.",
      "addressed_requirements": ["FR-001", "FR-004", "NFR-002"],
      "aspect_ids": ["asp-3"],
      "solution_type": "Integration",
      "priority": "must",
      "constraints": ["muss auf Azure laufen", "keine On-Prem-Datenhaltung"],
      "evaluation_criteria": ["Robustheit der Offline-Sync", "DACH-Datenresidenz", "Betriebskosten"],
      "candidate_directions": [
        { "label": "Azure-native Sync (SQL Edge + Sync Framework)", "rationale": "Nahtlose Azure-Integration, erfüllt Datenresidenz." },
        { "label": "CouchDB/PouchDB Replikation", "rationale": "Erprobtes Offline-First-Modell, aber zusätzlicher Betriebsaufwand." }
      ],
      "research_questions": [
        "Welche Offline-Sync-Technologien erfüllen 99,9% Konsistenz bei intermittierender Konnektivität?",
        "Welche Best Practices existieren für Konfliktauflösung bei POS-Transaktionen?"
      ],
      "needs_clarification": true,
      "clarification_reason": "multiple_directions",
      "clarification_question": "Für die Offline-Fähigkeit stehen ein Azure-nativer Sync-Ansatz und eine CouchDB/PouchDB-Replikation zur Wahl — welche Richtung soll recherchiert werden?",
      "confidence": 0.45
    },
    {
      "block_id": "SB-02",
      "title": "Automatisiertes Reporting",
      "description": "Verkaufszahlen sollen automatisiert und tagesaktuell ausgewertet werden. Ersetzt die manuellen Reporting-Prozesse.",
      "addressed_requirements": ["FR-007", "NFR-005"],
      "aspect_ids": ["asp-7"],
      "solution_type": "Datenplattform",
      "priority": "should",
      "constraints": ["muss auf Azure laufen"],
      "evaluation_criteria": ["Time-to-Insight", "Integrationsaufwand", "Lizenzkosten"],
      "candidate_directions": [
        { "label": "Azure Synapse + Power BI", "rationale": "Einzige mit Constraints kompatible, ausgereifte Richtung." }
      ],
      "research_questions": [
        "Welche Best Practices gelten für Near-Realtime-Retail-Reporting auf Azure Synapse?"
      ],
      "needs_clarification": false,
      "confidence": 0.82
    }
  ],
  "coverage": {
    "total_requirements": 6,
    "covered_requirements": 5,
    "uncovered_requirement_ids": ["NFR-009"]
  },
  "errors": []
}
```

- [ ] **Step 2: Ungültige Beispiel-Instanz schreiben (fehlendes Pflichtfeld `priority`)**

Schreibe nach `.../scratchpad/sc_invalid.json` (identisch zu `sc_valid.json`, aber im ersten Block Zeile `"priority": "must",` entfernen). Minimalvariante genügt:

```json
{
  "solution_blocks": [
    {
      "block_id": "SB-01",
      "title": "x",
      "description": "x",
      "addressed_requirements": ["FR-001"],
      "solution_type": "Integration",
      "evaluation_criteria": ["x"],
      "research_questions": ["x"],
      "needs_clarification": false,
      "confidence": 0.5
    }
  ],
  "coverage": { "total_requirements": 1, "covered_requirements": 1, "uncovered_requirement_ids": [] },
  "errors": []
}
```

- [ ] **Step 3: Validierung gegen (noch fehlendes) Schema ausführen — muss fehlschlagen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
python3 -c "import json; json.load(open('schema/solution_catalog.json'))"
```
Expected: FAIL mit `FileNotFoundError: ... schema/solution_catalog.json` (Schema existiert noch nicht).

- [ ] **Step 4: Schema `solution_catalog.json` schreiben**

Create `schema/solution_catalog.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/schemas/solution-catalog.schema.json",
    "title": "SolutionCatalog",
    "description": "Deterministic catalogue of solution blocks derived from functional/non-functional requirements, constraints and client context. Bridges requirements to downstream technology research.",
    "type": "object",
    "additionalProperties": false,
    "properties": {
        "document_id": {
            "type": "string",
            "description": "Optional ID of the source document."
        },
        "solution_blocks": {
            "type": "array",
            "description": "Thematic solution blocks, each clustering one or more requirements into a solution need.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "block_id": {
                        "type": "string",
                        "description": "Unique ID of the solution block (e.g. SB-01)."
                    },
                    "title": {
                        "type": "string",
                        "description": "Short title of the solution block, in output_language."
                    },
                    "description": {
                        "type": "string",
                        "description": "What capability/need this block covers, derived from the requirements, in output_language."
                    },
                    "addressed_requirements": {
                        "type": "array",
                        "description": "FR/NFR IDs this block addresses (e.g. FR-001, NFR-002).",
                        "items": { "type": "string" },
                        "minItems": 1
                    },
                    "aspect_ids": {
                        "type": "array",
                        "description": "Optional aspect IDs from the source analysis this block relates to.",
                        "items": { "type": "string" }
                    },
                    "solution_type": {
                        "type": "string",
                        "description": "Category of solution needed (e.g. Integration, Datenplattform, Frontend, Security, Cloud-Infra)."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["must", "should", "nice-to-have"],
                        "description": "Highest MoSCoW priority among the addressed requirements."
                    },
                    "constraints": {
                        "type": "array",
                        "description": "Relevant technical/budget/organisational constraints bounding this block, taken from ConstraintsResult.",
                        "items": { "type": "string" }
                    },
                    "evaluation_criteria": {
                        "type": "array",
                        "description": "Criteria to evaluate candidate technologies for this block.",
                        "items": { "type": "string" },
                        "minItems": 1
                    },
                    "candidate_directions": {
                        "type": "array",
                        "description": "Plausible technology directions (families, not concrete products) considered for this block.",
                        "items": {
                            "type": "object",
                            "additionalProperties": false,
                            "properties": {
                                "label": { "type": "string", "description": "Name of the technology direction." },
                                "rationale": { "type": "string", "description": "Why this direction is plausible." }
                            },
                            "required": ["label", "rationale"]
                        }
                    },
                    "research_questions": {
                        "type": "array",
                        "description": "Concrete research questions handed to the DeepResearch step.",
                        "items": { "type": "string" },
                        "minItems": 1
                    },
                    "needs_clarification": {
                        "type": "boolean",
                        "description": "True if user clarification is required before research (multiple directions, low confidence, or insufficient constraints)."
                    },
                    "clarification_reason": {
                        "type": "string",
                        "enum": ["multiple_directions", "low_confidence", "insufficient_constraints"],
                        "description": "Why clarification is needed. Present only when needs_clarification is true."
                    },
                    "clarification_question": {
                        "type": "string",
                        "description": "Question to ask the user, in output_language. Present only when needs_clarification is true."
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence that the block is well-scoped for research (0-1)."
                    }
                },
                "required": [
                    "block_id",
                    "title",
                    "description",
                    "addressed_requirements",
                    "solution_type",
                    "priority",
                    "evaluation_criteria",
                    "research_questions",
                    "needs_clarification",
                    "confidence"
                ]
            }
        },
        "coverage": {
            "type": "object",
            "additionalProperties": false,
            "description": "Coverage statistics of requirements across all solution blocks.",
            "properties": {
                "total_requirements": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Total number of FR+NFR in the input."
                },
                "covered_requirements": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of requirements addressed by at least one block."
                },
                "uncovered_requirement_ids": {
                    "type": "array",
                    "description": "IDs of requirements not addressed by any block.",
                    "items": { "type": "string" }
                }
            },
            "required": ["total_requirements", "covered_requirements", "uncovered_requirement_ids"]
        },
        "errors": {
            "type": "array",
            "description": "Error block for validation or processing errors.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "code": { "type": "string", "description": "Technical error code." },
                    "message": { "type": "string", "description": "Human-readable error message." },
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "error"],
                        "description": "Severity level of the error."
                    },
                    "reference": {
                        "type": "object",
                        "additionalProperties": false,
                        "description": "Optional reference to affected elements.",
                        "properties": {
                            "block_id": { "type": "string" },
                            "aspect_id": { "type": "string" }
                        }
                    }
                },
                "required": ["code", "message"]
            }
        }
    },
    "required": ["solution_blocks", "coverage"]
}
```

- [ ] **Step 5: Validierung ausführen — gültig besteht, ungültig schlägt fehl**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
SCRATCH=/tmp/claude-1000/-home-gebert-adgpt-agenticEngineering-adGPT-BudgetLimiting-configs-proposal-skill-app/78249cc7-af18-4593-a7af-131c140bc59c/scratchpad
python3 - "$SCRATCH" <<'PY'
import json, sys
from jsonschema import Draft202012Validator
scratch = sys.argv[1]
schema = json.load(open('schema/solution_catalog.json'))
Draft202012Validator.check_schema(schema)
v = Draft202012Validator(schema)
valid = json.load(open(f'{scratch}/sc_valid.json'))
assert v.is_valid(valid), f"valid fixture rejected: {list(v.iter_errors(valid))}"
invalid = json.load(open(f'{scratch}/sc_invalid.json'))
assert not v.is_valid(invalid), "invalid fixture wrongly accepted"
print("OK: schema well-formed, valid passes, invalid fails")
PY
```
Expected: `OK: schema well-formed, valid passes, invalid fails`

- [ ] **Step 6: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/schema/solution_catalog.json
git commit -m "ENH proposalgenerator: add solution_catalog JSON schema"
```

---

### Task 2: SolutionCatalog-Prompt

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/prompts/solution_catalog.md`

**Interfaces:**
- Consumes: Input-Artefakte `FunctionalResult.json` (`functional_requirements[].{id,description,priority,aspect_id}`, `non_functional_requirements[].{id,category,description,measurable_target,aspect_id}`, `aspects[]`), `ConstraintsResult.json` (`constraints.{budget,timeline,technical[],organisational[]}`), `ClientContextResult.json` (`client_context.{industry,current_systems,pain_points,strategic_goals}`). Validiert Output gegen `schema/solution_catalog.json`.
- Produces: Artefakt `SolutionCatalogResult.json`.

- [ ] **Step 1: Prompt `solution_catalog.md` schreiben**

Create `prompts/solution_catalog.md`:

```markdown
Context:
You receive the schema-validated artifacts of the preceding chain steps as input files. Read every field directly from them — do NOT retrieve the tender document and do NOT use external/general knowledge in this step:

- `FunctionalResult.json` — functional (`functional_requirements[]`: `id`, `description`, `priority`, `aspect_id`) and non-functional (`non_functional_requirements[]`: `id`, `category`, `description`, `measurable_target`, `aspect_id`) requirements plus `aspects[]`. Conforms to `functional_requirements.json`.
- `ConstraintsResult.json` — `constraints.budget` (`amount`, `currency`, `flexibility`), `constraints.timeline` (`go_live`, `key_milestones`), `constraints.technical[]`, `constraints.organisational[]`. Conforms to `constraints.json`.
- `ClientContextResult.json` — `client_context` (`industry`, `current_systems`, `pain_points`, `strategic_goals`). Conforms to `client_context.json`.

Your task is to derive a **solution catalogue**: cluster the functional and non-functional requirements into thematic **solution blocks** and, for each block, formulate a concrete research brief for the downstream technology-research step. This step is a deterministic bridge — it names solution NEEDS and technology DIRECTIONS (families), never concrete products, vendors, or technologies.

All labels, descriptions, questions, and messages in your output must be written in the language specified by the `output_language` parameter. If `output_language` is not provided, default to English.

Role:
Act as an experienced solution architect who structures requirement sets into coherent solution areas and scopes technology research. You group related requirements, respect constraints, and honestly flag where the solution direction is not yet determinable.

Emotion/Tone:
Neutral, systematic, exact. Prioritise correctness over completeness — only cluster what the requirements actually support. Do not invent requirements, constraints, or technologies.

Action:
Produce a JSON object conforming to `solution_catalog.json` with the following structure:

1. **solution_blocks**: One entry per thematic solution area. Group requirements that address the same capability/concern. For each block:
   - `block_id`: unique ID in the format `"SB-01"`, `"SB-02"`, ...
   - `title`: short title of the solution area, in `output_language`.
   - `description`: two sentences describing the capability/need this block covers, derived from the addressed requirements, in `output_language`.
   - `addressed_requirements`: the FR/NFR IDs this block addresses (from `functional_requirements[].id` and `non_functional_requirements[].id`). Each block must address at least one requirement.
   - `aspect_ids`: the related aspect IDs (collect the `aspect_id` values of the addressed requirements). Optional.
   - `solution_type`: the category of solution needed (e.g. `"Integration"`, `"Datenplattform"`, `"Frontend"`, `"Security"`, `"Cloud-Infra"`) — choose the best fit, in `output_language`.
   - `priority`: the highest MoSCoW priority among the addressed requirements (`"must"` > `"should"` > `"nice-to-have"`).
   - `constraints`: the technical/budget/organisational constraints from `ConstraintsResult.json` that bound THIS block (copy the relevant `constraints.technical`/`constraints.organisational` strings; add a budget/timeline note if relevant). Empty array if none apply.
   - `evaluation_criteria`: 2-5 criteria by which candidate technologies for this block should be judged (derive from the addressed NFRs, constraints, and client goals — e.g. measurable NFR targets, data residency, cost).
   - `candidate_directions`: plausible technology DIRECTIONS (families/approaches, NOT products) to consider, each with `label` and `rationale` in `output_language`. Provide the directions you can justify from the requirements/constraints; a single direction is fine when only one is defensible.
   - `research_questions`: 1-4 concrete questions the downstream research step must answer for this block, in `output_language`.
   - `needs_clarification`: set to `true` if ANY of these hold — (a) two or more seriously competing `candidate_directions`, (b) `confidence` below 0.5, (c) the requirements/constraints are too thin to scope the research. Otherwise `false`.
   - `clarification_reason`: only when `needs_clarification` is `true` — one of `"multiple_directions"`, `"low_confidence"`, `"insufficient_constraints"` (pick the dominant cause).
   - `clarification_question`: only when `needs_clarification` is `true` — a single clear question to the user, in `output_language`, naming the choice or the missing information.
   - `confidence`: a score 0-1 for how well-scoped the block is for research.

2. **coverage**: `total_requirements` = count of all FR + NFR in the input; `covered_requirements` = count of distinct requirement IDs appearing in any block's `addressed_requirements`; `uncovered_requirement_ids` = the FR/NFR IDs not addressed by any block.

3. **errors**: report structural problems (e.g. no requirements in input) using `code`, `message` (in `output_language`), optional `severity` and `reference.block_id`. Empty array if none.

4. **document_id**: copy from an input `document_id` if present, otherwise omit.

Output & Validation (Code Interpreter):
Produce the final result as a schema-validated file using the Code Interpreter — do NOT return the JSON inline in the chat.

1. Draft the catalogue JSON in memory following all field rules above.
2. Use the Code Interpreter to load the JSON Schema from `solution_catalog.json` and validate your draft with the `jsonschema` library (draft 2020-12).
3. If validation fails, inspect the violations, correct the draft, and re-validate. Repeat until it validates cleanly.
4. If a violation cannot be resolved from the input content, add an `errors` entry with `code: "SCHEMA_VALIDATION_FAILED"`, `severity: "error"`, and a `message` in `output_language`, then keep the object otherwise schema-conformant.
5. Write the final validated object to a file named `SolutionCatalogResult.json` (UTF-8, pretty-printed) and upload it back into the context so downstream steps can consume it.

Tweak:
- Use `output_language` for all `title`, `description`, `solution_type`, `label`, `rationale`, `research_questions`, `clarification_question`, and `message` values.
- Do NOT name concrete products, vendors, or technologies anywhere — only solution needs and technology directions/families.
- Every requirement should ideally belong to at least one block; list genuinely unmapped ones under `coverage.uncovered_requirement_ids` rather than forcing them into a block.
- `priority` must be the maximum priority of the block's addressed requirements, not an average.
- A block gets `needs_clarification: true` whenever the research direction is genuinely open — do not suppress uncertainty to appear decisive; the downstream step will ask the user.
- The authoritative deliverable is `SolutionCatalogResult.json`, validated against `solution_catalog.json`. The file content must be valid JSON only — no markdown fences, no commentary.
```

- [ ] **Step 2: Konsistenz-Check ausführen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
for token in FunctionalResult.json ConstraintsResult.json ClientContextResult.json solution_catalog.json SolutionCatalogResult.json needs_clarification clarification_reason candidate_directions research_questions output_language "Code Interpreter"; do
  grep -q -- "$token" prompts/solution_catalog.md || echo "MISSING: $token"
done
echo "check done"
```
Expected: nur `check done` (keine `MISSING:`-Zeile).

- [ ] **Step 3: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/prompts/solution_catalog.md
git commit -m "ENH proposalgenerator: add solution_catalog prompt"
```

---

### Task 3: Layout-Beispiel für den Lösungsvorschlag

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/schema/solution_proposal_output.md`

**Interfaces:**
- Produces: Layout-Template `solution_proposal_output.md` (fiktives Beispiel), das Task 4 als autoritative Layout-Vorlage referenziert. Kapitelreihenfolge: 1 Recherche-Vorgehen · 2 Lösungslandschaft · 3 Lösungsbausteine im Detail · 4 Gesamt-Lösungsvorschlag · 5 Technologie-Stack · 6 Annahmen/Risiken/offene Fragen · 7 Quellenverzeichnis.

- [ ] **Step 1: Layout-Template schreiben**

Create `schema/solution_proposal_output.md`:

```markdown
<!-- THIS IS AN EXAMPLE OUTPUT using the fictional client "CloudRetail" and a POS modernisation scenario. -->
<!-- ALL company names, requirements, technologies, numbers, and sources below are PLACEHOLDERS. -->
<!-- The LLM MUST replace every detail with data derived from the SolutionCatalogResult.json and the DeepResearch findings. -->
<!-- Do NOT copy any content from this example. -->
<!-- This example is written in English. The LLM MUST translate all headings, table headers, and prose into output_language. -->

## 1 Research Approach and Scope

[EXAMPLE] This solution proposal is based on a structured technology assessment for the solution blocks defined in the solution catalogue. For each block, targeted research was carried out on available technologies and industry best practices, scoped to the directions confirmed with CloudRetail. Sources are referenced inline as [S1], [S2], ... and listed in chapter 7.

[EXAMPLE] Scope confirmed with the client: research was limited to the Microsoft Azure technology stack per the client's platform constraint.

<!-- Derive from: SolutionCatalogResult.research_questions, the user's clarification answers, DeepResearch method. -->

## 2 Solution Landscape Overview

[EXAMPLE] The proposed target architecture combines an offline-capable point-of-sale layer, a central transaction backbone, and an automated analytics platform. The following chapters detail each solution block and converge on one recommended technology per block.

<!-- Derive from: the set of solution_blocks and how they interact. One or two paragraphs. -->

## 3 Solution Blocks in Detail

### 3.1 [EXAMPLE] SB-01 Offline-Capable POS Transactions

**Addressed requirements:** [EXAMPLE] FR-001, FR-004, NFR-002

**Technology options**

| Option | Maturity | Fit to criteria | Advantages / Disadvantages | Source |
|---|---|---|---|---|
| [EXAMPLE] Azure SQL Edge + Sync Framework | High | Meets data residency + offline sync | + Native Azure integration / − higher licence cost | [S1] |
| [EXAMPLE] CouchDB/PouchDB replication | High | Meets offline sync, residency needs config | + Proven offline-first / − extra operational effort | [S2] |

**Best practices:** [EXAMPLE] Use idempotent transaction IDs and last-write-wins conflict resolution for POS sync [S1]; queue-and-forward on the terminal for network gaps [S3].

**Recommendation:** [EXAMPLE] Azure SQL Edge + Sync Framework — it satisfies the data-residency constraint and minimises operational overhead against the evaluation criteria (offline-sync robustness, DACH residency, running cost).

### 3.2 [EXAMPLE] SB-02 Automated Reporting

**Addressed requirements:** [EXAMPLE] FR-007, NFR-005

**Technology options**

| Option | Maturity | Fit to criteria | Advantages / Disadvantages | Source |
|---|---|---|---|---|
| [EXAMPLE] Azure Synapse + Power BI | High | Meets near-realtime + Azure constraint | + Integrated, low time-to-insight / − licence cost | [S4] |

**Best practices:** [EXAMPLE] Incremental materialised views for near-realtime retail KPIs [S4].

**Recommendation:** [EXAMPLE] Azure Synapse + Power BI.

<!-- Repeat 3.x for every solution block. Each block ends with EXACTLY ONE recommendation. -->

## 4 Consolidated Solution Proposal

[EXAMPLE] The recommended technologies integrate into a single coherent target architecture: offline-capable terminals synchronise via Azure SQL Edge into a central transaction store, which feeds Azure Synapse for automated reporting. This design satisfies the non-functional targets (99.9% availability, < 2s response) and complies with the Azure-only and data-residency constraints. No open technology choices remain.

<!-- Derive from: all block recommendations, integrated into ONE unambiguous solution. Integration view + NFR fulfilment. -->

## 5 Technology Stack Overview

| Solution block | Recommended technology | Role |
|---|---|---|
| [EXAMPLE] SB-01 Offline POS | Azure SQL Edge + Sync Framework | Offline transaction store & sync |
| [EXAMPLE] SB-02 Reporting | Azure Synapse + Power BI | Analytics & dashboards |

## 6 Assumptions, Risks and Open Research Questions

- [EXAMPLE] **Assumption:** existing terminals support containerised Azure SQL Edge.
- [EXAMPLE] **Risk:** licence cost of Synapse may exceed the indicative budget — to validate in scoping.
- [EXAMPLE] **Open question:** peak transaction volume per store not yet quantified.

## 7 Sources

- [EXAMPLE] [S1] Microsoft Learn — Azure SQL Edge data sync (URL, accessed 2025).
- [EXAMPLE] [S2] Apache CouchDB documentation — replication (URL, accessed 2025).
- [EXAMPLE] [S3] Vendor-neutral POS offline best-practice article (URL, accessed 2025).
- [EXAMPLE] [S4] Microsoft Learn — Azure Synapse real-time analytics (URL, accessed 2025).
```

- [ ] **Step 2: Struktur-Check ausführen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
for h in "## 1 Research Approach" "## 2 Solution Landscape" "## 3 Solution Blocks" "## 4 Consolidated Solution" "## 5 Technology Stack" "## 6 Assumptions" "## 7 Sources"; do
  grep -qF "$h" schema/solution_proposal_output.md || echo "MISSING HEADING: $h"
done
echo "check done"
```
Expected: nur `check done`.

- [ ] **Step 3: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/schema/solution_proposal_output.md
git commit -m "ENH proposalgenerator: add solution_proposal layout example"
```

---

### Task 4: SolutionProposal-Prompt

**Files:**
- Create: `docs/.adesso/skills/proposalgenerator/prompts/solution_proposal.md`

**Interfaces:**
- Consumes: `SolutionCatalogResult.json` (Felder aus Task 1) als Haupt-Input; Layout-Template `solution_proposal_output.md` (Task 3); DeepResearch-Agent-Tool.
- Produces: Artefakt `SolutionProposalResult.md`.

- [ ] **Step 1: Prompt `solution_proposal.md` schreiben**

Create `prompts/solution_proposal.md`:

```markdown
Context:
You receive `SolutionCatalogResult.json` (conforming to `solution_catalog.json`) as your main input. It contains `solution_blocks[]` with `block_id`, `title`, `description`, `addressed_requirements`, `solution_type`, `priority`, `constraints`, `evaluation_criteria`, `candidate_directions`, `research_questions`, `needs_clarification`, `clarification_reason`, `clarification_question`, `confidence`, plus a `coverage` object.

Your task is to research technologies and best practices for each solution block using the **DeepResearch tool**, then condense the findings into a single, unambiguous, well-founded solution proposal in Markdown that matches the catalogue. In this step — and only this step of the whole chain — external research via the DeepResearch tool is explicitly allowed and required. (The tender document itself is never re-analysed here.)

The proposal must be written in the language specified by the `output_language` parameter. If `output_language` is not provided, default to German.

Template:
Use `solution_proposal_output.md` as the **authoritative layout template**. It is a fully worked EXAMPLE (fictional client "CloudRetail", POS modernisation) showing the exact chapter order, heading structure, table formats, and tone.
- Mirror its structure and formatting precisely — same chapters, sub-headings, table columns, in the same order.
- Replace ALL example content: every `[EXAMPLE]` marker and every HTML comment (`<!-- ... -->`) is a placeholder. Derive everything from `SolutionCatalogResult.json` and your DeepResearch findings — never copy example wording.
- The template is written in English; translate all headings, table headers, and prose into `output_language`.

Role:
Act as a senior solution architect who selects and justifies technology decisions. You research thoroughly, weigh options against explicit criteria, respect hard constraints, and commit to exactly one recommendation per solution area. You never present unresolved technology choices to the client.

Emotion/Tone:
Professional, decisive, evidence-based. Every recommendation is traceable to evaluation criteria, addressed requirements, and cited sources.

Action — follow these steps in order:

0. **Read the catalogue.** Load `SolutionCatalogResult.json`. If the user's original request already stated technology preferences or limits (e.g. "only Azure"), adopt them as a global research scope.

1. **Clarification gate (mandatory Human-in-the-Loop).** Collect every block with `needs_clarification: true`. If there is at least one:
   - Present a single, consolidated set of questions to the user. For each such block, show its `title`, its `candidate_directions` (label + rationale), and its `clarification_question`.
   - Additionally offer a global scoping option (e.g. "Should research be limited to a particular technology stack, such as Azure only?").
   - STOP and WAIT for the user's answer. Do NOT start research before the user has responded.
   If no block needs clarification, skip this gate.

2. **Fix the research scope.** Incorporate the user's answers per block. For any block still ambiguous after the answer, use the user's chosen direction; never silently pick for the user.

3. **Research (DeepResearch tool).** For each block, invoke the DeepResearch tool with its `research_questions`, restricted to the confirmed direction(s) and honouring all `constraints`. Gather concrete technologies and best practices, each with a traceable source. Do NOT fabricate sources or findings. If research yields nothing usable for a block, record it as an open research question in chapter 6 rather than inventing an answer.

4. **Converge.** For each block, select EXACTLY ONE recommended technology/approach. Show the compared options only to justify the choice — never leave the choice open. Verify each recommendation complies with the block's `constraints`; a recommendation that violates a hard constraint is not allowed.

5. **Consolidate.** Integrate all per-block recommendations into ONE coherent target architecture (chapter 4). Show how the parts integrate and how the non-functional targets are met.

6. **Write the Markdown** following the template chapters:
   1. Research Approach and Scope — method, which research questions were addressed, any user scoping.
   2. Solution Landscape Overview — target-architecture vision, how blocks interact.
   3. Solution Blocks in Detail — one `### 3.x` per block: addressed requirements, technology-options table (Option | Maturity | Fit to criteria | Advantages/Disadvantages | Source), best practices (cited), and exactly one Recommendation with justification against `evaluation_criteria` and `addressed_requirements`.
   4. Consolidated Solution Proposal — the single unambiguous target architecture, integration view, NFR fulfilment.
   5. Technology Stack Overview — table Solution block → recommended technology → role.
   6. Assumptions, Risks and Open Research Questions.
   7. Sources — every cited source with reference/URL, keyed [S1], [S2], ...

Output:
- Output ONLY the Markdown content of the proposal. No JSON wrapping, no code fences around the whole output, no `[EXAMPLE]` markers, no HTML comments.
- The authoritative deliverable is `SolutionProposalResult.md`. Save the Markdown to that file (UTF-8) via the Code Interpreter and upload it back into the context.

Tweak:
- REMINDER: The clarification gate in step 1 is mandatory whenever a block has `needs_clarification: true`. Never skip it and never research before the user answers.
- CRITICAL: The final proposal is unambiguous — exactly one recommendation per block and one consolidated architecture. Options appear only as justification.
- Every recommendation must trace to `evaluation_criteria`, `addressed_requirements`, and at least one cited source.
- Respect all `constraints` from the catalogue as hard limits.
- Do NOT invent technologies or sources. Cite every external claim with [Sn].
- Apply the language rule: translate ALL headings, table headers, and prose into `output_language`.
```

- [ ] **Step 2: Konsistenz-Check ausführen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
for token in SolutionCatalogResult.json solution_proposal_output.md SolutionProposalResult.md "DeepResearch tool" needs_clarification "Clarification gate" "WAIT" "EXACTLY ONE" constraints output_language; do
  grep -q -- "$token" prompts/solution_proposal.md || echo "MISSING: $token"
done
echo "check done"
```
Expected: nur `check done`.

- [ ] **Step 3: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/prompts/solution_proposal.md
git commit -m "ENH proposalgenerator: add solution_proposal prompt with DeepResearch + HITL gate"
```

---

### Task 5: plan.json — Solution-Phase verdrahten

**Files:**
- Modify: `docs/.adesso/skills/proposalgenerator/plan.json`

**Interfaces:**
- Consumes: existierende `chain`-Struktur (Keys `PreProcessing`, `Mapping`, `Consolidation`, `Validation`).
- Produces: neuen Key `Solution` mit zwei Schritten; `Consolidation`-Proposal-Schritt erhält zwei zusätzliche `batch`-Einträge.

- [ ] **Step 1: `Solution`-Phase einfügen**

In `plan.json`, ersetze die Zeile `  "Mapping": [],` durch den folgenden Block (fügt die neue Phase direkt nach `PreProcessing` ein und behält `Mapping` bei):

```json
    "Solution": [
      {
        "step": 1,
        "name": "SolutionCatalog",
        "description": "Derive a solution catalogue: cluster functional/non-functional requirements into thematic solution blocks with research briefs and clarification flags.",
        "depends_on": "PreProcessing",
        "next": "SolutionProposal",
        "resources": {
          "prompt": "/prompts/solution_catalog.md",
          "output": "/schema/solution_catalog.json",
          "scripts": [],
          "assets": [],
          "references": [
            "/schema/solution_catalog.json"
          ],
          "batch": [
            "/preprocessing/Functional.json",
            "/preprocessing/Constraints.json",
            "/preprocessing/ClientContext.json"
          ],
          "artifacts": {}
        }
      },
      {
        "step": 2,
        "name": "SolutionProposal",
        "description": "Research technologies and best practices per solution block via the DeepResearch tool (with a mandatory user clarification gate for flagged blocks) and condense them into one unambiguous solution proposal.",
        "depends_on": "Solution",
        "next": null,
        "resources": {
          "prompt": "/prompts/solution_proposal.md",
          "output": "/schema/solution_proposal_output.md",
          "scripts": [],
          "assets": [],
          "references": [
            "/schema/solution_proposal_output.md"
          ],
          "batch": [
            "/solution/SolutionCatalog.json"
          ],
          "artifacts": {}
        }
      }
    ],
    "Mapping": [],
```

- [ ] **Step 2: Proposal-Schritt um die beiden Solution-Artefakte erweitern**

In `plan.json`, im `Consolidation`-Schritt `Proposal`, ergänze die `batch`-Liste um zwei Einträge nach `"/consolidation/OpenPoints.json"`:

```json
            "/consolidation/OpenPoints.json",
            "/solution/SolutionCatalog.json",
            "/solution/SolutionProposal.md"
```

- [ ] **Step 3: JSON-Gültigkeit und Referenz-Integrität prüfen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
python3 - <<'PY'
import json, os
plan = json.load(open('plan.json'))
sol = plan['chain']['Solution']
assert [s['name'] for s in sol] == ['SolutionCatalog', 'SolutionProposal'], sol
# referenced prompt/output files must exist on disk (paths are repo-relative with leading slash)
for step in sol:
    for key in ('prompt', 'output'):
        rel = step['resources'][key].lstrip('/')
        assert os.path.exists(rel), f"missing {rel}"
prop = [s for s in plan['chain']['Consolidation'] if s['name'] == 'Proposal'][0]
assert '/solution/SolutionCatalog.json' in prop['resources']['batch']
assert '/solution/SolutionProposal.md' in prop['resources']['batch']
print("OK: plan.json valid, Solution phase wired, prompt/output files exist")
PY
```
Expected: `OK: plan.json valid, Solution phase wired, prompt/output files exist`

- [ ] **Step 4: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/plan.json
git commit -m "ENH proposalgenerator: wire Solution phase into plan.json"
```

---

### Task 6: AGENT.md — Orchestrierung erweitern

**Files:**
- Modify: `docs/.adesso/skills/proposalgenerator/AGENT.md`

**Interfaces:**
- Consumes: bestehende Abschnitte `Workflow / Chain`, `Dependency Rule`, `Tender Document Access`, `User Interaction Rule`.
- Produces: neue Phase in der Workflow-Liste, DeepResearch-Ausnahme, HITL-Gate-Regel, Konvergenz-Regel, erweiterte Dependency-Regeln.

- [ ] **Step 1: Workflow-Chain um die Solution-Phase erweitern**

In `AGENT.md`, ersetze im Abschnitt `# Workflow / Chain` den Block `Phase 2 — Consolidation` durch:

```markdown
Phase 2 — Solution
6. SolutionCatalog → skill `proposal-solution-catalog` → `SolutionCatalogResult.json`
7. SolutionProposal → skill `proposal-solution-proposal` → `SolutionProposalResult.md`

Phase 3 — Consolidation
8. OpenPoints → skill `proposal-open-points` → `OpenPointsResult.json`
9. Report → skill `proposal-report` → `ReportResult.md`
10. Proposal → skill `proposal-proposal` → `ProposalResult.md`
```

Und ersetze im selben Abschnitt den `Export`-Block durch:

```markdown
Export
11. Convert `ProposalResult.md` to `Proposal.docx`
12. Convert `ReportResult.md` to `Report.pdf`
```

- [ ] **Step 2: Dependency-Regeln erweitern**

In `AGENT.md`, im Abschnitt `# Dependency Rule`, füge direkt nach der Zeile `Consolidation steps require all PreProcessing artifacts to exist first.` folgenden Absatz ein:

```markdown
Solution steps run after PreProcessing and before Consolidation:
- `proposal-solution-catalog` may only run after `FunctionalResult.json`, `ConstraintsResult.json`, and `ClientContextResult.json` exist.
- `proposal-solution-proposal` may only run after `SolutionCatalogResult.json` exists.
- `proposal-proposal` additionally consumes `SolutionCatalogResult.json` and `SolutionProposalResult.md`.
```

- [ ] **Step 3: DeepResearch-Ausnahme in der Tender-Zugriffsregel verankern**

In `AGENT.md`, im Abschnitt `# Tender Document Access`, füge am Ende (nach `They may only be passed to the bound skills so those skills can retrieve the content themselves.`) hinzu:

```markdown

External research via the DeepResearch tool is permitted **only** in the `proposal-solution-proposal` step, and only for technology and best-practice research — never for analysing the tender document. All tender content remains RAG-only.
```

- [ ] **Step 4: HITL-Gate und Konvergenz in der User-Interaction-Regel verankern**

In `AGENT.md`, im Abschnitt `# User Interaction Rule`, füge nach `Do not ask whether you should use the workflow.` und der Folgezeile `You must use the workflow.` folgenden Absatz ein:

```markdown

Exception — mandatory clarification gate: in the `proposal-solution-proposal` step, when the solution catalogue flags blocks with `needs_clarification: true`, you MUST ask the user which technology directions to research (and offer to scope the research) BEFORE invoking the DeepResearch tool, and wait for the answer. This is the one point where asking is required rather than discouraged.

Convergence rule: the final solution proposal must present exactly one recommended technology per solution block and one consolidated target architecture — never leave an open technology choice for the client.
```

- [ ] **Step 5: Konsistenz-Check ausführen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
for token in "Phase 2 — Solution" "proposal-solution-catalog" "proposal-solution-proposal" "SolutionCatalogResult.json" "SolutionProposalResult.md" "DeepResearch tool" "clarification gate" "Convergence rule" "Phase 3 — Consolidation"; do
  grep -q -- "$token" AGENT.md || echo "MISSING: $token"
done
echo "check done"
```
Expected: nur `check done`.

- [ ] **Step 6: Commit**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/AGENT.md
git commit -m "ENH proposalgenerator: orchestrate Solution phase, DeepResearch + HITL gate in AGENT.md"
```

---

### Task 7: proposal.md — Lösungsvorschlag in Kap. 2.3 einspeisen

> **Hinweis:** Diese Integration ist laut Spec „geplant, final gemeinsam zu bestätigen". Vor dem Commit dieser Task kurz Rücksprache mit dem User halten, ob die Verdrahtung so gewünscht ist.

**Files:**
- Modify: `docs/.adesso/skills/proposalgenerator/prompts/proposal.md`

**Interfaces:**
- Consumes: bestehender `Context`-Input-Block und der Abschnitt `2.3 Technical Solution and Architecture`.
- Produces: zwei zusätzliche Input-Artefakte im Context; 2.3 nutzt `SolutionProposalResult.md` als bevorzugte Quelle.

- [ ] **Step 1: Input-Liste im Context ergänzen**

In `prompts/proposal.md`, im `Context`-Block nach der Zeile für `OpenPointsResult.json` (`- \`OpenPointsResult.json\` — gap analysis...`), füge hinzu:

```markdown
- `SolutionCatalogResult.json` — solution blocks (needs, addressed requirements, constraints, evaluation criteria). Conforms to `solution_catalog.json`.
- `SolutionProposalResult.md` — the researched, unambiguous solution proposal (one recommended technology per block plus a consolidated target architecture, with cited sources).
```

- [ ] **Step 2: Kap. 2.3 auf den Lösungsvorschlag stützen**

In `prompts/proposal.md`, im Abschnitt `2.3 **Technical Solution and Architecture**`, füge als erste Aufzählungszeile (vor `- Propose a high-level technical architecture...`) ein:

```markdown
- Use `SolutionProposalResult.md` as the authoritative source for the technical architecture: adopt its consolidated target architecture and the one recommended technology per solution block. Do NOT introduce alternative technologies or re-open decisions already made there. Summarise (do not restate the full research) and reference the recommendations.
```

- [ ] **Step 3: Konsistenz-Check ausführen**

Run:
```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator
for token in "SolutionProposalResult.md" "SolutionCatalogResult.json"; do
  grep -q -- "$token" prompts/proposal.md || echo "MISSING: $token"
done
echo "check done"
```
Expected: nur `check done`.

- [ ] **Step 4: Commit (erst nach User-Bestätigung)**

```bash
cd /home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting
git add configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/prompts/proposal.md
git commit -m "ENH proposalgenerator: feed SolutionProposalResult into proposal chapter 2.3"
```

---

## Self-Review (durchgeführt)

**Spec coverage:**
- Lösungskatalog (JSON, deterministisch, Functional+Constraints+ClientContext) → Task 1 (Schema) + Task 2 (Prompt). ✓
- Gruppierte Lösungsbausteine + Rechercheauftrag → `solution_blocks`/`research_questions` (Task 1/2). ✓
- Unsicherheits-Flags (multiple_directions/low_confidence/insufficient_constraints) → Schema + Prompt-Regel (Task 1/2). ✓
- DeepResearch-Recherche + Best Practices mit Quellen → Task 4. ✓
- HITL-Rückfrage-Gate vor Recherche → Task 4 (Prompt) + Task 6 (AGENT.md). ✓
- Konvergenz auf genau eine Lösung → Task 4 + Task 6 (Convergence rule). ✓
- Frei gewählte Kapitelstruktur (7 Kapitel) → Task 3 (Template) + Task 4 (Prompt). ✓
- Neue Phase + Chain-Verdrahtung → Task 5 (plan.json) + Task 6 (AGENT.md). ✓
- Einspeisung in Proposal 2.3 (geplant/zu bestätigen) → Task 7 (mit Bestätigungshinweis). ✓
- DeepResearch nur in diesem Schritt erlaubt (Kontrast zu RAG-only) → Task 6 Step 3. ✓

**Placeholder scan:** Keine offenen TODO/TBD; alle Datei-Inhalte und Kommandos vollständig ausgeschrieben.

**Type consistency:** Feldnamen (`solution_blocks`, `needs_clarification`, `clarification_reason`, `candidate_directions`, `research_questions`, `evaluation_criteria`, `coverage.uncovered_requirement_ids`) sind über Schema (Task 1), Katalog-Prompt (Task 2) und Proposal-Prompt (Task 4) identisch verwendet. Artefaktnamen konsistent: `SolutionCatalogResult.json` / `SolutionProposalResult.md` in AGENT.md+Prompts, `/solution/SolutionCatalog.json` / `/solution/SolutionProposal.md` in plan.json (bewusste, dokumentierte Konvention).

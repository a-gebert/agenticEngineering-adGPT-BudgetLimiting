# proposalgenerator-Chain — Gewinner-Angleichung: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die `proposalgenerator`-Prompt-Chain um adaptive Kapitelstruktur, Produkt-/UX-Design, adesso-Institutionswissen und tenderkonforme Tech-Übernahme erweitern (Basis: Design `2026-07-23-proposal-chain-winner-alignment-design.md`).

**Architecture:** Zwei neue Chain-Steps (`ProductDesign` in Phase Solution, `ProposalOutline` in Phase Consolidation), eine kuratierte Wissens-Referenzdatei, Edits an fünf bestehenden Prompts, Verdrahtung in `plan.json` + `AGENT.md`. Jeder Step = Prompt (Context/Role/Action/Output-Validation/Tweak-Struktur) + JSON-Schema (draft 2020-12), Output via Code Interpreter validiert und als `<Step>Result.json` hochgeladen.

**Tech Stack:** Markdown-Prompts, JSON Schema (2020-12), `plan.json`-Chain-Definition, `AGENT.md`-Orchestrierungsvertrag. Reine Konfiguration/Prompting — kein Applikationscode.

## Global Constraints

- **Skill-Wurzel:** `/home/gebert/adgpt/agenticEngineering-adGPT-BudgetLimiting/configs/proposal-skill/app/docs/.adesso/skills/proposalgenerator/` (unten: `<ROOT>`).
- **Prompts auf Englisch** verfassen; menschenlesbare Ausgabefelder nutzen `output_language` (Default `en`).
- **Prompt-Struktur** exakt wie Bestand: Abschnitte `Context / Role / Emotion/Tone / Action / Output & Validation (Code Interpreter) / Tweak`.
- **Schema:** JSON Schema draft 2020-12, `"additionalProperties": false` überall, `$schema` + `$id` + `title` + `description`, `required`-Array.
- **Determinismus vor Hilfsbereitschaft** (AGENT.md Determinism-Rule): keine Faktenerfindung; jede inhaltliche Aussage muss auf ein Artefakt-Zitat oder `adesso_facts.md` rückführbar sein.
- **Anonymisierung bleibt voll aktiv** — keine Personen-/Kundennamen einführen. Klarnamen-Konflikt (Finding 4) bleibt bewusst ungelöst.
- **Kein Commit ohne ausdrückliche Aufforderung** des Nutzers.
- Alle Ausgabe-Artefakte werden via Code Interpreter mit `jsonschema` (draft 2020-12) validiert, als `<Step>Result.json` (UTF-8, pretty) geschrieben, in den Context hochgeladen. Datei = reines JSON, keine Markdown-Fences.

---

### Task 1: adesso-Wissens-Referenzdatei

**Files:**
- Create: `<ROOT>/references/adesso_facts.md`

**Interfaces:**
- Consumes: nichts (statische Datenquelle).
- Produces: kuratierte adesso-Institutionsfakten, referenziert von Task 5 (`executive_summary.md`) und Task 7 (`proposal.md`). Feste Abschnitts-Anker (H2-Headings), damit Prompts gezielt zitieren können: `## Company Profile`, `## Certifications`, `## Delivery Methodology`, `## Quality Management`, `## Application Management & SLA`, `## Locations & Organisation`.

- [ ] **Step 1: Referenzdatei mit fixer Abschnittsstruktur anlegen**

Inhalt (kuratiert, versioniert — Platzhalterwerte klar als solche markiert, wo echte Zahlen fehlen; KEINE erfundenen Zahlen):

```markdown
# adesso Institutional Facts (curated reference)

> Curated, versioned source of adesso company/institutional facts for proposal
> generation. Prompts may cite ONLY from this file for adesso facts — never invent.
> Maintainer: keep financial figures current. Last reviewed: 2026-07-23.

## Company Profile
- Founded: 25+ years of market presence.
- Positioning: IT service provider, industry-focused delivery.
- <!-- MAINTAIN: revenue, EBITDA (last 4 years), employee count — fill with
     approved figures before use; leave blank rather than estimate. -->

## Certifications
- ISO 9001 (Quality Management)
- ISO 14001 (Environmental Management)
- ISO/IEC 27001 (Information Security Management)

## Delivery Methodology
- Maître concept: dedicated delivery-lead role owning client outcome.
- adVANTAGE: budget-control / agile-billing model.
- JourFixe: recurring structured client sync.
- Dedicated monitoring team for operations.

## Quality Management
- ISTQB-aligned test approach.
- Test pyramid (unit / integration / system / acceptance).
- Quality gates per increment.

## Application Management & SLA
- Priority model Prio I–IV with defined reaction/resolution targets.
- <!-- MAINTAIN: concrete SLA reaction/resolution times per priority. -->

## Locations & Organisation
- Multiple branch offices (EU focus).
- <!-- MAINTAIN: current branch count and org structure. -->
```

- [ ] **Step 2: Datei-Struktur verifizieren**

Run:
```bash
grep -c '^## ' "<ROOT>/references/adesso_facts.md"
```
Expected: `6` (sechs H2-Abschnitte, exakt die Anker aus dem Interfaces-Block).

- [ ] **Step 3: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/references/adesso_facts.md
git commit -m "feat(proposalgenerator): add curated adesso institutional facts reference"
```

---

### Task 2: ProductDesign-Step (Schema + Prompt)

**Files:**
- Create: `<ROOT>/schema/product_design.json`
- Create: `<ROOT>/prompts/product_design.md`

**Interfaces:**
- Consumes: `FunctionalResult.json` (User Stories / FR/NFR mit `aspect_id`), `SolutionProposalResult.md` (Tech-Kontext).
- Produces: `ProductDesignResult.json` conforming to `product_design.json`. Downstream: Task 3 (`ProposalOutline` liest es als Evidenz für die Produkt/UX-Dimension), Task 7 (`proposal.md` rendert das UX-Kapitel daraus).

- [ ] **Step 1: JSON-Schema schreiben**

`<ROOT>/schema/product_design.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/schemas/product-design.schema.json",
    "title": "ProductDesign",
    "description": "Screen-by-screen feature and interaction design derived from functional requirements. Each screen behaviour must trace back to a functional requirement.",
    "type": "object",
    "additionalProperties": false,
    "properties": {
        "document_id": {
            "type": "string",
            "description": "Optional ID of the source document."
        },
        "screens": {
            "type": "array",
            "description": "The screens / views of the product, each with derived interaction behaviour.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "screen_id": {
                        "type": "string",
                        "description": "Unique ID of the screen, e.g. scr-1."
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable screen/view name."
                    },
                    "purpose": {
                        "type": "string",
                        "description": "What the user accomplishes on this screen."
                    },
                    "interactions": {
                        "type": "array",
                        "description": "Concrete interaction behaviours on this screen.",
                        "items": {
                            "type": "object",
                            "additionalProperties": false,
                            "properties": {
                                "trigger": {
                                    "type": "string",
                                    "description": "User action, e.g. 'clicks Add'."
                                },
                                "reaction": {
                                    "type": "string",
                                    "description": "System/UI response, e.g. 'opens a menu with N options'."
                                },
                                "result_state": {
                                    "type": "string",
                                    "description": "Resulting state after the reaction."
                                },
                                "requirement_ids": {
                                    "type": "array",
                                    "description": "Functional requirement IDs this interaction is derived from. MUST be non-empty — no invented behaviour.",
                                    "minItems": 1,
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": [
                                "trigger",
                                "reaction",
                                "requirement_ids"
                            ]
                        }
                    }
                },
                "required": [
                    "screen_id",
                    "name",
                    "purpose",
                    "interactions"
                ]
            }
        },
        "total_screens": {
            "type": "integer",
            "description": "Number of screens."
        },
        "errors": {
            "type": "array",
            "description": "Validation or processing errors.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "code": {
                        "type": "string"
                    },
                    "message": {
                        "type": "string"
                    },
                    "severity": {
                        "type": "string",
                        "enum": [
                            "info",
                            "warning",
                            "error"
                        ]
                    }
                },
                "required": [
                    "code",
                    "message"
                ]
            }
        }
    },
    "required": [
        "screens",
        "total_screens"
    ]
}
```

- [ ] **Step 2: Schema-Wohlgeformtheit prüfen**

Run:
```bash
python3 -c "import json,jsonschema; s=json.load(open('<ROOT>/schema/product_design.json')); jsonschema.Draft202012Validator.check_schema(s); print('schema OK')"
```
Expected: `schema OK`

- [ ] **Step 3: Prompt schreiben**

`<ROOT>/prompts/product_design.md` — Struktur wie Bestand. Kern-Inhalt:

```markdown
Context:
Input = artifacts from prior Solution chain steps. This ProductDesign step does
**not** re-read the tender document; it derives from prior JSON/MD artifacts:

- `FunctionalResult.json` — functional + non-functional requirements (user
  stories), each linked to an aspect via `aspect_id`. Conforms to
  `functional_requirements.json`.
- `SolutionProposalResult.md` — the recommended target architecture and
  technology per solution block. Context only; do not restate tech choices.

Task: produce a screen-by-screen product / UX design — the behavioural narrative
a winning proposal's "User Interface" chapter is built from (screens, menus,
workflow states, interaction rules). Every behaviour MUST be derived from one or
more functional requirements.

Output language = `output_language` parameter (default English).

Role:
Act as a senior product designer / business analyst. Translate user stories into
concrete, plausible screen behaviour without inventing scope beyond the
requirements.

Emotion/Tone:
Concrete, product-oriented, decisive. Describe behaviour ("clicking Add opens a
menu with N options"), not implementation.

Action:
1. Group functional requirements into coherent screens/views. Each screen gets a
   `screen_id` (scr-1, scr-2, …), `name`, `purpose`.
2. For each screen, derive concrete `interactions`: `trigger` (user action) →
   `reaction` (system/UI response) → `result_state`.
3. For EVERY interaction, set `requirement_ids` to the FunctionalResult
   requirement IDs it derives from. This array MUST be non-empty. If you cannot
   trace an interaction to a requirement, DROP it — never invent behaviour.
4. Compute `total_screens`.

Output & Validation (Code Interpreter):
1. Load `FunctionalResult.json` (+ `SolutionProposalResult.md` for context).
   Compute the design in memory per the rules above.
2. Load `product_design.json` schema, validate draft with `jsonschema`
   (draft 2020-12). Fix violations and re-validate until clean.
3. If a required value is genuinely absent, add an `errors` entry
   (`code`, `message` in `output_language`, `severity`) and keep the object
   otherwise schema-conformant.
4. Write validated object to `ProductDesignResult.json` (UTF-8, pretty-printed),
   upload back into context.

Tweak:
- Authoritative deliverable = `ProductDesignResult.json`, valid JSON only, no
  markdown fences, no commentary.
- Do NOT invent screens or interactions without a `requirement_ids` link.
- Do NOT restate technology choices from SolutionProposal — describe behaviour.
- Use `output_language` for all human-readable fields.
- If there are no UI-bearing requirements, return an empty `screens` array with
  `total_screens: 0` and note it in `errors`.
```

- [ ] **Step 4: Prompt-Pflichtklauseln prüfen**

Run:
```bash
grep -Eic 'requirement_ids|ProductDesignResult.json|never invent|output_language' "<ROOT>/prompts/product_design.md"
```
Expected: Zahl `>= 4` (jede Pflichtklausel mindestens einmal vorhanden).

- [ ] **Step 5: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/schema/product_design.json docs/.adesso/skills/proposalgenerator/prompts/product_design.md
git commit -m "feat(proposalgenerator): add ProductDesign step (screen-by-screen UX narrative)"
```

---

### Task 3: ProposalOutline-Step (Schema + Prompt)

**Files:**
- Create: `<ROOT>/schema/proposal_outline.json`
- Create: `<ROOT>/prompts/proposal_outline.md`

**Interfaces:**
- Consumes: alle vorhandenen Artefakte — `ClientContextResult.json`, `FunctionalResult.json`, `FormalResult.json`, `ConstraintsResult.json`, `SolutionCatalogResult.json`, `SolutionProposalResult.md`, `ProductDesignResult.json`, `StaffingCatalogResult.json`, `ProfilerMatchResult.json`, `EstimationResult.json`, `ExecutiveSummaryResult.json`, `OpenPointsResult.json`.
- Produces: `ProposalOutlineResult.json` conforming to `proposal_outline.json`. Downstream: Task 7 (`proposal.md` rendert Kapitel ausschließlich aus dem `outline`-Array mit Status `activate`/`present`).

- [ ] **Step 1: JSON-Schema schreiben**

`<ROOT>/schema/proposal_outline.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/schemas/proposal-outline.schema.json",
    "title": "ProposalOutline",
    "description": "Adaptive proposal chapter outline. Evaluates each standard winning-proposal dimension against artifact evidence and marks it present / activate / n/a. proposal.md renders from this outline.",
    "type": "object",
    "additionalProperties": false,
    "$defs": {
        "dimensionStatus": {
            "type": "string",
            "enum": [
                "present",
                "activate",
                "n/a"
            ],
            "description": "present = baseline chapter always rendered; activate = conditional chapter enabled by evidence; n/a = not applicable for this tender."
        }
    },
    "properties": {
        "dimensions": {
            "type": "array",
            "description": "Every rubric dimension with its status decision and evidence.",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "dimension": {
                        "type": "string",
                        "description": "Rubric dimension key, e.g. 'Transition/Migration'."
                    },
                    "status": {
                        "$ref": "#/$defs/dimensionStatus"
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this status was chosen."
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Artifact citation supporting the decision (e.g. 'FunctionalResult req F-12: data migration'). Required unless status is 'n/a'."
                    }
                },
                "required": [
                    "dimension",
                    "status",
                    "rationale"
                ]
            }
        },
        "outline": {
            "type": "array",
            "description": "Ordered list of chapters to render (only dimensions with status present or activate).",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "order": {
                        "type": "integer",
                        "description": "1-based render order."
                    },
                    "heading": {
                        "type": "string",
                        "description": "Chapter heading."
                    },
                    "purpose": {
                        "type": "string",
                        "description": "What this chapter must accomplish."
                    },
                    "source_artifacts": {
                        "type": "array",
                        "description": "Artifacts feeding this chapter.",
                        "items": {
                            "type": "string"
                        }
                    },
                    "target_length": {
                        "type": "string",
                        "description": "Rough target length, e.g. 'short', 'medium', '1-2 pages'."
                    }
                },
                "required": [
                    "order",
                    "heading",
                    "purpose",
                    "source_artifacts"
                ]
            }
        },
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                    "code": {
                        "type": "string"
                    },
                    "message": {
                        "type": "string"
                    },
                    "severity": {
                        "type": "string",
                        "enum": [
                            "info",
                            "warning",
                            "error"
                        ]
                    }
                },
                "required": [
                    "code",
                    "message"
                ]
            }
        }
    },
    "required": [
        "dimensions",
        "outline"
    ]
}
```

- [ ] **Step 2: Schema-Wohlgeformtheit prüfen**

Run:
```bash
python3 -c "import json,jsonschema; s=json.load(open('<ROOT>/schema/proposal_outline.json')); jsonschema.Draft202012Validator.check_schema(s); print('schema OK')"
```
Expected: `schema OK`

- [ ] **Step 3: Prompt schreiben**

`<ROOT>/prompts/proposal_outline.md` — Kern-Inhalt (Rubrik, Baseline, Trigger-Tabelle):

```markdown
Context:
Input = ALL prior chain artifacts (PreProcessing, Solution, and the earlier
Consolidation steps ExecutiveSummary + OpenPoints). This ProposalOutline step
does **not** re-read the tender document; it decides the proposal's chapter
structure from artifact evidence only. It runs after Report and before Proposal.

Consumed artifacts (skip any absent, note in `errors`):
- ClientContextResult.json, FunctionalResult.json, FormalResult.json,
  ConstraintsResult.json, SolutionCatalogResult.json, SolutionProposalResult.md,
  ProductDesignResult.json, StaffingCatalogResult.json, ProfilerMatchResult.json,
  EstimationResult.json, ExecutiveSummaryResult.json, OpenPointsResult.json.

Task: for each rubric dimension, decide status `present` / `activate` / `n/a`
with rationale and (unless n/a) an artifact citation as evidence. Then emit an
ordered `outline` of the chapters to render. Same pattern as OpenPoints
(gap analysis) but on STRUCTURE, not requirements.

Output language = `output_language` (default English).

Role:
Act as a senior bid manager deciding which chapters a winning proposal needs for
THIS tender, justified strictly by available evidence.

Emotion/Tone:
Decisive, evidence-bound. No chapter without justification.

Action:
1. Rubric dimensions (evaluate every one):
   Executive Summary, Architecture, Product/UX, Business Logic, Import/Export,
   Non-functional, Methodology/SCRUM, Quality Management, Application
   Management & SLA, Transition/Migration, Compliance List, Key Personnel,
   Company Background/References, Price, Terms & Conditions, Risk.
2. Baseline set — ALWAYS `present` (determinism guarantee):
   Executive Summary, Architecture, Price, Terms & Conditions.
3. Conditional-chapter triggers — set `activate` ONLY if evidence holds:
   | Dimension | Activate when |
   |---|---|
   | Product/UX | ProductDesignResult.json has non-empty `screens` |
   | Transition/Migration | migration requirement in Functional/Constraints |
   | Application Management & SLA | NFR availability/support present |
   | Risk | high-severity item in OpenPoints or Constraints |
   | Compliance List | binding formal requirement present |
   Other dimensions: `present` if a feeding artifact exists, else `n/a`.
4. For every dimension set `rationale`; for non-`n/a` set `evidence` = a concrete
   artifact citation. No evidence → do NOT activate.
5. Build `outline`: one entry per `present`/`activate` dimension, in a sensible
   proposal order, with `heading`, `purpose`, `source_artifacts`, `target_length`.

Output & Validation (Code Interpreter):
1. Load available artifacts, compute decisions in memory per the rules above.
2. Load `proposal_outline.json` schema, validate with `jsonschema`
   (draft 2020-12). Fix and re-validate until clean.
3. Genuinely-absent required values → add `errors` entry, keep object conformant.
4. Write validated object to `ProposalOutlineResult.json` (UTF-8, pretty),
   upload back into context.

Tweak:
- Authoritative deliverable = `ProposalOutlineResult.json`, valid JSON only.
- Baseline dimensions MUST always appear with status `present`.
- Never `activate` a conditional chapter without an `evidence` citation.
- `outline` contains ONLY `present`/`activate` dimensions, never `n/a`.
- Use `output_language` for human-readable fields.
```

- [ ] **Step 4: Prompt-Pflichtklauseln prüfen**

Run:
```bash
grep -Eic 'Baseline|activate|evidence|ProposalOutlineResult.json' "<ROOT>/prompts/proposal_outline.md"
```
Expected: Zahl `>= 4`.

- [ ] **Step 5: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/schema/proposal_outline.json docs/.adesso/skills/proposalgenerator/prompts/proposal_outline.md
git commit -m "feat(proposalgenerator): add ProposalOutline step (adaptive chapter structure)"
```

---

### Task 4: Solution-Paradigma — Tender-Re-Read + vorgeschriebene Tech

**Files:**
- Modify: `<ROOT>/prompts/solution_catalog.md`
- Modify: `<ROOT>/prompts/solution_proposal.md`

**Interfaces:**
- Consumes: unverändert (Functional/Constraints/ClientContext bzw. SolutionCatalog).
- Produces: `SolutionCatalogResult.json` / `SolutionProposalResult.md` — jetzt mit erhaltenen tender-vorgeschriebenen Tech-Vorgaben und, wo vom Tender vorgegeben, konkreten Produktnamen.

- [ ] **Step 1: Bestehende Prompts lesen**

Run:
```bash
sed -n '1,200p' "<ROOT>/prompts/solution_catalog.md"; echo "==="; sed -n '1,200p' "<ROOT>/prompts/solution_proposal.md"
```
Erwartung: die aktuellen Regeln sichten, insbesondere das Produktnamen-Verbot in `solution_catalog.md` und den Web-only-Research-Scope in `solution_proposal.md`.

- [ ] **Step 2: `solution_catalog.md` — Tender-Re-Read + gelockertes Produktnamen-Verbot**

Ergänze im `Action`-Abschnitt eine Klausel (Wortlaut anpassen an bestehende Nummerierung):

```markdown
- Tender-prescribed technology: where the tender explicitly mandates a concrete
  technology or product (e.g. an existing database, a named PDF toolkit, a fixed
  export format), re-read that constraint from the requirement artifacts and
  carry it verbatim into the relevant solution block as a fixed input — do not
  turn it into an open option.
```

Ersetze die absolute Produktnamen-Verbots-Regel im `Tweak`-Abschnitt durch die abgegrenzte Fassung:

```markdown
- Concrete product/vendor names are allowed ONLY where the tender itself
  prescribes them (mark such blocks `tender_mandated: true` in the research
  brief). For all OTHER, open blocks, stay vendor-neutral — no product names.
```

- [ ] **Step 3: `solution_proposal.md` — entschiedene Übernahme ohne Zitatenzwang**

Ergänze im `Action`-Abschnitt:

```markdown
- For solution blocks marked `tender_mandated: true`, adopt the prescribed
  technology decisively as the recommended choice. Do NOT run a web option
  comparison and do NOT attach `[Sn]` research citations for these — the tender
  is the source. Web research applies ONLY to blocks that are genuinely open.
```

Die Konvergenz-Regel (genau eine empfohlene Tech je Block, eine Zielarchitektur) bleibt unverändert.

- [ ] **Step 4: Änderungen verifizieren**

Run:
```bash
grep -Eic 'tender.?mandated|prescribe' "<ROOT>/prompts/solution_catalog.md" && grep -Eic 'tender.?mandated|do not run a web option comparison|decisively' "<ROOT>/prompts/solution_proposal.md"
```
Expected: beide Zahlen `>= 1`.

- [ ] **Step 5: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/prompts/solution_catalog.md docs/.adesso/skills/proposalgenerator/prompts/solution_proposal.md
git commit -m "feat(proposalgenerator): re-read tender tech and adopt prescribed technologies decisively"
```

---

### Task 5: executive_summary.md — adesso-Fakten + Preisbegründung

**Files:**
- Modify: `<ROOT>/prompts/executive_summary.md`

**Interfaces:**
- Consumes: zusätzlich `references/adesso_facts.md` (Task 1) und `EstimationResult.json` (für Preis-Modell-Rationale).
- Produces: `ExecutiveSummaryResult.json` — jetzt mit adesso-Institutionsbezug (Maître, Mission) und Preisbegründung.

- [ ] **Step 1: Bestehenden Prompt lesen**

Run:
```bash
sed -n '1,200p' "<ROOT>/prompts/executive_summary.md"
```

- [ ] **Step 2: adesso-Fakten + Preisbegründung ergänzen**

Ergänze im `Context`-Abschnitt die neue Quelle:

```markdown
- `references/adesso_facts.md` — curated adesso institutional facts. You may cite
  adesso facts (Maître concept, mission fit, methodology) ONLY from this file.
  Never invent company facts.
```

Ergänze im `Action`-Abschnitt:

```markdown
- Weave in adesso's delivery differentiators from `adesso_facts.md` (e.g. Maître
  concept) where they support the mission fit — cite only facts present there.
- Include a brief price-model rationale (fixed-price / T&M reasoning) consistent
  with the engagement; do not restate figures from the price table.
```

- [ ] **Step 3: Verifizieren**

Run:
```bash
grep -Eic 'adesso_facts.md|Maître|price-model rationale' "<ROOT>/prompts/executive_summary.md"
```
Expected: `>= 2`.

- [ ] **Step 4: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/prompts/executive_summary.md
git commit -m "feat(proposalgenerator): cite adesso facts and price rationale in executive summary"
```

---

### Task 6: estimator.md — Preis-Cleanup

**Files:**
- Modify: `<ROOT>/prompts/estimator.md`

**Interfaces:**
- Consumes: unverändert.
- Produces: `EstimationResult.json` — Rollentabelle bleibt, aber ohne `"XXX"`-Platzhalter-Tagessätze; Zahlungsziel 60 Tage.

- [ ] **Step 1: Bestehenden Prompt lesen**

Run:
```bash
grep -n 'XXX\|payment\|Zahlungsziel\|10 day\|10 Tage\|day rate\|Tagessatz' "<ROOT>/prompts/estimator.md"
```
Erwartung: die Stellen finden, an denen `"XXX"`-Tagessätze und das Zahlungsziel gesetzt werden.

- [ ] **Step 2: Platzhalter + Zahlungsziel korrigieren**

- Ersetze die `"XXX"`-Tagessatz-Anweisung: entweder ein tatsächliches Tagessatz-Feld (falls verfügbar) oder Tagessatz/Summen leer lassen statt `"XXX"` einzusetzen; Regel im Prompt:

```markdown
- Do NOT emit placeholder day rates such as "XXX". If a day rate is not
  available, leave the rate/total field empty (or omit it) rather than inserting
  a placeholder token.
```

- Setze das Zahlungsziel auf 60 Tage (Wortlaut an vorhandene Formulierung anpassen):

```markdown
- Payment term defaults to 60 days (net) unless the tender/constraints specify
  otherwise.
```

- [ ] **Step 3: Verifizieren**

Run:
```bash
grep -c 'XXX' "<ROOT>/prompts/estimator.md"; grep -Eic '60 day|60 Tage' "<ROOT>/prompts/estimator.md"
```
Expected: erste Zahl `0` bzw. nur noch in der Negativ-Regel ("do NOT emit ... XXX"); zweite Zahl `>= 1`. Falls `XXX` außerhalb der Negativ-Regel noch vorkommt → weiter entfernen.

- [ ] **Step 4: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/prompts/estimator.md
git commit -m "fix(proposalgenerator): drop XXX day-rate placeholders, set 60-day payment term"
```

---

### Task 7: proposal.md — Outline-gesteuertes Rendering + Kapitel-Bausteine

**Files:**
- Modify: `<ROOT>/prompts/proposal.md`

**Interfaces:**
- Consumes: zusätzlich `ProposalOutlineResult.json` (Task 3, steuert Kapitelstruktur), `ProductDesignResult.json` (Task 2, Produkt/UX-Kapitel), `references/adesso_facts.md` (Task 1, Firmenprofil-Tiefe).
- Produces: `ProposalResult.md` — Kapitel gemäß Outline, Fließtext-Narrativ statt FR/NFR-Tabelle, bedingte Bausteine, entschiedener Scoping-Ton, Preis-Cleanup.

- [ ] **Step 1: Bestehenden Prompt lesen**

Run:
```bash
sed -n '1,300p' "<ROOT>/prompts/proposal.md"
```
Erwartung: aktuelle feste Struktur, Requirements-Tabelle in 2.2, Preiskapitel, Deferier-Ton verorten.

- [ ] **Step 2: Outline-gesteuertes Rendering einführen**

Ergänze im `Context`-Abschnitt die neuen Quellen und im `Action`-Abschnitt die zentrale Render-Regel:

```markdown
- `ProposalOutlineResult.json` — the adaptive chapter outline. RENDER CHAPTERS
  STRICTLY FROM its `outline` array, in `order`. Do not render a fixed built-in
  chapter list; do not add chapters absent from the outline; do not drop chapters
  present in it. Each outline entry's `heading`/`purpose`/`source_artifacts`
  drives one proposal chapter.
- `ProductDesignResult.json` — feeds the Product/UX chapter (screen-by-screen
  behaviour) when that dimension is in the outline.
- `references/adesso_facts.md` — company-profile / methodology facts; cite ONLY
  from here for adesso facts, never invent.
```

- [ ] **Step 3: Requirements-Tabelle optional stellen + Fließtext-Narrativ**

Ersetze die Anweisung, FR/NFR als Tabelle ins Dokument zu kippen, durch:

```markdown
- Do NOT dump the FR/NFR requirements table into the client-facing proposal.
  Express requirement fulfilment as flowing feature narrative. A requirements/
  compliance table is rendered ONLY if the outline contains a "Compliance List"
  chapter (then keep it concise, ideally as a separate compliance section).
```

- [ ] **Step 4: Bedingte Kapitel-Bausteine ergänzen**

Füge Bausteine hinzu, die genutzt werden, WENN das jeweilige Kapitel im Outline steht:

```markdown
- Transition/Migration chapter (if in outline): cover delta-transition,
  read-only cutover, log-file handling — driven by migration requirements.
- Methodology/SCRUM chapter: describe the concrete SCRUM setup (roles,
  ceremonies, increments), not a generic agile blurb.
- Quality Management chapter: use the ISTQB / test-pyramid / quality-gate
  building blocks from `adesso_facts.md`.
- Application Management & SLA chapter: render the Prio I–IV SLA model as a
  table, sourced from `adesso_facts.md`.
- Company Background chapter: use `adesso_facts.md` for depth (certifications,
  methodology, organisation) — cite only facts present there.
```

- [ ] **Step 5: Entschiedener Scoping-Ton**

```markdown
- Scoping tone: where scope is bounded by a deliberate decision, state it
  decisively inline (e.g. "Sub-templates are out of scope for this proposal and
  will be clarified during implementation") instead of deferring everything to
  open-points/clarification. Reserve open-points framing for genuinely
  unresolved questions.
```

- [ ] **Step 6: Preis-Cleanup im Preiskapitel**

```markdown
- Price chapter: no "XXX" placeholder day rates (leave empty if unknown);
  payment term 60 days unless constraints say otherwise.
```

- [ ] **Step 7: Änderungen verifizieren**

Run:
```bash
grep -Eic 'ProposalOutlineResult.json|RENDER CHAPTERS STRICTLY FROM|ProductDesignResult.json|adesso_facts.md|flowing feature narrative|Prio I' "<ROOT>/prompts/proposal.md"
```
Expected: `>= 5`.

Run:
```bash
grep -c 'XXX' "<ROOT>/prompts/proposal.md"
```
Expected: nur innerhalb der Negativ-Regel (kein produktiver `"XXX"`-Platzhalter mehr).

- [ ] **Step 8: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/prompts/proposal.md
git commit -m "feat(proposalgenerator): render proposal from adaptive outline with conditional chapters"
```

---

### Task 8: Wiring — plan.json + AGENT.md

**Files:**
- Modify: `<ROOT>/plan.json`
- Modify: `<ROOT>/AGENT.md`

**Interfaces:**
- Consumes: die neuen Step-Prompts/Schemas (Task 2, 3) müssen existieren.
- Produces: lauffähige Chain — `ProductDesign` zwischen `SolutionProposal` und `StaffingCatalog`, `ProposalOutline` zwischen `Report` und `Proposal`.

- [ ] **Step 1: `plan.json` — ProductDesign in Solution einfügen**

- Neuer Eintrag in `chain.Solution` als `step 3` (vorherige Steps 3–5 werden 4–6).
- `SolutionProposal.next` von `"StaffingCatalog"` auf `"ProductDesign"` ändern.
- Neuer Eintrag `ProductDesign`: `next: "StaffingCatalog"`, `depends_on: "Solution"`, `prompt: "/prompts/product_design.md"`, `output: "/schema/product_design.json"`, `references: ["/schema/product_design.json"]`, `batch: ["/preprocessing/Functional.json", "/solution/SolutionProposal.md"]`.

```json
{
  "step": 3,
  "name": "ProductDesign",
  "description": "Derive a screen-by-screen product/UX design (feature and interaction behaviour) from the functional requirements; every behaviour traces to a requirement. No web research.",
  "depends_on": "Solution",
  "next": "StaffingCatalog",
  "resources": {
    "prompt": "/prompts/product_design.md",
    "output": "/schema/product_design.json",
    "scripts": [],
    "assets": [],
    "references": ["/schema/product_design.json"],
    "batch": ["/preprocessing/Functional.json", "/solution/SolutionProposal.md"],
    "artifacts": {}
  }
}
```

- [ ] **Step 2: `plan.json` — ProposalOutline in Consolidation einfügen**

- Neuer Eintrag in `chain.Consolidation` nach `Report`, vor `Proposal`.
- `Report.next` von `"Proposal"` auf `"ProposalOutline"` ändern.
- Neuer Eintrag `ProposalOutline`: `next: "Proposal"`, `depends_on: "PreProcessing"`, batch = alle Artefakte (analog `Proposal`-batch + `ProductDesign`).

```json
{
  "step": 4,
  "name": "ProposalOutline",
  "description": "Decide the adaptive proposal chapter structure: evaluate each rubric dimension against artifact evidence (present/activate/n/a), emit an ordered outline. Runs after Report, before Proposal.",
  "depends_on": "PreProcessing",
  "next": "Proposal",
  "resources": {
    "prompt": "/prompts/proposal_outline.md",
    "output": "/schema/proposal_outline.json",
    "scripts": [],
    "assets": [],
    "references": ["/schema/proposal_outline.json"],
    "batch": [
      "/consolidation/ExecutiveSummary.json",
      "/consolidation/OpenPoints.json",
      "/preprocessing/ClientContext.json",
      "/preprocessing/Functional.json",
      "/preprocessing/Formal.json",
      "/preprocessing/Constraints.json",
      "/solution/SolutionCatalog.json",
      "/solution/SolutionProposal.md",
      "/solution/ProductDesign.json",
      "/solution/StaffingCatalog.json",
      "/solution/ProfilerMatch.json",
      "/solution/Estimator.json"
    ],
    "artifacts": {}
  }
}
```

- Danach `Proposal`-Step: `step` auf `5` erhöhen und `ProposalOutline.json` zu seinem `batch` hinzufügen.

- [ ] **Step 3: `plan.json` — Wohlgeformtheit prüfen**

Run:
```bash
python3 -c "import json; d=json.load(open('<ROOT>/plan.json')); s=[x['name'] for x in d['chain']['Solution']]; c=[x['name'] for x in d['chain']['Consolidation']]; print('Solution:',s); print('Consolidation:',c); assert s.index('ProductDesign')==s.index('SolutionProposal')+1; assert c.index('ProposalOutline')==c.index('Report')+1 and c.index('ProposalOutline')<c.index('Proposal'); print('order OK')"
```
Expected: gültiges JSON, `order OK`.

- [ ] **Step 4: `AGENT.md` — Workflow-Liste + Dependency-Rule**

- Phase 2 (Solution): `ProductDesign` als Schritt 8 einschieben, `StaffingCatalog`/`ProfilerMatch`/`Estimator` auf 9–11 hochziehen.
- Phase 3 (Consolidation): `ProposalOutline` vor `Proposal` einschieben.
- Dependency-Rule ergänzen:

```markdown
- `proposal-product-design` runs only after `FunctionalResult.json` and
  `SolutionProposalResult.md` exist. No web research, no tender re-read.
- `proposal-proposal-outline` runs only after Report, and after all Solution +
  earlier Consolidation artifacts exist (ExecutiveSummary, OpenPoints,
  ProductDesign, …). Produces `ProposalOutlineResult.json`.
- `proposal-proposal` additionally consumes `ProductDesignResult.json` and
  `ProposalOutlineResult.json`; it renders chapters strictly from the outline.
```

- Im Abschnitt "Tender Document Access" die kuratierte Wissensquelle als erlaubte Ausnahme dokumentieren:

```markdown
adesso institutional facts are available ONLY via the curated reference file
`references/adesso_facts.md`, cited by the executive-summary and proposal steps.
This file is the sole permitted source for adesso company facts; inventing such
facts remains forbidden.
```

- [ ] **Step 5: AGENT.md-Konsistenz prüfen**

Run:
```bash
grep -Eic 'product-design|proposal-outline|adesso_facts.md|renders chapters strictly from the outline' "<ROOT>/AGENT.md"
```
Expected: `>= 3`.

- [ ] **Step 6: Commit**

```bash
git add docs/.adesso/skills/proposalgenerator/plan.json docs/.adesso/skills/proposalgenerator/AGENT.md
git commit -m "feat(proposalgenerator): wire ProductDesign and ProposalOutline steps into chain"
```

---

## Manuelle Verifikation (nach allen Tasks)

Nicht automatisierbar in dieser Umgebung (Chain läuft im adessoGPT-Skill-Runtime, nicht lokal). Nach Deployment mit dem Infineon-Tender als Eval:

1. **Struktur-Eval:** erzeugte `ProposalOutlineResult.json` → Kapitelliste vs. Gewinner-Struktur (Exec Summary, Architektur, Produkt/UX, Business Logic, Import/Export, Non-functional, SCRUM, QM, App-Mgmt/SLA, Transition, Compliance, Price). Baseline-Dimensionen immer vorhanden; Migration/SLA/Risk/Compliance nur bei Evidenz.
2. **Produkt/UX-Eval:** `ProductDesignResult.json` — jede Interaktion hat nicht-leere `requirement_ids`.
3. **Solution-Eval:** tender-vorgegebene Tech (pdftron, SQL Server, DITA-XML) taucht konkret auf; Negativ-Test: offene Blöcke ohne Produktnamen.
4. **Preis-Eval:** kein `"XXX"` im `ProposalResult.md`, Zahlungsziel 60 Tage.
5. **Anonymisierungs-Regression:** weiterhin keine Personen-/Kundennamen im Output (Policy unverändert).

## Bekannte, bewusst offene Lücke

Klarnamen-Konflikt (Finding 4) bleibt ungelöst: X-FAB-Branchenreferenz, benannte Profile/CVs sind weiter nicht möglich. Dokumentiert im Design-Doc, Abschnitt "Bewusst NICHT im Scope".

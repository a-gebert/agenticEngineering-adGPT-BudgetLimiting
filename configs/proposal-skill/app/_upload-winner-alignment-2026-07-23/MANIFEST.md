# Deployment-Mappe: proposalgenerator Winner-Alignment (2026-07-23)

Zu aktualisierende / neu zu registrierende Dateien für den Agenten. Pfade relativ
zur Skill-Wurzel `docs/.adesso/skills/proposalgenerator/`.

Merge-Commit: `7d0aed1` (Branch `feat/proposal-winner-alignment`).

## 1. Neue Chain-Steps (Skill NEU registrieren)

| Step | Skill-Name | Prompt | Schema (output) | Artefakt |
|---|---|---|---|---|
| ProductDesign | `proposal-product-design` | `prompts/product_design.md` | `schema/product_design.json` | `ProductDesignResult.json` |
| ProposalOutline | `proposal-proposal-outline` | `prompts/proposal_outline.md` | `schema/proposal_outline.json` | `ProposalOutlineResult.json` |

- **ProductDesign** — Phase Solution, Position 7 (zwischen `SolutionProposal` und `StaffingCatalog`). Batch-Input: `Functional.json`, `SolutionProposal.md`.
- **ProposalOutline** — Phase Consolidation, Position 14 (zwischen `Report` und `Proposal`). Batch-Input: alle PreProcessing/Solution-Artefakte + `ExecutiveSummary.json`, `OpenPoints.json`.

## 2. Geänderte Step-Prompts (Skill-Prompt aktualisieren)

| Step | Skill-Name | Prompt (geändert) | Schema | Änderung |
|---|---|---|---|---|
| SolutionCatalog | `proposal-solution-catalog` | `prompts/solution_catalog.md` | `schema/solution_catalog.json` | Tender-Re-Read; `tender_mandated`-Flag; Produktnamen-Verbot gelockert |
| SolutionProposal | `proposal-solution-research` | `prompts/solution_proposal.md` | `schema/solution_proposal_output.md` | vorgeschriebene Tech entschieden übernehmen, kein Optionsvergleich/Zitat für `tender_mandated`-Blöcke |
| ExecutiveSummary | `proposal-executive-summary` | `prompts/executive_summary.md` | `schema/executive_summary.json` | adesso-Fakten-Zitat + Preis-Rationale |
| Proposal | `proposal-proposal` | `prompts/proposal.md` | `schema/proposal_output.md` (Output-Template) | Outline-gesteuertes Rendering, bedingte Kapitel, Fließtext-Narrativ, Ton, Preis-Cleanup |

## 3. Geänderte Schemas / Templates (mit-deployen)

| Datei | Typ | Änderung |
|---|---|---|
| `schema/solution_catalog.json` | JSON Schema | optionales Boolean `tender_mandated` auf `solution_blocks.items` (nicht `required`) |
| `schema/proposal_output.md` | Markdown-Output-Template (für `proposal-proposal`) | Beispiel-`XXX`-Tagessatzzellen geleert |

## 4. Neue Referenzdatei (mit-deployen, kein Skill)

| Datei | Konsumenten | Zweck |
|---|---|---|
| `references/adesso_facts.md` | `proposal-executive-summary`, `proposal-proposal` | Einzige erlaubte Quelle für adesso-Institutionsfakten. Anker: `## Company Profile`, `## Certifications`, `## Delivery Methodology`, `## Quality Management`, `## Application Management & SLA`, `## Locations & Organisation`. **Pflege:** `<!-- MAINTAIN -->`-Platzhalter mit echten Zahlen füllen (Umsatz/EBITDA, SLA-Zeiten, Standortzahl) — sonst leer lassen, nie erfinden. |

## 5. Orchestrierung (mit-deployen — kein Skill)

| Datei | Zweck | Änderung |
|---|---|---|
| `plan.json` | Chain-Definition | +2 Step-Einträge, next-Verkettung, Batch-Inputs; `Proposal`-Batch um `ProductDesign.json` + `ProposalOutline.json` erweitert |
| `AGENT.md` | Agent-Vertrag/Orchestrator | Workflow-Liste 1–17, Dependency-Rule, `adesso_facts.md` als erlaubte Wissensquelle |

## Deployment-Reihenfolge

1. Schemas + `references/adesso_facts.md` bereitstellen.
2. Zwei neue Skills registrieren (`proposal-product-design`, `proposal-proposal-outline`) mit Prompt + Schema.
3. Vier geänderte Step-Prompts aktualisieren.
4. `plan.json` + `AGENT.md` deployen (aktiviert die Chain-Verdrahtung).

## Deterministischer Join (kritisch)

Die 16 Rubrik-Dimensionsstrings müssen **zeichengenau identisch** sein über:
`prompts/proposal_outline.md` (Rubrik) = `schema/proposal_outline.json` (`dimension`-Enum, in `outline[]` und `dimensions[]`) = `prompts/proposal.md` (`— outline dimension: X`-Tags). `proposal.md` rendert Kapitel 2 per exaktem `dimension`-Key-Match, nicht per Heading-Text.

## Bewusst NICHT geändert

- Anonymisierung voll aktiv (Finding 4): keine Klarnamen/Personen/CVs. `proposal-profiler-match` unverändert.
- `estimator.md` **nicht** geändert — Preis-`XXX`-Cleanup lag real in `proposal.md` Kap 3, dort behoben.

## Nicht-deployrelevant (Repo-Doku)

`docs/superpowers/specs/2026-07-23-...-design.md`, `docs/superpowers/plans/2026-07-23-...md` — Design + Plan, nicht Teil des Skill-Bundles.

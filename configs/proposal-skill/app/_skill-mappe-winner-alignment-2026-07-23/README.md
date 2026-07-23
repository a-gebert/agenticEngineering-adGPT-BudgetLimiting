# Skill-Mappe: Winner-Alignment (2026-07-23)

Zu aktualisierende Dateien, **pro Skill gruppiert** (Basis: `git diff 2de739a..7d0aed1`).
Jeder Ordner = ein Skill; enthält nur dessen geänderte Dateien.

| Ordner | Skill / Rolle | Aktion | Enthaltene Dateien |
|---|---|---|---|
| `proposal-product-design [NEU]` | neuer Step | **Skill anlegen** | `product_design.md` (Prompt), `product_design.json` (Schema) |
| `proposal-proposal-outline [NEU]` | neuer Step | **Skill anlegen** | `proposal_outline.md` (Prompt), `proposal_outline.json` (Schema) |
| `proposal-solution-catalog` | Step | Prompt + Schema updaten | `solution_catalog.md`, `solution_catalog.json` (+`tender_mandated`) |
| `proposal-solution-research` | Step | nur Prompt updaten | `solution_proposal.md` |
| `proposal-executive-summary` | Step | nur Prompt updaten | `executive_summary.md` |
| `proposal-proposal` | Step | Prompt + Output-Template updaten | `proposal.md`, `proposal_output.md` |
| `_shared-reference` | kein Skill | Referenzdatei bereitstellen | `adesso_facts.md` |
| `_orchestration` | kein Skill | zuletzt deployen | `AGENT.md`, `plan.json`, `changes-full.diff` |

## Reihenfolge

1. `_shared-reference/adesso_facts.md` bereitstellen.
2. Beide `[NEU]`-Skills anlegen (Prompt + Schema).
3. Vier bestehende Step-Skills aktualisieren (Ordner ohne `[NEU]`).
4. `_orchestration/` (`AGENT.md` + `plan.json`) deployen — aktiviert die Chain.

## Hinweise

- Skills mit nur einer Datei (`proposal-solution-research`, `proposal-executive-summary`): Schema **unverändert**, nicht neu hochladen.
- `changes-full.diff` = voller Diff aller M-Dateien für gezieltes Patchen statt Voll-Ersatz.
- Zielpfade im Skill-Bundle: `prompts/*.md`, `schema/*.json|*.md`, `references/*.md`, sowie `AGENT.md` + `plan.json` in der Skill-Wurzel.
- Deterministischer Join: die 16 Dimensionsstrings müssen zeichengenau identisch bleiben über `proposal_outline.md`, `proposal_outline.json`, `proposal.md` — beim Upload keine Umformulierung.

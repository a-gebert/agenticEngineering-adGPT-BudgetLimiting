# Design: neuer `Estimator`-Schritt (proposalgenerator)

**Datum:** 2026-07-21
**Status:** Freigegeben (User-Approval liegt vor)
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator/`)
**Auslöser:** Es gibt aktuell keinen deterministischen Schätz-Schritt vor der Preistabelle in
`proposal.md` Kapitel 3 ("Prices") — die Personentage-Spannen werden dort ad-hoc vom
Proposal-Schritt selbst geraten, ohne nachvollziehbare Grundlage.

## Ziel

Ein neuer Kettenschritt `Estimator` leitet aus `SolutionProposalResult.md` Arbeitspakete ab und
schätzt pro Arbeitspaket und Rolle (aus `StaffingCatalogResult.json`) den Aufwand in Personentagen
(als Spanne). Das Ergebnis wird als schema-validiertes JSON (`EstimationResult.json`) abgesichert
und liefert die deterministische Grundlage für die Preistabelle in `proposal.md`.

## Inputs

- `SolutionProposalResult.md` — die konsolidierte Lösungsvorschau mit Solution-Blöcken (`SB-01`,
  `SB-02`, ...), je mit adressierten Requirements, empfohlener Technologie und Kapitel 6
  ("Assumptions, Risks and Open Research Questions").
- `StaffingCatalogResult.json` — `roles[]` (`role_id`, `title`, `seniority`, `required_skills`).
  **Nur diese Felder verwenden** — `profiler_query` (inkl. `location`/`availability`) ist laut
  bestehender Design-Entscheidung (`2026-07-15-profiler-staffing-referenzen-design.md`) reiner
  Matching-Kontext und darf im Estimator nicht verwendet werden. Der Estimator erfindet keine
  neuen Rollen — er verwendet ausschließlich `role_id`s, die bereits in `StaffingCatalogResult.json`
  existieren.

## Arbeitspaket-Modell

- **Granularität:** mehrere Arbeitspakete pro Solution-Block (typischerweise 2–4), vom Modell
  sinnvoll benannt je nach Art des Blocks (z.B. andere Aufteilung bei einer Migration als bei
  einem neuen Feature) — kein festes Phasen-Enum.
- **Block-übergreifende Arbeitspakete:** zusätzlich zu den block-gebundenen WPs kann es WPs ohne
  `solution_block_id` geben, für Rollen/Tätigkeiten, die über das ganze Projekt laufen
  (Projektsteuerung, Qualitätssicherung/Testmanagement, Deployment & Hypercare). Das verhindert,
  dass z.B. die Rolle "Projektleiter" künstlich einem einzelnen Block zugeschlagen werden muss.
- Jedes Arbeitspaket hat `effort_by_role[]`: pro benötigter Rolle (Referenz `role_id` auf
  `StaffingCatalogResult.json`) eine Personentage-**Spanne** (`person_days_min`/`max`) plus
  `rationale`. Spannen statt Einzelwerte, weil `proposal.md` Kapitel 3 bereits "realistic effort
  ranges (e.g. '80–120') rather than exact numbers" verlangt.

## Schema-Kern (`schema/estimator.json`)

```jsonc
{
  "document_id": "...",                          // optional
  "work_packages": [{
    "wp_id": "WP-01",
    "title": "z.B. Konzeption Integrationsschicht",
    "solution_block_id": "SB-01",                 // optional — fehlt bei block-übergreifenden WPs
    "description": "kurze Beschreibung des Arbeitspakets",
    "addressed_requirements": ["FR-001", "NFR-002"], // optional, aus dem Block übernommen
    "effort_by_role": [{
      "role_id": "R-01",                          // Referenz auf StaffingCatalogResult.roles[]
      "role_title": "Integration Architect",       // denormalisiert für Lesbarkeit
      "person_days_min": 10,
      "person_days_max": 15,
      "rationale": "warum dieser Aufwand für diese Rolle in diesem WP"
    }],
    "assumptions": ["..."]                        // optional, WP-spezifische Annahmen
  }],
  "role_summary": [{                              // aggregiert über alle work_packages
    "role_id": "R-01",
    "role_title": "Integration Architect",
    "seniority": "senior",
    "person_days_min": 25,
    "person_days_max": 35
  }],
  "total_effort": { "person_days_min": 0, "person_days_max": 0 },
  "assumptions": ["..."],                         // globale Annahmen (z.B. Reisekosten, Testdaten)
  "confidence": "medium",                          // low | medium | high
  "errors": []                                     // gleiches Fehler-Muster wie übrige Schemata
}
```

`confidence` wird aus Kapitel 6 der `SolutionProposalResult.md` (offene Forschungsfragen, Risiken)
abgeleitet — viele/gravierende offene Punkte → niedrigere Confidence.

## Chain-Einordnung

Solution-Phase, letzter Schritt (nach `ProfilerMatch` — funktional unabhängig davon, aber
thematisch schließt er die Solution-Phase ab):

```
SolutionCatalog → SolutionProposal → StaffingCatalog → ProfilerMatch → Estimator
```

- Skill: `proposal-estimator`
- Prompt: `prompts/estimator.md` (NEU)
- Schema: `schema/estimator.json` (NEU)
- Artefakt: `EstimationResult.json`

### AGENT.md-Änderungen

1. Workflow/Chain: neuer Schritt in Phase 2 Solution nach `ProfilerMatch`; nachfolgende
   Consolidation-Schritte (`OpenPoints`, `Report`, `ExecutiveSummary`, `Proposal`) und Export
   rücken in der Nummerierung um eins weiter.
2. Dependency Rule: `proposal-estimator` darf erst laufen, nachdem `SolutionProposalResult.md`
   und `StaffingCatalogResult.json` existieren. `proposal-proposal` bekommt `EstimationResult.json`
   als zusätzliche Pflicht-Abhängigkeit.

### Scope-Abgrenzung

`plan.json`/`minimal_plan.json` werden **bewusst nicht** angepasst (User-Entscheidung, analog zu
den vorherigen Chain-Änderungen in dieser Session).

## Anbindung an `proposal.md` (Kapitel 3 "Prices")

- Neuer Input in der Context-Liste: `EstimationResult.json`.
- Die Preistabelle (`| Qualification/Role | Person-Days | Day Rate | Price |`) wird direkt aus
  `EstimationResult.json` → `role_summary[]` befüllt: eine Zeile pro Eintrag, `Person-Days` als
  `person_days_min–person_days_max`. Die Total-Zeile kommt aus `total_effort`.
- Die bisherige Anweisung "Base estimates on the complexity indicated by the requirements" (Kap. 3)
  entfällt — die Schätzung kommt jetzt ausschließlich aus `EstimationResult.json`, nicht mehr aus
  eigener Einschätzung des Proposal-Schritts.
- `Day Rate` bleibt weiterhin "XXX" (vertraulich, manuell befüllt) — daran ändert sich nichts.
- Kapitel 2.4 ("Project Approach and Methodology") wird **nicht** angetastet — das ist bewusste
  Scope-Begrenzung; die dortigen Projektphasen bleiben unabhängig von den Arbeitspaketen des
  Estimators.

## Annahmen / offen

- Der Estimator verwendet ausschließlich die zwei genannten Input-Dateien — kein Zugriff auf
  `ConstraintsResult.json` (Budget/Timeline) für einen Plausibilitäts-Check gegen ein
  Budget-Ceiling. Das ist eine bewusste Scope-Begrenzung (YAGNI) und kann bei Bedarf später
  ergänzt werden.
- Kein Schema-Constraint erzwingt `person_days_min <= person_days_max` — das wird als
  Prompt-Anweisung (Tweak) vorgegeben, nicht als JSON-Schema-Validierung (analog zum bestehenden
  Muster, dass Geschäftsregeln primär im Prompt-Text stehen, nicht im Schema).

## Nächster Schritt

Direkte Umsetzung: neues Schema, neuer Prompt, `AGENT.md`-Verdrahtung, `proposal.md`
Kapitel-3-Anbindung — kein separater Implementierungsplan nötig.

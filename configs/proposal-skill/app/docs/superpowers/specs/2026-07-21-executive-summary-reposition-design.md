# Design: ExecutiveSummary ans Kettenende verschieben (proposalgenerator)

**Datum:** 2026-07-21
**Status:** Freigegeben (User-Approval liegt vor)
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator/`)
**Auslöser:** Hinweis des Chefs des Users — die Executive Summary soll logischerweise die Solution
mit einbeziehen, kann also nicht als allererster Schritt (vor jeder Lösungsfindung) entstehen.

## Ziel

`ExecutiveSummary` wird von Phase-1-Schritt 1 (PreProcessing, ganz am Anfang) an das Ende der
Phase 3 (Consolidation) verschoben — als letzter Schritt vor `Proposal`. Dadurch kann die
Zusammenfassung neben dem Tender-Inhalt auch adessos vorgeschlagene Lösung einbeziehen.

## Bestandsaufnahme (Abhängigkeitsanalyse)

`ExecutiveSummaryResult.json` liefert zwei unabhängige Dinge:
1. Den eigentlichen Management-Summary-Text (`executive_summary`, `key_topics`).
2. Eine vollständige Dokumentstruktur-Ableitung (`chapters`/`sections`/`aspects`) aus dem
   Tender-PDF — **redundant** zu den chapters/sections/aspects, die `ClientContextResult.json`,
   `FunctionalResult.json`, `FormalResult.json` und `ConstraintsResult.json` jeweils **selbst und
   unabhängig** aus derselben RAG-Retrieval ableiten (jeder PreProcessing-Schritt macht seine
   eigene komplette Struktur-Rekonstruktion).

Konsumenten von `ExecutiveSummaryResult.json`:
- `open_points.md` (OpenPoints) — aggregiert die Struktur aus allen PreProcessing-Result-Dateien,
  toleriert aber explizit fehlende Dateien ("Any …Result.json file that is absent … is simply
  skipped").
- `functional_consolidation.md` (Report) — dieselbe Toleranz, wortgleich dokumentiert.
- `proposal.md` (Proposal) — nutzt `key_topics`/`executive_summary` für Kapitel 1 ("Initial
  Situation") und referenziert die Struktur **wahlweise** aus `ExecutiveSummaryResult.json`
  **oder** `ClientContextResult.json` ("using the structure carried in
  `ExecutiveSummaryResult.json` / `ClientContextResult.json`").

**Schlussfolgerung:** Da `OpenPoints` und `Report` ein fehlendes `ExecutiveSummaryResult.json`
bereits vertragen (ihre Struktur-Aggregation fällt automatisch auf `ClientContextResult.json` &
Co. zurück) und `proposal.md` die Struktur ohnehin alternativ aus `ClientContextResult.json`
beziehen kann, ist eine Verschiebung ans Kettenende **ohne Bruch der Aspect-Chain-Auflösung**
möglich. Der einzige echte Bruch wäre, wenn `Proposal` weiterhin `key_topics`/`executive_summary`
braucht, aber `ExecutiveSummary` erst NACH `Proposal` liefe — deshalb läuft `ExecutiveSummary`
unmittelbar **vor** `Proposal`, nicht danach.

## Entscheidung (User-Approval)

`ExecutiveSummary` läuft als letzter Schritt der Consolidation-Phase, nach `Report` und vor
`Proposal` — nicht ganz am physischen Ende der Kette (das wäre nach `Proposal`), aber am Ende der
inhaltlichen Vorbereitung, sodass `Proposal` weiterhin unverändert auf
`ExecutiveSummaryResult.json` zugreifen kann.

## Neue Chain-Reihenfolge

```
Phase 1 — PreProcessing:  ClientContext → Functional → Formal → Constraints
Phase 2 — Solution:       SolutionCatalog → SolutionProposal → StaffingCatalog → ProfilerMatch
Phase 3 — Consolidation:  OpenPoints → Report → ExecutiveSummary (NEU HIER) → Proposal
```

## Änderungen an `AGENT.md`

1. **Workflow/Chain:** `ExecutiveSummary` aus Phase 1 (Schritt 1) entfernen; Phase-1-Schritte neu
   durchnummerieren (`ClientContext` wird Schritt 1, `Functional` Schritt 2, `Formal` Schritt 3,
   `Constraints` Schritt 4). `ExecutiveSummary` wird neuer Schritt in Phase 3, zwischen `Report`
   und `Proposal` eingefügt. Gesamte Schrittnummerierung 1–14 entsprechend verschieben.
2. **Dependency Rule:**
   - `ExecutiveSummaryResult.json` aus den Prerequisite-Listen von `proposal-open-points` und
     `proposal-report` entfernen (existiert an dieser Stelle der Kette noch nicht).
   - Neue Regel: `proposal-executive-summary` darf erst laufen, nachdem `SolutionProposalResult.md`
     existiert.
   - `proposal-proposal`s Prerequisite-Liste bekommt `ExecutiveSummaryResult.json` explizit
     ergänzt (bisher implizit über die PreProcessing-Zugehörigkeit abgedeckt).
3. Keine Änderung an anderen Sektionen (Output Language, Tender Document Access, Code Interpreter
   Restriction, Forbidden Behaviors etc.) — diese sind chain-positionsunabhängig formuliert.

## Änderungen an `prompts/executive_summary.md`

1. **Neuer Input:** `SolutionProposalResult.md` (die konsolidierte Zielarchitektur / je eine
   empfohlene Technologie pro Lösungsblock) wird als zusätzliche Kontext-Datei eingeführt, analog
   zur Einleitung anderer später laufender Schritte (Muster: `open_points.md`,
   `functional_consolidation.md`).
2. **`executive_summary`-Textvorgabe erweitert:** von "maximal 10 Zeilen, reiner Tender-Inhalt" auf
   **maximal 12 Zeilen** — die 2 zusätzlichen Zeilen fassen zusammen:
   - adessos vorgeschlagene Lösungsrichtung / Zielarchitektur (aus
     `SolutionProposalResult.md`), auf hoher Flughöhe, ohne Wiederholung der technischen Details.
   - eine abschließende Positionierungs-/Confidence-Aussage (adesso als idealer Partner) — analog
     zum dritten Absatz der Management Summary in `proposal.md`, aber als eigenständiges, kürzeres
     Artefakt.
3. **`key_topics` bleibt unverändert** — weiterhin ausschließlich aus dem Tender abgeleitet, keine
   Vermischung mit Lösungsthemen (bewusste Scope-Begrenzung, um Redundanz mit `SolutionCatalog`
   klein zu halten).
4. Die RAG-basierte Dokumentstruktur-Ableitung (`chapters`/`sections`/`aspects`) bleibt inhaltlich
   unverändert — sie bedient weiterhin `proposal.md`s alternative Strukturquelle.
5. Kein Schema-Change nötig: `executive_summary.json` erzwingt keine Zeilenanzahl (reiner
   `string`-Typ), die 12-Zeilen-Vorgabe ist ausschließlich Prompt-Text.

## Scope-Abgrenzung

- `plan.json` / `minimal_plan.json` (maschinenlesbarer Chain-Graph) werden **bewusst nicht**
  angepasst — User-Entscheidung. Das erzeugt eine bekannte Inkonsistenz zwischen `AGENT.md`
  (Doku/Orchestrierungs-Prompt) und `plan.json` (falls dieses tatsächlich zur Laufzeit
  ausgewertet wird) — analog zum bereits aufgetretenen `proposal-solution-research`-Bug. Diese
  Inkonsistenz ist der Nutzerin/dem Nutzer bekannt und bewusst in Kauf genommen; nicht Teil dieser
  Umsetzung.
- `proposal.md` wird **nicht** verändert — es referenziert `ExecutiveSummaryResult.json` bereits
  heute exakt so, wie es nach der Verschiebung weiterhin funktioniert (Datei existiert zum
  Zeitpunkt, an dem `Proposal` läuft).
- `schema/executive_summary.json` wird **nicht** verändert (kein struktureller Feld-Unterschied).

## Nächster Schritt

Direkte Umsetzung in `AGENT.md` und `prompts/executive_summary.md` — kleine, lokal begrenzte
Textänderungen an zwei bestehenden Dateien, kein separater Implementierungsplan nötig.

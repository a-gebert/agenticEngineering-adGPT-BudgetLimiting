# Design: adesso-Vorlagen-Mapping für den Proposal.docx-Export (proposalgenerator)

**Datum:** 2026-07-21
**Status:** Freigegeben (User-Approval liegt vor)
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator/`)

## Ziel

Der Export-Schritt „`ProposalResult.md` → `Proposal.docx`" (Schritt 13 der Chain) erzeugt
aktuell ein unstyled Word-Dokument. Auf dem Code-Interpreter-Image liegen unter
`/customer/adesso/assets/docs/` echte adesso-Angebotsvorlagen im Corporate Design (`.dotx`).
Der Export soll die inhaltlich passende Vorlage laden und das Corporate Design (Layout,
Deckblatt, Kopf-/Fußzeilen, Formatvorlagen) auf den Inhalt von `ProposalResult.md` anwenden,
statt ein generisches Dokument zu erzeugen.

## Verfügbare Vorlagen

Auf dem Code-Interpreter-Image unter `/customer/adesso/assets/docs/`:

- `Angebotsvorlage_Dienstleistung.dotx`
- `Angebotsvorlage_Dienstleistung zum Festpreis.dotx`
- `Angebotsvorlage_Schulungen und Workshops.dotx`

## Mapping-Tabelle

| Template-Datei | Angebotstyp / Szenario | Auswahlkriterium |
|---|---|---|
| `Angebotsvorlage_Dienstleistung.dotx` | Standard-Dienstleistung (Time & Material) | **Default.** Wird verwendet, wenn keines der anderen Kriterien eindeutig zutrifft, oder wenn `ConstraintsResult.json` → `budget.type` ungleich `"fixed"` ist. |
| `Angebotsvorlage_Dienstleistung zum Festpreis.dotx` | Festpreis-Angebot | `ConstraintsResult.json` → `budget.type == "fixed"` **und** das Vorhaben ist kein reines Trainings-/Workshop-Projekt. |
| `Angebotsvorlage_Schulungen und Workshops.dotx` | Trainings- und Workshop-Angebot | Der Auftragsgegenstand ist primär Training/Enablement/Workshops — ableitbar aus `key_topics` (`ExecutiveSummaryResult.json`) und den Lösungsbausteinen in `SolutionCatalogResult.json` (keine Software-Implementierung, sondern Wissenstransfer). |

### Entscheidungsreihenfolge

1. Ist das Vorhaben primär Training/Workshop → `Angebotsvorlage_Schulungen und Workshops.dotx`.
2. Sonst: ist `budget.type == "fixed"` → `Angebotsvorlage_Dienstleistung zum Festpreis.dotx`.
3. Sonst → `Angebotsvorlage_Dienstleistung.dotx` (Default).

### Umgang mit Mehrdeutigkeit

Bei nicht eindeutiger Klassifikation wird **nicht** nachgefragt — es gilt automatisch der
Default (`Angebotsvorlage_Dienstleistung.dotx`). Das unterscheidet sich bewusst von der
„mandatory clarification gate"-Regel bei DeepResearch/Profiler-Matching in `AGENT.md`: die
Vorlagenwahl ist ein reines Formatierungs-/Layout-Detail ohne inhaltliche Tragweite und
rechtfertigt keine zusätzliche Rückfrage im Workflow.

### Scope-Abgrenzung

Die Mapping-Logik gilt **ausschließlich** für den `Proposal.docx`-Export. `Report.pdf`
(`ReportResult.md`) ist ein interner Analyse-Report ohne Kunden-Layout und wird weiterhin ohne
adesso-Angebotsvorlage exportiert.

## Änderungen an `AGENT.md`

1. **Neue Sektion „Proposal Template Selection"**, platziert vor der bestehenden Sektion
   `# Code Interpreter Restriction`. Enthält den Vorlagenpfad, die Mapping-Tabelle, die
   Entscheidungsreihenfolge, die Default-Regel bei Mehrdeutigkeit und die Scope-Abgrenzung
   zu `Report.pdf`.
2. **Workflow/Chain, Schritt 13** wird präzisiert von
   „Convert `ProposalResult.md` to `Proposal.docx`" zu
   „Convert `ProposalResult.md` to `Proposal.docx` using the adesso template selected per the
   **Proposal Template Selection** mapping".
3. **`# Code Interpreter Restriction`**: die Liste erlaubter Nutzungen wird um „loading the
   adesso template file selected via the Proposal Template Selection mapping to apply
   corporate design to `Proposal.docx`" ergänzt.

Alle übrigen Sektionen (Dependency Rule, Artifact Integrity Rule, Forbidden Behaviors, Final
Compliance Check) bleiben unverändert — die Änderung betrifft ausschließlich den bereits
bestehenden Export-Schritt, keine neuen Chain-Schritte oder Artefakte.

## Annahmen / offen

- Die drei genannten Dateinamen (inkl. exaktes Leerzeichen/Schreibweise) sind vom User als
  vollständige, aktuelle Liste bestätigt. Sollten künftig weitere Vorlagen ergänzt werden,
  muss die Mapping-Tabelle entsprechend erweitert werden.
- Wie der Code Interpreter das `.dotx`-Template technisch auf den Markdown-Inhalt anwendet
  (z. B. python-docx mit Formatvorlagen aus der Vorlage), ist Implementierungsdetail des
  Code-Interpreter-Aufrufs und nicht Teil dieser AGENT.md-Änderung — `AGENT.md` regelt nur die
  Orchestrierung (welche Vorlage wird gewählt), nicht die technische Umsetzung des Exports.

## Nächster Schritt

Direkte Umsetzung in `AGENT.md` (kleine, lokal begrenzte Textänderung an drei Stellen einer
bestehenden Markdown-Datei — kein separater Implementierungsplan nötig).

# Proposalgenerator: RAG-Retrieval statt Sandbox-PDF-Konvertierung

**Datum:** 2026-07-10
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator`)
**Status:** Design freigegeben — bereit für Implementierungsplan

## Problem

Die dokument-lesenden Prompts der Chain beginnen alle mit derselben Annahme:

> *You receive the extracted content of a document (originally PDF or Word) as **Markdown text**. The Markdown was produced by Azure Document Intelligence … `<!-- PageNumber="Page X of Y" -->` markers …*

`AGENT.md` weist als Fallback an, ein nicht-Markdown-Dokument **im Code-Interpreter-Sandbox aus dem PDF nach Markdown zu konvertieren** (Abschnitt „Document Retrieval & Analysis", Punkt 3). Genau dieser Schritt scheitert: Der Sandbox-Konverter kann die PDFs nicht einlesen. Fehlerbild des Agenten:

> *„Aktuell kann der Sandbox-Konverter die PDFs nicht einlesen …"*

Tatsächlich liegt das Tender-Dokument **ausschließlich im RAG** vor und wird über **Document-Search** durchsucht. Document-Search liefert **relevante Passagen/Chunks** (mit Zitat/Seitenbezug) zurück — **nicht** das vollständige Dokument als sauberes Markdown mit Heading-Hierarchie.

## Ziel

Alle dokument-lesenden Prompts greifen **immer** über Document-Search (RAG) auf den Tender zu. Keine Annahme mehr über vor-konvertiertes Markdown, keine PDF-Konvertierung im Sandbox. Retrieval wird **explizit als gezielte RAG-Query** angeleitet.

## Scope

| Prompt | Liest Tender? | Änderung |
|---|---|---|
| `prompts/executive_summary.md` | Ja | **RAG-Rewrite** |
| `prompts/client_context.md` | Ja | **RAG-Rewrite** |
| `prompts/functional.md` | Ja | **RAG-Rewrite** |
| `prompts/formal.md` | Ja | **RAG-Rewrite** |
| `prompts/constraints.md` | Ja | **RAG-Rewrite** |
| `AGENT.md` | Orchestrierung | Sandbox-PDF-Konvertierung entfernen; Document-Search-Retrieval verpflichtend; Code-Interpreter nur noch für JSON-Schema-Validierung + DOCX/PDF-**Export** |
| `prompts/open_points.md` | Nein | **unverändert** (RAG-frei, konsumiert `…Result.json`) |
| `prompts/functional_consolidation.md` (Report) | Nein | **unverändert** (RAG-frei) |
| `prompts/proposal.md` | Nein | **unverändert** (RAG-frei) |
| `prompts/reference.md` | Ja, aber nicht im Chain verdrahtet | **unverändert** (bewusst ausgeklammert) |

**Bestätigte Entscheidungen:**
- Consolidation-Prompts bleiben deterministisch und RAG-frei — „immer RAG" gilt für die dokument-lesenden PreProcessing-Schritte, nicht für die Aggregation.
- `reference.md` bleibt unberührt (aktuell nicht als Chain-Schritt verdrahtet).

## Wichtige Randbedingung: Schema-Pflichtfelder bleiben bestehen

`chapters`, `sections`, `aspects` sind in **jedem** PreProcessing-Schema Pflichtfelder auf Root-Ebene; `aspects` sind die semantische Brücke zwischen den Chain-Schritten. `functional`/`formal` verlangen zusätzlich `source_page` pro Requirement. Diese Struktur-Logik **bleibt erhalten** — nur die Quelle wechselt von „vollständiges Markdown" zu „Document-Search-Treffern". Struktur wird best-effort aus den Treffern abgeleitet; Lücken werden in `errors` gemeldet, nicht erfunden.

## Gewählter Ansatz (A): Explizite, gezielte RAG-Queries in zwei Wellen

Jeder dokument-lesende Prompt bekommt einen expliziten Retrieval-Block:

1. **Welle 1 — Struktur/Outline:** breite Document-Search-Queries (z. B. Inhaltsverzeichnis, Kapitelüberschriften, Abschnittstitel), um `chapters`/`sections`/`aspects` best-effort zu rekonstruieren.
2. **Welle 2 — themenspezifisch:** Queries passend zum Schritt-Zweck:
   - **ExecutiveSummary:** ausschreibende Organisation, Zweck, Leistungsumfang, Fristen, Ergebnisse
   - **ClientContext:** Branche, Bestandssysteme, Herausforderungen/Pain-Points, strategische Ziele
   - **Functional:** Anforderungen, „muss/soll/kann", „shall/should/could", Funktionen, Qualitätsmerkmale (nicht-funktional)
   - **Formal:** Frist, Einreichung, Format, Seitenlimit, Sprache, Eignung/Zertifikate, Preisformat, Lose
   - **Constraints:** Budget/Obergrenze, Zeitplan, Meilensteine, Go-Live, Pflichttechnologien, organisatorische Auflagen

**Regeln für jeden umgebauten Prompt:**
- Inhalt liegt **nur** via RAG vor; Document-Search ist **Pflicht** vor jeder Analyse; **nichts erfinden**, nicht aus generischem Wissen antworten.
- `source_page` aus dem Zitat/Seitenbezug des jeweiligen Treffers; Fallback `"n/a"` (Requirements) bzw. Feld weglassen (Aspekte), wenn kein Seitenbezug vorliegt.
- Struktur-Felder best-effort aus den Treffern; konsistente IDs (`ch-N`, `sec-N-M`, `asp-N`) beibehalten.
- Alte Regel „keine Markdown-Headings → `NO_STRUCTURE`" ersetzen durch: „Document-Search liefert nichts Relevantes → `errors`-Eintrag `code: "NO_SOURCE_CONTENT"`, `severity: "error"`, leere Arrays für chapters/sections/aspects".
- Tabellen-/Listenextraktion weiterhin aus den Treffer-Passagen (Chunks können Tabellenzeilen enthalten).
- Code-Interpreter-Validierung gegen das JSON-Schema und das `…Result.json`-Deliverable bleiben **unverändert**.

**Verworfene Alternativen:**
- **B — generisch „durchsuche zuerst die Dokumente":** einfacher, aber weniger reproduzierbar/deterministisch.
- **C — volles Markdown per erschöpfender Suche zusammenbauen:** fragil, widerspricht dem Chunk-Modell.

## AGENT.md — konkrete Änderungen

**Leitprinzip: Delegation statt Eigen-Analyse.** Der Orchestrator führt **selbst keine** Document-Search durch und analysiert den Tender **nicht** selbst — jede Chain-Skill holt sich ihren Inhalt via Document-Search und analysiert eigenständig. Der Agent übergibt einer Skill maximal `output_language` und den **Datei-Namen/-Referenz** des Tenders; keinen Dokumentinhalt und keine eigene Zusammenfassung. Die frühere „Document Retrieval & Analysis"-Sektion (die den Agenten selbst suchen/lesen/Struktur-rekonstruieren ließ) wird durch eine „Document Access (delegated to the skills)"-Sektion ersetzt.

- **„The tender document is provided through RAG …"**-Absatz: schärfen auf „Zugriff **ausschließlich** über Document-Search; niemals annehmen, der Dokumenttext sei bereits im Kontext".
- **„Document Retrieval & Analysis", Punkt 3** (PDF→Markdown-Konvertierung im Sandbox): **entfernen** und ersetzen durch „gezielte Document-Search-Queries; strukturierte Auswertung der Treffer; keine Sandbox-Konvertierung von Eingabe-PDFs".
- Klarstellen, dass der **Code-Interpreter** nur für (a) JSON-Schema-Validierung der Artefakte und (b) den **Export** der erzeugten Markdown-Deliverables nach `Proposal.docx` / `Report.pdf` genutzt wird — **nicht** für das Einlesen der Eingabe-Dokumente.
- „document search across all uploaded files"-Formulierungen konsistent auf **Document-Search / RAG** vereinheitlichen.

## Verifikation

- Alle 5 umgebauten Prompts enthalten keinen Verweis mehr auf „Azure Document Intelligence", „PageNumber"-Markdown-Marker als *Eingabequelle* oder PDF→Markdown-Konvertierung als Eingabeschritt.
- Jeder umgebaute Prompt enthält einen expliziten Retrieval-(RAG-)Block mit Document-Search-Queries.
- `AGENT.md` enthält keine Anweisung mehr, Eingabe-PDFs im Sandbox zu konvertieren.
- Consolidation-Prompts (`open_points`, `functional_consolidation`, `proposal`) und `reference.md` sind unverändert.
- Schema-Pflichtfelder (`chapters`/`sections`/`aspects`, `source_page`) bleiben in den Prompt-Anweisungen erhalten.

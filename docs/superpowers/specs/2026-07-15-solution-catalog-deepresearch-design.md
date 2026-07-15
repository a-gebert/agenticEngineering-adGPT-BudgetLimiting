# Design: Lösungskatalog + DeepResearch-Lösungsvorschlag (proposalgenerator)

**Datum:** 2026-07-15
**Status:** Freigegeben (User-Approval liegt vor)
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator/`)

## Ziel

Zwei neue Kettenschritte, die aus den extrahierten funktionalen und nicht-funktionalen
Anforderungen (1) einen **Lösungskatalog** ableiten und (2) über ein **DeepResearch-Agent-Tool**
Technologien und Best Practices recherchieren und zu **einem eindeutigen, ausgearbeiteten
Lösungsvorschlag** verdichten, der zum Katalog passt.

Leitprinzip: Das Angebot präsentiert am Ende **genau eine** klare Lösung. Der Lösungsvorschlag
konvergiert je Baustein zu genau einer Empfehlung; Optionen dienen ausschließlich der Begründung,
nie als offene Wahl für den Kunden.

## Chain-Einordnung

Neue Phase **`Solution`** zwischen `PreProcessing` und dem `Proposal`-Schritt der `Consolidation`,
damit der Lösungsvorschlag in die Angebotserstellung (Kap. 2.3) einfließen kann.

```
PreProcessing (ExecutiveSummary, ClientContext, Functional, Formal, Constraints)
   → Solution (SolutionCatalog, SolutionProposal)          [NEU]
   → Consolidation (OpenPoints, Report, Proposal)
```

Datenfluss:

```
FunctionalResult.json + ConstraintsResult.json + ClientContextResult.json
   → [SolutionCatalog]  → SolutionCatalogResult.json
   → [SolutionProposal] (+ DeepResearch-Tool, + HITL-Rückfrage)  → SolutionProposalResult.md
   → [Proposal] Kap. 2.3 nutzt SolutionProposalResult.md
```

## Schritt A — SolutionCatalog

- **Skill:** `proposal-solution-catalog`
- **Prompt:** `prompts/solution_catalog.md` (NEU)
- **Schema:** `schema/solution_catalog.json` (NEU)
- **Artefakt:** `SolutionCatalogResult.json` (schema-validiert via Code Interpreter)
- **Inputs:** `FunctionalResult.json`, `ConstraintsResult.json`, `ClientContextResult.json`

Deterministische Ableitung — **kein externes Wissen, keine konkreten Produkte/Technologien**.
Der Katalog clustert FR/NFR zu thematischen Lösungsbausteinen und formuliert je Baustein einen
konkreten Rechercheauftrag. Er ist die Brücke zwischen Anforderungen und Recherche und markiert
zugleich Unsicherheit für das spätere Rückfrage-Gate.

### Schema-Kern (`solution_catalog.json`)

```jsonc
{
  "document_id": "...",                       // optional
  "solution_blocks": [{
    "block_id": "SB-01",
    "title": "z.B. Offline-Transaktionsfähigkeit",
    "description": "Welche Fähigkeit/Bedarf der Baustein abdeckt (aus den Anforderungen)",
    "addressed_requirements": ["FR-001", "FR-004", "NFR-002"],
    "aspect_ids": ["asp-3"],                   // optional, Cross-Ref
    "solution_type": "z.B. Integration | Datenplattform | Frontend | Security | Cloud-Infra",
    "priority": "must | should | nice-to-have", // höchste Prio der adressierten Reqs
    "constraints": ["relevante technische/Budget-/Org-Restriktionen aus ConstraintsResult"],
    "evaluation_criteria": ["Bewertungskriterien für Kandidaten-Technologien"],
    "candidate_directions": [                  // plausible Technologie-RICHTUNGEN (Familien, keine Produkte)
      { "label": "z.B. Azure-native Sync", "rationale": "..." }
    ],
    "research_questions": ["konkrete Fragen als Auftrag an DeepResearch"],
    "needs_clarification": true,               // Unsicherheits-Flag fürs HITL-Gate
    "clarification_reason": "multiple_directions | low_confidence | insufficient_constraints",
    "clarification_question": "Frage an den User (in output_language), nur wenn needs_clarification",
    "confidence": 0.0                          // 0..1
  }],
  "coverage": {
    "total_requirements": 0,
    "covered_requirements": 0,
    "uncovered_requirement_ids": []
  },
  "errors": []                                 // gleiches Fehler-Muster wie functional_requirements.json
}
```

### Regel zur Unsicherheitserkennung

`needs_clarification = true`, sobald mindestens eine Bedingung zutrifft:
- **(a) `multiple_directions`:** zwei oder mehr ernsthaft konkurrierende `candidate_directions`.
- **(b) `low_confidence`:** `confidence` unterhalb der Schwelle (Richtwert < 0.5).
- **(c) `insufficient_constraints`:** Anforderungen/Restriktionen reichen nicht aus, um die
  Recherche einzugrenzen.

`clarification_reason` hält fest, welcher Fall vorliegt; `clarification_question` formuliert die
konkrete Rückfrage. Bei `needs_clarification = false` entfallen `clarification_reason` und
`clarification_question`.

## Schritt B — SolutionProposal

- **Skill:** `proposal-solution-proposal`
- **Prompt:** `prompts/solution_proposal.md` (NEU)
- **Layout-Beispiel:** `schema/solution_proposal_output.md` (NEU, fiktives Beispiel als Layout-Template)
- **Artefakt:** `SolutionProposalResult.md` (Markdown, kein Schema — wie `proposal.md`)
- **Inputs:** `SolutionCatalogResult.json` (+ referenziert FunctionalResult/ConstraintsResult/ClientContext für Kontext)
- **Tools:** DeepResearch-Agent-Tool (externe Recherche), Code Interpreter nur für Export

### Ablauf (im Prompt vorgeschrieben)

0. **Katalog lesen.** Im ursprünglichen User-Request bereits genannte Technologie-Präferenzen als
   globalen Recherche-Scope übernehmen.
1. **Rückfrage-Gate (Human-in-the-Loop):** Alle Bausteine mit `needs_clarification = true` bündeln
   und den User fragen — je Baustein die `candidate_directions` + `clarification_question`, plus
   ein Angebot zur globalen Eingrenzung („nur Microsoft-/Azure-Stack?"). **Auf Antwort warten**,
   bevor recherchiert wird. Gibt es keine geflaggten Bausteine, entfällt das Gate.
2. **Scope fixieren:** Antworten je Baustein in den Recherche-Scope übernehmen.
3. **DeepResearch** pro Baustein (auf den bestätigten Scope begrenzt) → Technologien + Best
   Practices, **immer mit Quellen**. Keine erfundenen Quellen.
4. **Konvergenz:** je Baustein genau **eine** empfohlene Technologie/Lösung. Alternativen erscheinen
   nur zur Begründung der Wahl.
5. **Verdichtung** zu *einer* kohärenten Gesamtlösung.
6. **Ausgabe** als Markdown gemäß Kapitelstruktur.

### Regeln
- Jede Empfehlung ist auf die `evaluation_criteria` und die adressierten FR/NFR-IDs zurückzuführen.
- Constraints aus dem Katalog sind bindend — keine Empfehlung, die eine technische Restriktion verletzt.
- Keine offenen Technologie-Wahlmöglichkeiten am Kunden — Ergebnis ist eindeutig.

### Kapitelstruktur (frei gewählt)

1. **Recherche-Vorgehen & Scope** — Methode, bearbeitete DeepResearch-Fragen, Quellenlage,
   ggf. vom User gesetzte Eingrenzungen.
2. **Lösungslandschaft im Überblick** — Zielarchitektur-Vision, Zusammenspiel der Bausteine.
3. **Lösungsbausteine im Detail** (je SB-xx): adressierte Anforderungen · Technologie-Optionen
   (Vergleichstabelle: Option | Reifegrad | Kriterien-Fit | Vor/Nachteile | Quelle) · Best Practices
   (zitiert) · **Empfehlung + Begründung**.
4. **Verdichteter Gesamt-Lösungsvorschlag** — eindeutige, integrierte Zielarchitektur,
   Integrationssicht, NFR-Erfüllung.
5. **Technologie-Stack-Übersicht** — Tabelle Baustein → empfohlene Technologie → Rolle.
6. **Annahmen, Risiken & offene Rechercheragen.**
7. **Quellenverzeichnis** — alle DeepResearch-Quellen mit Zitat/URL.

## Integration in die bestehende Chain

- **`plan.json`:** neue `Solution`-Phase mit den zwei Schritten; `Proposal` erhält
  `SolutionCatalogResult.json` und `SolutionProposalResult.md` als zusätzliche `batch`-Inputs.
- **`AGENT.md`:**
  - Workflow-Liste um Phase `Solution` (2 Schritte) erweitert; Sequenz vor `Proposal`.
  - Dependency-Regeln: `SolutionCatalog` nach `Functional`/`Constraints`/`ClientContext`;
    `SolutionProposal` nach `SolutionCatalog`; `Proposal` nach `Solution`.
  - **DeepResearch explizit und ausschließlich für `SolutionProposal` erlaubt** — im bewussten
    Kontrast zur RAG-only-Regel der Tender-Analyse. Die Tender-Analyse bleibt RAG-only.
  - **Rückfrage-Gate als verpflichtende Interaktion**: `SolutionProposal` MUSS den User zu den
    geflaggten Bausteinen fragen, bevor DeepResearch läuft (Ausnahme zur sonstigen
    „nicht unnötig nachfragen"-Regel).
  - **Konvergenz-Regel:** finaler Lösungsvorschlag ist singulär/eindeutig.
- **`prompts/proposal.md`:** Kap. 2.3 („Technical Solution and Architecture") nutzt
  `SolutionProposalResult.md` als bevorzugte Quelle für die technische Architektur.
  **Status: geplant, konkrete Verdrahtung final gemeinsam zu bestätigen.**

## Betroffene Dateien

**Neu:**
- `docs/.adesso/skills/proposalgenerator/prompts/solution_catalog.md`
- `docs/.adesso/skills/proposalgenerator/prompts/solution_proposal.md`
- `docs/.adesso/skills/proposalgenerator/schema/solution_catalog.json`
- `docs/.adesso/skills/proposalgenerator/schema/solution_proposal_output.md`

**Bearbeitet:**
- `docs/.adesso/skills/proposalgenerator/plan.json`
- `docs/.adesso/skills/proposalgenerator/AGENT.md`
- `docs/.adesso/skills/proposalgenerator/prompts/proposal.md` (geplant, final zu bestätigen)

## Offene Punkte / später zu bestätigen

- Konkrete Verdrahtung des Lösungsvorschlags in `proposal.md` Kap. 2.3.
- Exakter Aufruf-/Rückgabekontrakt des DeepResearch-Agent-Tools im Runtime (Toolname, Parameter),
  sobald verfügbar — der Prompt wird darauf abgestimmt.
- Confidence-Schwelle (Richtwert 0.5) ggf. nach ersten Läufen kalibrieren.

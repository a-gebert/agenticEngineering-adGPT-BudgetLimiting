# Analyse: SalesGPT-Vergleich + Profiler-Integration (proposalgenerator)

**Datum:** 2026-07-15
**Status:** Analyse / Vorstufe zum Design (Profiler-Design noch offen)
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator/`)

## Anlass

Vergleich der bestehenden proposalgenerator-Prompt-Chain mit einer im Einsatz befindlichen,
konsolidierten Anweisung **„SalesGPT"** (Multi-Persona-Sales-Copilot: AccountGPT + TenderGPT +
ProposalGPT). Ziel: Unterschiede herausarbeiten und ableiten, was in unsere Prompts zu ergänzen
wäre. Daraus entstand die Anschlussfrage, ob der **Profiler-MCP** als eigener Chain-Schritt
integriert werden soll.

## Teil 1 — Architektureinordnung

Die beiden Systeme sind unterschiedliche Genres; das ist für die Bewertung zentral.

| | **SalesGPT** (vorgelegt) | **proposalgenerator-Chain** (Ist) |
|---|---|---|
| Typ | Konversationeller Multi-Persona-Copilot | Deterministische, schema-getriebene Pipeline |
| Steuerung | Modell erkennt Phase / bietet Menüs im Dialog | Fester Chain-Ablauf, `AGENT.md` erzwingt Reihenfolge |
| Abdeckung | Phasen 1–4 (Account → Tender → Angebot → Veredelung) | Tender-Analyse + Lösung + Angebot |
| Output | Markdown im Chat | Schema-validierte JSON-Artefakte + MD/DOCX/PDF |

**Konsequenz:** Konversationelle Elemente von SalesGPT (Phasenmenüs, „Nächste Schritte",
Phasenerkennung, Web-Recherche in Phase 1) sind bewusst **nicht** Teil der Chain bzw. gehören in
die Orchestrierung. Empfehlung ist daher **nicht**, SalesGPT nachzubauen, sondern gezielt die
**inhaltlichen Regeln** zu übernehmen, die in der Chain fehlen.

### Aktueller Chain-Stand (Ist)

```
PreProcessing (ExecutiveSummary, ClientContext, Functional, Formal, Constraints)
   → Solution (SolutionCatalog, SolutionProposal + DeepResearch + HITL-Gate)
   → Consolidation (OpenPoints, Report, Proposal)
   → Export (Proposal.docx, Report.pdf)
```

## Teil 2 — Gap-Analyse (priorisiert)

### 🔴 Hoch

**G1 — adesso-Schreibstil-Regeln fehlen in `proposal.md`.** SalesGPT hat konkrete Vorgaben, die
unser Proposal-Prompt nicht kennt:
- „adesso" immer klein.
- Rechtssichere Sprache: „adesso plant/unterstützt/stellt sicher" statt
  „garantiert/gewährleistet/sichert zu" (haftungsrelevant).
- Gendergerechte Sprache („Mitarbeitende", Doppelpunkt-Schreibweise; „Kunde" ungegendert).
- Kundenname vor adesso, Kundennutzen im Mittelpunkt.
- Einheitliche Platzhalter: `[KUNDENNAME]`, `[PROJEKTNAME]`, `[PREIS in EUR zzgl. MwSt.]`,
  `[AUFWAND in Personentagen]`.
- Längenbasis 277 Wörter/DIN-A4-Seite (wir arbeiten nur mit Seitenangaben ohne Wortanker).

**G2 — Konflikt: `proposal.md` provoziert erfundene adesso-Fakten.** SalesGPT verbietet strikt,
adesso-spezifische Fakten (Referenzen, SLAs, Preise, Personen) zu erfinden, inkl. **Profile-Verbot**
(keine CVs; Verweis auf Profiler). Unser `proposal.md` fordert das Gegenteil:
- Annex A: „2–3 reference projects" + Schlüsselrollen mit Seniorität/Zertifikaten → erfundene
  Referenzen & Profile.
- Kap. 2.5: Team mit Rollen/Seniorität/Allokation → erfundene Personen.
- Kap. 2.7: „tiered SLA table" mit Response/Resolution Times → erfundene SLAs.

Da die Chain nur aus dem Tender speist, werden diese Werte zwangsläufig halluziniert.
→ **Dies ist der Aufhänger für die Profiler-Integration** (Teil 3): echte Profile statt
Halluzination. Für Referenzen/SLAs bleibt: Platzhalter + Verweis auf Fachbereich, sofern keine
verlässliche Quelle angebunden wird.

**G3 — Showstopper- & Bid/No-Bid-Analyse fehlt in der Tender-Phase.** SalesGPT bewertet
Showstopper per Ampel (rot/gelb/grün), setzt harte Ausschlussfristen fett und liefert
Bid/No-Bid-Treiber (Portfolio-Fit, Wettbewerb, Risiken, Ressourcen, Preisdruck). Unsere Chain hat
`formal`, `constraints`, `open_points`, aber keine K.-o.-Risiko-/Showstopper-Bewertung und kein
Bid/No-Bid. Kandidat: eigener Schritt oder Erweiterung von `formal.md`/Report um eine Ampel-Spalte.

### 🟡 Mittel

**G4 — Management Summary an Hot Buttons ausrichten.** SalesGPT strukturiert entlang der
Kunden-Hot-Buttons (Erfolgsfaktoren nummeriert → je Hot Button adesso-Lösung mit Nutzen → warum
adesso → nächste Schritte). Unser `proposal.md` hat eine generische 3-Absatz-Summary. Speisbar aus
`client_context.pain_points` + `strategic_goals` (bereits vorhanden).

**G5 — Faktencheck-/Vier-Augen-Hinweis fehlt.** SalesGPT weist vor Abgabe darauf hin, dass der
Output ein Entwurf ist. Unsere finalen Deliverables tragen keinen solchen Disclaimer.

**G6 — Inline-Quellen im Angebotstext.** SalesGPT: `[n]`-Verweise am Absatzende +
Quellenverzeichnis, sonst „Keine Angabe in den vorliegenden Dokumenten gefunden". Unser Report löst
Quellen sauber über die Aspect-Chain auf; das Proposal selbst zitiert nicht.

### 🟢 Cleanup

**G7 — `prompts/reference.md` ist inkonsistent/verwaist.** Beschreibt noch den alten
Azure-Document-Intelligence-Markdown-Ansatz statt RAG/Document-Search und ist in `plan.json` nicht
als Chain-Schritt gebunden. Kandidat zum Löschen oder Angleichen (passt zu Commit `c28b2ff`: RAG
statt Sandbox-PDF).

## Teil 3 — Profiler-MCP-Integration (offenes Design)

**Auslöser:** G2 (Profile-Verbot). Ein Profiler-MCP kann echte adesso-Profile liefern und damit die
halluzinationsgefährdeten Stellen des Angebots durch reale Daten ersetzen. Zugriff auf den
Profiler-MCP kann bereitgestellt werden.

**Passendes Muster:** Die Chain nutzt bereits „deterministischer Katalog-Schritt → Schritt mit
externem Tool + HITL" (solution_catalog → solution_proposal via DeepResearch). Ein Profiler-Schritt
reiht sich analog ein und sitzt sinnvollerweise **nach der Lösungsrecherche**, weil erst dann
feststeht, welche Skills/Rollen das Zielbild erfordert.

### Offene Entscheidungen (im Brainstorming zu klären)

1. **Scope / was befüllt der Profiler?** (mehrfach möglich)
   - Team-Besetzung Kap. 2.5
   - Kurzprofile/CVs in Annex A
   - Referenzprojekte in Annex A (nur falls Profiler auch Projektdaten liefert)
   - Rollen-/Aufwandsbasis für Kap. 3 (Preise)
2. **Eigener Schritt vs. Integration in `proposal`/`solution_proposal`.**
3. **Ein Schritt oder zwei** (deterministischer „Staffing-Katalog" der benötigten Rollen/Skills →
   Profiler-Matching mit externem Tool + ggf. HITL), analog zum solution-Muster.
4. **Datenschutz/Datensparsamkeit:** Welche Personendaten dürfen ins Angebot (anonymisiert vs.
   namentlich, Verfügbarkeit)? SalesGPT betont Datensparsamkeit.
5. **Fallback**, wenn der Profiler nichts Passendes liefert: Platzhalter + Verweis, kein Erfinden.

### Empfehlungsrichtung (vorläufig, noch nicht freigegeben)

Eigener Schritt in Phase `Solution` **nach** `SolutionProposal`, dem solution-Muster folgend:
deterministische Ableitung der benötigten Rollen/Skills aus Anforderungen + Lösungsvorschlag, dann
Profiler-MCP-Matching auf reale Profile; Ergebnis speist Kap. 2.5 und Annex A des Proposals. Damit
wird G2 an der Wurzel gelöst und `proposal.md` von der Halluzinationsanweisung befreit.

## Nächste Schritte

1. Profiler-Scope + Design final klären (Brainstorming fortsetzen).
2. Umsetzung der Stil-/Compliance-Regeln (G1 + G2) in `proposal.md` bündeln.
3. Showstopper/Bid-No-Bid (G3) als eigener Change bewerten.
4. Cleanup `reference.md` (G7).

# Design: proposalgenerator-Chain — Gewinner-Angleichung

**Datum:** 2026-07-23
**Autor:** Andreas Gebert (mit Claude Code)
**Status:** Design / freigegeben zur Planung
**Vorgänger:** `2026-07-22-infineon-proposal-gap-analysis.md` (Findings)

## Ziel

Die `proposalgenerator`-Prompt-Chain so erweitern, dass sie ein Angebot vom
Kaliber des real gewonnenen Infineon-Angebots erzeugen kann. Grundlage sind die
Findings der Gap-Analyse. Dieses Dokument hält die getroffenen Entscheidungen
fest und beschreibt die Zielarchitektur.

## Getroffene Entscheidungen (Brainstorming 2026-07-23)

| # | Thema | Entscheidung |
|---|---|---|
| 1 | Adaptive Kapitelstruktur | **Neuer `ProposalOutline`-Step** vor `Proposal` |
| 2 | Produkt-/UX-Design | **Neuer `ProductDesign`-Step** in Phase Solution |
| 3 | adesso-Institutionswissen | **Kuratierte Referenzdatei** im Skill-Bundle |
| 4 | Anonymisierung vs. Klarnamen | **Voll anonym belassen** — Konflikt nur dokumentiert |
| 5 | Solution-Paradigma | **Tender-Re-Read + vorgeschriebene Tech entschieden übernehmen** |
| 6 | Preismodell | **Estimator-Rollentabelle behalten, nur aufräumen** (kein "XXX", 60 Tage) |
| 7 | Wiring | **plan.json + AGENT.md mitplanen** (neue Steps sonst inaktiv) |

## Zielarchitektur

### Chain-Struktur

Zwei neue Steps. Alle übrigen Steps und Reihenfolgen bleiben.

**Phase Solution** — `ProductDesign` nach `SolutionProposal`:

```
SolutionCatalog → SolutionProposal → ProductDesign(NEU) → StaffingCatalog → ProfilerMatch → Estimator
```

**Phase Consolidation** — `ProposalOutline` nach `Report`, vor `Proposal`:

```
ExecutiveSummary → OpenPoints → Report → ProposalOutline(NEU) → Proposal
```

### Neue Komponente A — ProductDesign (Content-Erzeuger)

**Zweck:** screen-by-screen Feature-/Interaktionsverhalten aus den User Stories
ableiten (Kap. 2.2 des Gewinners, größte Lücke der Chain).

- **Prompt:** `/prompts/product_design.md` (neu)
- **Schema/Output:** `/schema/product_design.json` (neu) → `ProductDesignResult.json`
- **Batch-Inputs:** `Functional.json` (User Stories), `SolutionProposal.md` (Tech-Kontext)
- **Inhalt:** je Screen/Workflow eine Verhaltensbeschreibung (Trigger → UI-Reaktion →
  Folgezustand), abgeleitet aus FR/NFR. Kein freies Erfinden ohne Requirement-Bezug —
  jede Screen-Aussage muss auf ein Functional-Requirement rückführbar sein.
- **Determinismus:** keine Web-Recherche, keine externen Quellen.

### Neue Komponente B — ProposalOutline (Struktur-Planer)

**Zweck:** adaptive Kapitelstruktur je Angebot. Gleiches Muster wie `OpenPoints`
(Gap-Analyse), aber auf **Struktur** statt Requirements.

- **Prompt:** `/prompts/proposal_outline.md` (neu)
- **Schema/Output:** `/schema/proposal_outline.json` (neu) → `ProposalOutlineResult.json`
- **Batch-Inputs:** alle vorhandenen Artefakte (ClientContext, Functional, Formal,
  Constraints, SolutionCatalog, SolutionProposal, ProductDesign, StaffingCatalog,
  ProfilerMatch, Estimator, ExecutiveSummary, OpenPoints)
- **Rubrik** (feste Checkliste der Standard-Dimensionen eines Gewinner-Angebots):
  Exec Summary, Architektur, Produkt/UX, Business Logic, Import/Export,
  Non-functional, Methodik/SCRUM, QM, App-Mgmt/SLA, Transition/Migration,
  Compliance-Liste, Key Personnel, Firmenprofil/Referenzen, Preis, T&C, Risiko.
- **Ausgabe je Dimension:** Status `present | activate | n/a`, Begründung,
  **Artefakt-Zitat als Evidenz**, bei `activate`: Heading, Zweck, Quell-Artefakte,
  Ziellänge. Ergebnis = geordnetes Outline.
- **Evidenz-Pflicht** verhindert Halluzination. **Baseline-Set** (immer `present`:
  Exec Summary, Architektur, Preis, T&C) sichert Determinismus.

**Bedingte-Kapitel-Trigger:**

| Kapitel | Aktiviert wenn |
|---|---|
| Transition/Migration | Migrations-Requirements in Functional/Constraints |
| Betrieb & SLA | NFR Availability/Support vorhanden |
| Risiko | hohe Severity in OpenPoints/Constraints |
| Compliance-Liste | bindende Formal-Requirements vorhanden |
| Produkt/UX | `ProductDesignResult.json` nicht leer |

### Neue Komponente C — adesso-Wissensquelle

- **Datei:** `/references/adesso_facts.md` (neu), kuratiert + versioniert
- **Inhalt:** Maître-Konzept, adVANTAGE-Budgetcontrolling, JourFixe, Monitoring-Team,
  "25 Jahre", ISO 9001/14001/27001, Finanzkennzahlen, Standorte, Org, Methodik-/QM-/
  SLA-Bausteine.
- **Konsumenten:** `executive_summary.md`, `proposal.md`.
- **Regel:** Prompts dürfen **nur** aus dieser Datei zitieren, kein Erfinden.
  Konsistent mit AGENT.md-Erfindungsverbot.

### Geänderte Prompts (bestehend)

**`solution_catalog.md` + `solution_proposal.md`** (Finding 2):
- Tender-Re-Read: tenderspezifische Tech-Vorgaben (z.B. Active-PDF→pdftron,
  bestehender SQL Server, DITA-XML, TXT-Import) erneut einlesen und erhalten.
- Vorgeschriebene Tech **entschieden übernehmen** ohne Optionsvergleich/Zitatenzwang.
- Produktnamen-Verbot **gelockert** — konkrete Produkte erlaubt, **aber nur** wo der
  Tender sie vorgibt. Prompt grenzt scharf ab: kein Produktname für offene Blöcke.
- Web-Recherche nur noch für echt offene Blöcke.
- Konvergenz-Regel (eine empfohlene Tech je Block) bleibt.

**`proposal.md`** (Findings 1, 3, 7, 8):
- Rendert **aus `ProposalOutlineResult.json`** statt fixer Struktur.
- Requirements-Tabelle optional/raus — Anforderungserfüllung im Fließtext-Narrativ.
- Bedingte Kapitel mit Bausteinen: Migration/Transition (Delta-Transition,
  Read-only-Cutover, Log-Files), detailliertes SCRUM, QM (ISTQB, Testpyramide,
  Quality-Gates), operative SLA-Prio-Tabelle, Risiko.
- Produkt/UX-Kapitel aus `ProductDesignResult.json`.
- Entschiedener Scoping-Ton inline erlaubt statt reflexives Deferieren in OpenPoints.
- Firmenprofil-Tiefe aus `adesso_facts.md`.
- Preiskapitel-Cleanup: kein `"XXX"`, Zahlungsziel 60 Tage.

**`executive_summary.md`** (Finding 5):
- adesso-Fakten (Maître, Mission-Bezug) aus `adesso_facts.md`.
- Preisbegründung (Festpreis/T&M-Rationale).

**`estimator.md`** (Finding 6):
- `"XXX"`-Platzhalter raus, Zahlungsziel 60 Tage. Rollentabelle bleibt als interne
  Kalkulationsgrundlage + Kundentabelle.

### Wiring

**`plan.json`:**
- `ProductDesign` in `Solution` (step 3), `next`/Vorgänger-`next` anpassen, batch-Inputs.
- `ProposalOutline` in `Consolidation` (nach Report), `next`-Verkettung, batch-Inputs.

**`AGENT.md`:**
- Workflow-Liste: `ProductDesign` als Schritt 7 (Solution), `ProposalOutline` als
  Schritt vor Proposal einschieben, Folge-Nummerierung anpassen.
- Dependency-Rule: neue Steps + ihre Vorbedingungen ergänzen.
- Referenzdatei `adesso_facts.md` als erlaubte Wissensquelle für die genannten Steps
  dokumentieren (Ausnahme zum Erfindungsverbot).

## Bewusst NICHT im Scope (nur dokumentiert)

- **Anonymisierung unverändert.** Klarnamen-Konflikt (Finding 4: X-FAB-Branchentrumpf,
  benannte Referenzen, Vorstandsnamen, CVs) bleibt offen. Policy bleibt voll anonym.
  Die Chain erreicht den Gewinner hier strukturell nicht — bewusst akzeptiert.
- Kein benanntes Personal, keine CVs.
- adesso-Wissensquelle nur für Institutions-/Firmenfakten, nicht für Personendaten.
- Kein voller Pricing-Matrix-Umbau (Estimator-Cleanup statt Modellwechsel).

## Risiken

- Zwei neue Steps → längere Laufzeit, mehr Tokens je Angebot.
- `adesso_facts.md` muss gepflegt werden (Finanzkennzahlen veralten).
- Gelockertes Produktnamen-Verbot: Modell könnte auch bei offenen Blöcken Produkte
  nennen → Prompt-Abgrenzung muss scharf sein, Eval nötig.

## Teststrategie

- Jeder neue Prompt: Schema-Konformität des Outputs (JSON validiert gegen sein Schema).
- `ProposalOutline`: Baseline-Dimensionen immer `present`; bedingte Kapitel feuern nur
  bei passender Artefakt-Evidenz (Trigger-Tabelle).
- `ProductDesign`: jede Screen-Aussage auf ein Functional-Requirement rückführbar.
- Solution-Prompts: Produktnamen nur bei tender-vorgegebenen Blöcken (Negativ-Test:
  offener Block → kein Produktname).
- Regressions-Eval mit Infineon-Tender: erzeugte Kapitelliste vs. Gewinner-Struktur.

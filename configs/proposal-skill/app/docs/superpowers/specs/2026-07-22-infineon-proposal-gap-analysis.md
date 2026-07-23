# Gap-Analyse: Infineon-Gewinnerangebot vs. proposalgenerator-Chain

**Datum:** 2026-07-22
**Autor:** Andreas Gebert (mit Claude Code)
**Status:** Findings / Analyse (keine Implementierung)

## Kontext

Vergleich eines real gewonnenen adesso-Angebots gegen die aktuelle
`proposalgenerator`-Prompt-Chain, um zu verstehen, warum die Chain dieses
Angebot in seiner jetzigen Form **nicht** erzeugen würde.

**Analysierte Quellen:**

| Dokument | Umfang | Rolle |
|---|---|---|
| `Infineon.pdf` — "Requirements PSS Datasheet Tool ePower 2.0" | 29 S. | Ausschreibung (RfP) |
| `Proposal_adesso_Infineon_RfP ePower 2.0.pdf` | 52 S. | Gewinner-Angebot adesso |
| `AGENT.md`, `plan.json`, alle Kern-Prompts | — | aktuelle Chain |

Bilder/Screenshots (Figures im Angebot) wurden bewusst ignoriert.

### Ausschreibung — Kurzfassung
Infineon (Power & Sensor Systems) will das Alt-Tool "ePower" (Classic ASP,
SQL Server, End-of-Life Sep/Okt 2023) ersetzen. Neues Tool erzeugt Datenblätter
(Tabellen + Diagramme) aus technischen Importdaten, mit Workflow/Approval,
PDF-Rendering, ~500 Nutzer EU/US, ~1800 Datenblätter. Anforderungen als
~130 User Stories (MoSCoW), plus ER-Modell, Rollenkonzept, KPIs/Performance-Korridor.
Tender nennt konkrete Tech-Hinweise: Active-PDF-Toolkit → Upgrade auf pdftron.com
prüfen; bestehender SQL Server; Export DITA-XML; TXT-Importformat.

### Gewinner-Angebot — Struktur
1. Executive Summary (Mission-Bezug, Maître-Konzept, T&M+Festpreis-Begründung, Budget-Transparenz)
2. Detailed proposal
   - 2.1 Architektur (.NET 6, ASP.NET Core, Angular, TS, MS SQL + Filestream, PDFTron; DDD)
   - **2.2 User Interface (~8 S., screen-by-screen UX-Narrativ)**
   - 2.3 Business Logic (WYSIWYG-docx-Templates, Diagramm-Templates, Filestream)
   - 2.4 Import (Migration, Delta) / 2.5 Export (PDF/TXT/DITA-XML, REST-API)
   - 2.6 Non-functional / 2.7 Agile (SCRUM detailliert) / 2.8 QM (ISTQB, Testpyramide, Quality Gates) / 2.9 Application Mgmt (SLA Prio I–IV)
3. Transition/Migration-Konzept (eigenes Kapitel: Delta-Transition, Read-only-Cutover, Log-Files)
4. Compliance List (Attachment)
5. Key Personnel (benannte Beispielprofile + CVs)
6. Background (Firmenprofil, benannte Referenzen X-FAB/medgineering/Sprint, Finanzen, Org, ISO)
7. Price (Verweis Pricing-Matrix xlsx; Festpreis+T&M; 60 Tage)
8. Conditions (Legal T&C) / 9. Bidder's statement / 10. Commitment Period / Appendix A

## Struktur-Mapping: Angebot vs. Chain

| Gewinner-Kapitel | Chain-Erzeuger | Lücke |
|---|---|---|
| Exec Summary (Maître, Mission, T&M-Begründung) | `ExecutiveSummary` (nur Tender + Solution) | adesso-Institutionswissen fehlt |
| 2.1 Architektur (konkret, tenderkonform) | `SolutionProposal` | Web-Recherche + Optionsvergleich statt entschiedener konkreter Stack |
| **2.2 User Interface (screen-by-screen)** | **keiner** | größte Lücke |
| 2.3 Business Logic (Produkt-Verhalten) | `SolutionProposal` / proposal 2.3 | Feature-/Verhaltensbeschreibung fehlt |
| 2.4/2.5 Import + Export (DITA-XML, TXT-Format) | `SolutionProposal` | tenderspezifische Details verloren |
| 2.7 SCRUM detailliert | proposal 2.4 | nur generisch |
| 2.8 QM (ISTQB, Testpyramide, Quality Gates) | proposal 2.6 | nur generisch |
| 2.9 Application Mgmt (SLA Prio-Tabelle) | proposal 2.7 | grob vs. operativ |
| **3 Transition/Migration (eigenes Kapitel)** | **keiner** (nur `OpenPoints`) | fehlt |
| 6.2 Referenzen (Klarnamen, Tech-Stacks) | Annex A (`ProfilerMatch`, **anonymisiert**) | Policy verbietet Klarnamen |
| 6.1 Firmenprofil (Umsatz/EBITDA 4J, Org, ISO) | Annex B (Kurz-Blurb) | Tiefe fehlt |
| 5 Key Personnel (benannte Profile + CVs) | 2.5 / Annex A (**anonym**) | Policy-Konflikt |
| 7 Preis (Pricing-Matrix, Festpreis+T&M, 60 Tage) | Kap. 3 (Personentage-Tabelle, "XXX", 10 Tage) | Modell-Mismatch |

## Findings — die harten Lücken

### 1. Kein Produkt-/UX-Konzept-Erzeuger (größte Lücke)
Herzstück des Gewinners (Kap. 2.2, ~8 Seiten) ist ein detailliertes,
screen-by-screen Feature-Narrativ: "Klickt der Nutzer auf Add, öffnet sich ein
Menü mit 10 Optionen…", Workflow mit max. 10 Quality-Nodes, Deadline-Fallback-Logik,
Infinite-Scroll/Lazy-Loading, Favoriten-Filter, iFrame für Links, Vergleichsansicht,
Mass-Edit von Workflows. Das ist **erfundenes, plausibles Produkt-Design** aus
~130 User Stories.

Die Chain hat dafür keinen Schritt: `functional.md` extrahiert nur FR/NFR-Tabellen;
`SolutionProposal` liefert Technologie-Auswahl (Architektur, Tech-Stack,
Optionstabellen mit `[Sn]`-Zitaten). Niemand schreibt Screen-Verhalten /
Interaktionsdesign.

### 2. Falsches Solution-Paradigma
Chain = Web-Recherche + Optionsvergleich + Zitate. Der Tender **schreibt Tech vor**
(Active-PDF → pdftron.com, bestehender SQL Server, DITA-XML) und der Gewinner
**übernimmt sie entschieden, ohne Zitate**. Zusätzlich: nach `functional.md` wird
der Tender nie wieder gelesen (`solution_catalog` ist deterministisch aus FR/NFR,
`solution_research` nur Web, Tender ausdrücklich nicht re-analysiert).
→ Tenderspezifische Tech-Hinweise gehen verloren. `solution_catalog.md`
**verbietet sogar konkrete Produktnamen** — genau das, was das Angebot durchweg nennt.

### 3. Requirements-Tabelle, die der Gewinner bewusst weglässt
`proposal.md` 2.2 kippt FR/NFR-Tabellen ins kundengerichtete Dokument. Der Gewinner
hat **keine** Requirements-Tabelle — Compliance liegt als separates Attachment (docx),
Anforderungserfüllung ist in Fließtext-Feature-Narrativ gewoben.

### 4. Anonymisierungs-Policy kollidiert direkt
`proposal.md` + `AGENT.md` erzwingen: keine Personennamen, keine Kundennamen,
Referenzen nur anonym aus `ProfilerMatch`. Der Gewinner **lebt** von Klarnamen:
X-FAB (Halbleiter-Branchenreferenz = Schlüssel-Trumpf!), medgineering, Sprint
Sanierung mit vollem Tech-Stack, Vorstandsnamen, benannte Beispielprofile + CV-Anhänge.

### 5. adesso-Institutionswissen hat keine Quelle
Maître-Konzept, adVANTAGE-Budgetcontrolling, JourFixe, eigenes Monitoring-Team,
"25 Jahre", ISO 9001/14001/27001, Finanzkennzahlen, 56 Niederlassungen.
`AGENT.md` verbietet Faktenerfindung — aber kein Prompt-Input liefert dieses Wissen.
Die Chain **kann** es strukturell nicht produzieren.

### 6. Preismodell-Mismatch
`Estimator` → Personentage-Range je Rolle → Tabelle mit "XXX"-Tagessätzen.
Gewinner: **keine** Personentage-Rollentabelle, sondern Verweis auf beigelegte
Pricing-Matrix + Festpreis/T&M-Hybrid mit Begründung in der Exec Summary.
Zahlungsziel 60 vs. 10 Tage.

### 7. Ambiguität: entschieden scopen vs. deferieren
Gewinner trifft mutige Scoping-Entscheidungen inline ("Sub-Templates aus diesem
Angebot ausgeschlossen, in Implementierung klären"; "API nur simpler Token,
komplexe Security nicht abgedeckt"). Die Chain schiebt Unklares in
`OpenPoints`/Clarification-Gate als "Themen zur gemeinsamen Klärung" — defensiver,
anderer Ton.

### 8. Fehlende eigenständige Kapitel
Dediziertes Transition/Migrations-Kapitel (Delta-Transition, Read-only-Cutover,
Log-Files), detailliertes SCRUM, ISTQB/Testpyramide, operatives SLA-Modell.
In `proposal.md` bestenfalls generisch, meist gar nicht.

## Fazit — zwei Kategorien

**Strukturell schließbar (Prompt-Arbeit):**
- Dediziertes Migrations-/Transition-Kapitel
- Konkretere QM- / SCRUM- / SLA-Prompts (mit Bausteinen wie Testpyramide, SLA-Prio-Tabelle)
- Requirements-Tabelle raus bzw. optional stellen
- Preiskapitel an Pricing-Matrix-Modell anpassen
- Tender-Re-Read im Solution-Schritt (tenderspezifische Tech-Hinweise erhalten)

**Fundamental fehlend (neue Chain-Bausteine / Wissensquellen nötig):**
- (a) **Produkt-/UX-Design-Schritt**, der Feature-Verhalten screen-by-screen aus den
  User Stories ableitet — das größte Loch
- (b) **adesso-Wissensquelle** für Institutions-/Firmenfakten (Maître, Finanzen, Zertifikate, …)
- (c) Auflösung des **Anonymisierung-vs-Klarnamen**-Konflikts für Referenzen/Personal

## Lösungsrichtung: adaptive Kapitelstruktur (Diskussion, noch nicht entschieden)

Frage aus dem Gespräch: generische Kapitel erzeugen + Modell überlegen lassen,
welche Kapitel noch rein müssen. Empfohlener **hybrider** Ansatz:

1. **Statisches Skelett** in `proposal.md` verbreitern — tenderunabhängige generische
   Kapitel (Methodik, QM, App-Mgmt/SLA, Firmenprofil, T&C, Risiko) mit festem
   Boilerplate + wenigen artefakt-gespeisten Slots. Deterministisch, garantiert vorhanden.

2. **Bedingte Kapitel** aus kuratiertem Katalog, je an Artefakt-Evidenz gekoppelt
   (kein freies Erfinden):
   - Transition/Migration ← Migrations-Reqs in Functional/Constraints
   - Betrieb & SLA ← NFR Availability/Support vorhanden
   - Risiko ← hohe Severity in OpenPoints/Constraints
   - Compliance-Liste ← bindende Formal-Reqs

3. **Neuer Planungs-Step "ProposalOutline"** vor `proposal.md`: liest alle Artefakte +
   eine **Rubrik** (Checkliste der Standard-Dimensionen eines Gewinner-Angebots),
   markiert je Dimension `vorhanden / aktivieren / n.a.` **mit Begründung + Artefakt-Zitat**,
   gibt geordnetes Outline aus (Heading, Zweck, Quell-Artefakte, Ziellänge).
   `proposal.md` rendert dann **aus dem Outline** statt aus fixer Struktur.
   Gleiches Muster wie `OpenPoints` (Gap-Analyse), aber auf **Struktur** statt Requirements —
   Rubrik erzwingt Vollständigkeits-Check, Evidenz-Pflicht verhindert Halluzination,
   Baseline sichert Determinismus (vgl. `AGENT.md` Determinism-Rule).

**Wichtig:** Struktur-Planung liefert nur das überzeugende Gerüst. Aktivierte Kapitel
brauchen weiterhin **Content-Erzeuger** (UX-Design-Autor für 2.2, adesso-Wissensquelle
für Firmen-/Institutionsfakten). Sonst: schön geplantes, aber leeres Kapitel.

## Nächster Schritt
Vor Implementierung Brainstorming-Runde: Baseline-Set festlegen, bedingten
Katalog + Trigger definieren, Rubrik-Dimensionen, Outline als eigener Step vs. Teil
von `proposal.md`. Danach Prompt-Edits + `plan.json`-Sync.

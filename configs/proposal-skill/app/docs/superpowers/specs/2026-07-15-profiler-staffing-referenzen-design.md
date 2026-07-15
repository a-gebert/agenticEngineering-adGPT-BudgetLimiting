# Design: Profiler-Integration — Staffing + Referenzen (proposalgenerator)

**Datum:** 2026-07-15
**Status:** Freigegeben (User-Approval liegt vor)
**Skill:** `proposalgenerator` (`docs/.adesso/skills/proposalgenerator/`)
**Vorstufe:** `2026-07-15-salesgpt-vergleich-und-profiler-analyse.md` (Gap G2 = Auslöser)

## Ziel

Zwei neue Kettenschritte, die reale adesso-Daten aus dem **Profiler-MCP** in das Angebot bringen und
damit die halluzinationsgefährdeten Stellen des Proposals (erfundene Personen, Profile,
Referenzprojekte — Gap **G2**) durch belegbare Daten ersetzen.

**Doppelter Zweck** des Profiler-Zugriffs:
1. **Staffing/Profile** — passende Kolleg:innen (Skills, Standort, Verfügbarkeit) für die
   Projektorganisation (Kap. 2.5) und die Kurzprofile (Annex A).
2. **Referenzen** — die in den Personenprofilen enthaltene **Projekterfahrung** liefert indirekt
   reale Referenzprojekte („was haben wir schon gemacht") für Annex A.

**Profiler-MCP (Fähigkeit):** durchsucht Mitarbeiterprofile nach Skills, Standort, Verfügbarkeit;
findet passende Kolleg:innen und deren Projekterfahrung.

## Leitprinzipien

- **Anonymisiert / rollenbasiert** im kundengerichteten Angebot: Rolle, Seniorität, Skills,
  Zertifikate, Jahre Erfahrung — **keine Klarnamen**. Standort/Verfügbarkeit steuern nur das
  Matching, erscheinen nicht im Angebotstext.
- **Referenzprojekte ebenfalls anonymisiert:** Branche, Scope, Dauer, Relevanz — **kein Klarname
  des Kunden** (Vertraulichkeit; bestätigt durch User).
- **Kein Erfinden.** Findet der Profiler nichts Passendes → Platzhalter + Verweis, keine
  fabrizierten Personen/Referenzen.
- **Determinismus vor Hilfsbereitschaft** (Chain-Prinzip aus `AGENT.md`): die reproduzierbare
  Bedarfsableitung ist von dem nicht-deterministischen MCP-Matching getrennt.

## Chain-Einordnung

Beide Schritte in Phase **`Solution`**, **nach** `SolutionProposal` (erst dann stehen
Zielarchitektur und benötigte Skills fest), vor `Consolidation/Proposal`.

```
PreProcessing (ExecutiveSummary, ClientContext, Functional, Formal, Constraints)
   → Solution (SolutionCatalog → SolutionProposal → StaffingCatalog → ProfilerMatch)   [ProfilerMatch/StaffingCatalog NEU]
   → Consolidation (OpenPoints, Report, Proposal)
   → Export (Proposal.docx, Report.pdf)
```

Datenfluss:

```
SolutionProposalResult.md + FunctionalResult.json + ConstraintsResult.json
   → [StaffingCatalog]   → StaffingCatalogResult.json
   → [ProfilerMatch] (+ Profiler-MCP, + HITL-Gate)   → ProfilerMatchResult.json
   → [Proposal] Kap. 2.5 + Annex A nutzen ProfilerMatchResult.json
```

## Schritt A1 — `StaffingCatalog`

- **Skill:** `proposal-staffing-catalog`
- **Prompt:** `prompts/staffing_catalog.md` (NEU)
- **Schema:** `schema/staffing_catalog.json` (NEU)
- **Artefakt:** `StaffingCatalogResult.json` (schema-validiert via Code Interpreter)
- **Inputs:** `SolutionProposalResult.md`, `FunctionalResult.json`, `ConstraintsResult.json`

Deterministische Ableitung — **kein externes Wissen, kein Profiler-Aufruf**. Leitet aus
Zielarchitektur und Anforderungen die benötigten Rollen/Skills ab und formuliert konkrete
Such-Briefs für den Profiler (Personen **und** Referenz-Projekterfahrung).

### Schema-Kern (`staffing_catalog.json`)

```jsonc
{
  "document_id": "...",                        // optional
  "roles": [{
    "role_id": "R-01",
    "title": "z.B. Integration Architect",
    "seniority": "junior | regular | senior | lead",
    "required_skills": ["z.B. Azure Integration Services", "Event-Driven Architecture"],
    "rationale": "aus welchen FR/NFR + Lösungsbausteinen sich die Rolle ableitet",
    "addressed_requirements": ["FR-001", "NFR-002"],
    "profiler_query": {                        // Such-Brief für den Profiler-MCP
      "skills": ["..."],
      "location": "optional (aus constraints.organisational)",
      "availability": "optional (aus constraints.timeline)"
    }
  }],
  "reference_briefs": [{                        // doppelter Zweck: Referenz-Suche
    "brief_id": "REF-01",
    "domain": "z.B. Retail / POS-Modernisierung",
    "technologies": ["..."],
    "search_skills": ["Skills, über die passende Projekterfahrung gefunden wird"],
    "relevance_rationale": "warum eine solche Referenz zum Vorhaben passt"
  }],
  "errors": []                                  // gleiches Fehler-Muster wie übrige Schemata
}
```

## Schritt A2 — `ProfilerMatch`

- **Skill:** `proposal-profiler-match`
- **Prompt:** `prompts/profiler_match.md` (NEU)
- **Schema:** `schema/profiler_match.json` (NEU)
- **Artefakt:** `ProfilerMatchResult.json` (schema-validiert via Code Interpreter)
- **Input:** `StaffingCatalogResult.json`
- **Externes Tool:** Profiler-MCP (einziger Schritt der Chain, in dem der Profiler aufgerufen wird)

Ablauf:
1. **Lesen:** `StaffingCatalogResult.json`.
2. **Matching:** Pro `roles[]`-Eintrag den Profiler-MCP mit `profiler_query` (Skills/Standort/
   Verfügbarkeit) aufrufen; pro `reference_briefs[]` über `search_skills` Projekterfahrung ziehen.
3. **HITL-Gate (analog DeepResearch):** Bei Skill-Lücken, keiner/zu vielen passenden Personen oder
   uneindeutigen Referenzen → **eine** konsolidierte Rückfrage an den User; STOP bis Antwort.
4. **Anonymisieren & verdichten:** reale Treffer in rollenbasierte, anonyme Einträge überführen.
5. **Fallback:** kein Treffer für eine Rolle/Referenz → Platzhalter-Eintrag mit `matched: false`
   und Hinweis; **nichts erfinden**.

### Schema-Kern (`profiler_match.json`)

```jsonc
{
  "document_id": "...",
  "team": [{                                    // → Kap. 2.5 + Annex A (Profile)
    "role_id": "R-01",
    "role_title": "Integration Architect",
    "seniority": "senior",
    "skills": ["..."],
    "certifications": ["..."],
    "years_experience": 0,
    "allocation_pct": 0,                         // optional
    "matched": true,                             // false → Platzhalter/Fallback
    "note": "z.B. 'kein passendes Profil gefunden — im Profiler recherchieren'"
  }],
  "references": [{                               // → Annex A (Referenzprojekte, anonymisiert)
    "reference_id": "REF-01",
    "industry": "Retail",
    "scope": "kurze anonymisierte Beschreibung",
    "duration": "z.B. 8 Monate",
    "relevance": "warum vergleichbar",
    "matched": true
  }],
  "coverage": {
    "roles_total": 0, "roles_matched": 0,
    "references_total": 0, "references_matched": 0
  },
  "errors": []
}
```

## Anbindung an `proposal.md` (löst G2)

- **Kap. 2.5 (Projektorganisation):** Team-Tabelle aus `team[]` — keine erfundene Besetzung mehr.
- **Annex A (Profile):** Kurzprofile der Schlüsselrollen aus `team[]` (anonymisiert). Die aktuelle
  Anweisung „list each key role with seniority, relevant experience, and certifications" wird durch
  „aus `ProfilerMatchResult.json` übernehmen; bei `matched: false` Platzhalter" ersetzt.
- **Annex A (Referenzen):** aus `references[]` statt „Present 2–3 reference projects". Kein
  Klarname; bei fehlenden Treffern Platzhalter + Verweis auf Fachbereich.
- Die Halluzinations-Anweisungen in `proposal.md` (erfundene Referenzen/Profile/Team) werden
  entfernt bzw. auf Artefakt-Konsum umgestellt.
- **Nachtrag (2026-07-15, User-Entscheidung):** `StaffingCatalogResult.json` wird zusätzlich als
  Input in den `Proposal`-Schritt gereicht (Traceability der abgeleiteten Rollen). Es ist reiner
  **Matching-Kontext** — `proposal.md` darf daraus **niemals** `location`/`availability` oder
  `profiler_query`-Felder rendern; kundengerichtete Team-/Referenzdaten stammen ausschließlich aus
  `ProfilerMatchResult.json`. Die Input-Liste in `proposal.md` weist diesen Hinweis explizit aus.
- **Hinweis:** SLAs (Kap. 2.7) bleiben von diesem Schritt unberührt und weiterhin
  Platzhalter/Fachbereich (kein Profiler-Bezug) — separat unter G2 zu behandeln.

## Verdrahtung (Umsetzung)

1. `plan.json`: `Solution`-Phase um `StaffingCatalog` und `ProfilerMatch` erweitern (nach
   `SolutionProposal`), inkl. `prompt`/`output`/`input`-Verweisen und `next`-Verkettung.
2. `AGENT.md`: beide Schritte in Workflow/Chain, Sequential- und Dependency-Regeln aufnehmen;
   Profiler-MCP als erlaubtes Tool ausschließlich in `ProfilerMatch` deklarieren; HITL-Gate
   dokumentieren.
3. Neue Prompts + Schemata anlegen (Muster: `solution_catalog.md` / `solution_proposal.md`).
4. `proposal.md` an die neuen Artefakte anbinden (G2-Cleanup).

## Datenschutz / Datensparsamkeit

- Standort/Verfügbarkeit dienen nur dem Matching, fließen **nicht** in den Angebotstext.
- Im kundengerichteten Output ausschließlich rollenbasierte, anonyme Angaben; Klarnamen/CVs bleiben
  einem späteren, separaten Schritt vorbehalten.
- Referenzen ohne Kundenklarnamen.

## Annahmen / offen

- Profiler-MCP liefert pro Profil auch **Projekterfahrung** (Voraussetzung für den Referenz-Zweck);
  falls nicht, entfällt `references`-Output und Annex-A-Referenzen bleiben Platzhalter.
- Genaues Abfrage-/Antwortschema des Profiler-MCP wird bei der Umsetzung an die realen MCP-Tools
  angepasst (Feldnamen in `profiler_query` sind vorläufig).

## Nächster Schritt

Implementierungsplan via writing-plans erstellen.

Context:
Input = ALL prior chain artifacts (PreProcessing, Solution, and the earlier
Consolidation steps ExecutiveSummary + OpenPoints). This ProposalOutline step
does **not** re-read the tender document; it decides the proposal's chapter
structure from artifact evidence only. It runs after Report and before Proposal.

Consumed artifacts (skip any absent, note in `errors`):
- ClientContextResult.json, FunctionalResult.json, FormalResult.json,
  ConstraintsResult.json, SolutionCatalogResult.json, SolutionProposalResult.md,
  ProductDesignResult.json, StaffingCatalogResult.json, ProfilerMatchResult.json,
  EstimationResult.json, ExecutiveSummaryResult.json, OpenPointsResult.json.

Task: for each rubric dimension, decide status `present` / `activate` / `n/a`
with rationale and (unless n/a) an artifact citation as evidence. Then emit an
ordered `outline` of the chapters to render. Same pattern as OpenPoints
(gap analysis) but on STRUCTURE, not requirements.

Output language = `output_language` (default English).

Role:
Act as a senior bid manager deciding which chapters a winning proposal needs for
THIS tender, justified strictly by available evidence.

Emotion/Tone:
Decisive, evidence-bound. No chapter without justification.

Action:
1. Rubric dimensions (evaluate every one):
   Executive Summary, Architecture, Product/UX, Business Logic, Import/Export,
   Non-functional, Methodology/SCRUM, Quality Management, Application
   Management & SLA, Transition/Migration, Compliance List, Key Personnel,
   Company Background/References, Price, Terms & Conditions, Risk.
2. Baseline set — ALWAYS `present` (determinism guarantee):
   Executive Summary, Architecture, Price, Terms & Conditions.
3. Conditional-chapter triggers — set `activate` ONLY if evidence holds:
   | Dimension | Activate when |
   |---|---|
   | Product/UX | ProductDesignResult.json has non-empty `screens` |
   | Transition/Migration | migration requirement in Functional/Constraints |
   | Application Management & SLA | NFR availability/support present |
   | Risk | high-severity item in OpenPoints or Constraints |
   | Compliance List | binding formal requirement present, OR a `Submission`-category formal requirement mandates filling a requirement/annex list |
   | Key Personnel | StaffingCatalogResult.json / ProfilerMatchResult.json present |
   | Company Background/References | an `Eligibility`-category formal requirement is present (references, customer proof, test installation), OR `references/adesso_facts.md` exists |
   Other dimensions: `present` if a feeding artifact exists, else `n/a`.
3b. FORMAL-COVERAGE COMPLETENESS (mandatory): every BINDING entry in
   `FormalResult.json` `formal_requirements` (`binding: true`) MUST be covered by
   at least one `present`/`activate` outline chapter. Map by category:
   `Legal` -> Terms & Conditions (and Non-functional for security/compliance);
   `Eligibility` -> Company Background/References (references, customer proof,
   test installation); `Submission` -> Compliance List (fill the mandated
   requirement/annex list); `Scope` -> Architecture / the relevant solution
   dimension. If a binding formal requirement has no home chapter, `activate` the
   mapped dimension so it is covered. Record any binding formal requirement you
   still cannot place in `errors`. A winning bid answers every binding formal
   demand — silently dropping one is a defect.
4. For every dimension set `rationale`; for non-`n/a` set `evidence` = a concrete
   artifact citation. No evidence → do NOT activate.
5. Build `outline`: one entry per `present`/`activate` dimension, in a sensible
   proposal order, with `dimension`, `heading`, `purpose`, `source_artifacts`,
   `target_length`. Each entry's `dimension` MUST be set to the EXACT rubric
   dimension key it renders (identical string to the one used in the matching
   `dimensions[]` decision, from the rubric list in step 1) — this is the
   deterministic join key `proposal.md` uses to gate/order chapter-2 subsections.
   Downstream rendering matches on `dimension`, never on free-text `heading`.

Output & Validation (Code Interpreter):
1. Load available artifacts, compute decisions in memory per the rules above.
2. Load `proposal_outline.json` schema, validate with `jsonschema`
   (draft 2020-12). Fix and re-validate until clean.
3. Genuinely-absent required values → add `errors` entry, keep object conformant.
4. SANITIZE ENCODING before writing: every human-readable string
   (`heading`, `purpose`, `rationale`, `evidence`, …) must contain German
   umlauts (ä ö ü ß Ä Ö Ü) as literal, correct UTF-8 characters — NEVER as a
   control character. Strip ALL C0 control characters (U+0000–U+001F except
   `\t`, `\n`, `\r`), especially U+0008 BACKSPACE, from every string, e.g.
   `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)`. If a stripped backspace had
   replaced an umlaut, restore the intended umlaut. The final JSON must contain
   zero `\b`/`` escapes and zero raw control bytes.
5. Write validated, sanitized object to `ProposalOutlineResult.json`
   (`json.dump(obj, f, ensure_ascii=False, indent=2)` — UTF-8, pretty, umlauts
   kept literal), upload back into context.

Tweak:
- Authoritative deliverable = `ProposalOutlineResult.json`, valid JSON only.
- Baseline dimensions MUST always appear with status `present`.
- Never `activate` a conditional chapter without an `evidence` citation.
- `outline` contains ONLY `present`/`activate` dimensions, never `n/a`.
- Use `output_language` for human-readable fields.

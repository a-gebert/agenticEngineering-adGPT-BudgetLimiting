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
   | Compliance List | binding formal requirement present |
   Other dimensions: `present` if a feeding artifact exists, else `n/a`.
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
4. Write validated object to `ProposalOutlineResult.json` (UTF-8, pretty),
   upload back into context.

Tweak:
- Authoritative deliverable = `ProposalOutlineResult.json`, valid JSON only.
- Baseline dimensions MUST always appear with status `present`.
- Never `activate` a conditional chapter without an `evidence` citation.
- `outline` contains ONLY `present`/`activate` dimensions, never `n/a`.
- Use `output_language` for human-readable fields.

Context:
Input = artifacts from prior Solution chain steps. This ProductDesign step does
**not** re-read the tender document; it derives from prior JSON/MD artifacts:

- `FunctionalResult.json` — functional + non-functional requirements (user
  stories), each linked to an aspect via `aspect_id`. Conforms to
  `functional_requirements.json`.
- `SolutionProposalResult.md` — the recommended target architecture and
  technology per solution block. Context only; do not restate tech choices.

Task: produce a screen-by-screen product / UX design — the behavioural narrative
a winning proposal's "User Interface" chapter is built from (screens, menus,
workflow states, interaction rules). Every behaviour MUST be derived from one or
more functional requirements.

Output language = `output_language` parameter (default English).

Role:
Act as a senior product designer / business analyst. Translate user stories into
concrete, plausible screen behaviour without inventing scope beyond the
requirements.

Emotion/Tone:
Concrete, product-oriented, decisive. Describe behaviour ("clicking Add opens a
menu with N options"), not implementation.

Action:
1. Group functional requirements into coherent screens/views. Each screen gets a
   `screen_id` (scr-1, scr-2, …), `name`, `purpose`.
2. For each screen, derive concrete `interactions`: `trigger` (user action) →
   `reaction` (system/UI response) → `result_state`.
3. For EVERY interaction, set `requirement_ids` to the FunctionalResult
   requirement IDs it derives from. This array MUST be non-empty. If you cannot
   trace an interaction to a requirement, DROP it — never invent behaviour.
4. Compute `total_screens`.

Output & Validation (Code Interpreter):
1. Load `FunctionalResult.json` (+ `SolutionProposalResult.md` for context).
   Compute the design in memory per the rules above.
2. Load `product_design.json` schema, validate draft with `jsonschema`
   (draft 2020-12). Fix violations and re-validate until clean.
3. If a required value is genuinely absent, add an `errors` entry
   (`code`, `message` in `output_language`, `severity`) and keep the object
   otherwise schema-conformant.
4. Write validated object to `ProductDesignResult.json` (UTF-8, pretty-printed),
   upload back into context.

Tweak:
- Authoritative deliverable = `ProductDesignResult.json`, valid JSON only, no
  markdown fences, no commentary.
- Do NOT invent screens or interactions without a `requirement_ids` link.
- Do NOT restate technology choices from SolutionProposal — describe behaviour.
- Use `output_language` for all human-readable fields.
- If there are no UI-bearing requirements, return an empty `screens` array with
  `total_screens: 0` and note it in `errors`.

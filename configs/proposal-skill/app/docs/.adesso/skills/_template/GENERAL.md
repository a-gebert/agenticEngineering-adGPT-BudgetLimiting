---
name: my-skill-name
description: >
  A concise description of what this skill does, when it should be triggered,
  and what value it provides. Max 1024 characters.
---

# Purpose

What this skill accomplishes and why it exists.

# Trigger Conditions

When this skill should be activated:

- User says "..."
- User asks to ...
- Matches keywords: `keyword-a`, `keyword-b`

# Prerequisites

- Required tools or CLI access (e.g., `az`, `terraform`, `git`)
- Authentication or permissions needed
- Environment variables or config files expected

# Inputs

| Parameter   | Required | Description              | Default |
|-------------|----------|--------------------------|---------|
| `param-one` | yes      | What this parameter does | —       |
| `param-two` | no       | Optional configuration   | `auto`  |

# Workflow

1. **Gather context** — Read relevant files or fetch state
2. **Validate** — Check prerequisites and inputs
3. **Execute** — Perform the core operation
4. **Report** — Present results to the user

# Error Handling

| Error Condition         | Action                          |
|-------------------------|---------------------------------|
| Missing prerequisite    | Inform user, suggest fix        |
| External service down   | Retry once, then abort cleanly  |
| Invalid input           | Show validation error, ask user |

# Output Format

Describe the expected output structure:

```
## Result
- Status: success | failure
- Summary: ...
- Details: ...
```

# Resources

- `scripts/` — Executable scripts (Python, Bash, JS) for deterministic operations
- `references/` — Documentation loaded into context on-demand (API docs, schemas, guides)
- `assets/` — Templates, images, boilerplate (never loaded into context, copied to output)

# Examples

**Example invocation:**

```
/my-skill-name param-one
```

**Expected output:**

```
Result: ...
```

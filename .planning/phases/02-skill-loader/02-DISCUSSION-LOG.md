# Phase 2: Skill Loader - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 02-skill-loader
**Areas discussed:** Return type

---

## Return type

### What does load_skill() return?

| Option | Description | Selected |
|--------|-------------|----------|
| SkillDefinition dataclass | Passive data holder: name, description, input_class, output_class. Calling code calls the LLM itself. Phase 3 adds result wrapper. | |
| SkillRunner with .run() | Active object with a .run() method that calls the LLM. Phase 3 later wraps the result. | ✓ |
| Plain dict | {name, description, system_prompt, input_class, output_class} — no type safety. | |

**User's choice:** SkillRunner with .run()

---

### What does SkillRunner.run() return in Phase 2 (before Phase 3)?

| Option | Description | Selected |
|--------|-------------|----------|
| Raw LLM output, Phase 3 wraps it | .run() returns the raw LLM response string. Phase 3 wraps in {structured_output, reasoning, confidence}. | |
| Parsed output_schema only | .run() already parses output into the output_schema. Phase 3 adds reasoning/confidence on top. | |
| Full contract in Phase 2 | .run() returns the full {structured_output, reasoning, confidence} contract. Phase 3 just tests/validates it. | ✓ |

**User's choice:** Full contract in Phase 2
**Notes:** Phase 3 becomes a validation/testing phase rather than an implementation phase.

---

### How does SkillRunner get the LLM client?

| Option | Description | Selected |
|--------|-------------|----------|
| Caller injects LLM client | SkillRunner.run(llm_client, input_data) — caller injects the LLM client. | ✓ |
| LLM client at load time | load_skill(name, llm_client) — client passed at load time, runner has it. | |
| Internal LLM factory | SkillRunner uses factory.py internally. | |

**User's choice:** Caller injects LLM client
**Notes:** Consistent with existing AIAgent(ABC) pattern. Clean dependency injection.

---

### What type is SkillResult.structured_output?

| Option | Description | Selected |
|--------|-------------|----------|
| output_schema instance (Pydantic) | Validated instance of the skill's output_schema Pydantic class. Type-safe. | ✓ |
| Plain dict (unvalidated) | Dict parsed from LLM JSON. Simpler but no validation. | |
| Claude's discretion | Pydantic if fields defined, dict fallback for placeholders. | |

**User's choice:** output_schema instance (Pydantic)

---

## Claude's Discretion

- Loader module placement (no discussion — Claude decides)
- SKILL.md parsing depth (no discussion — Claude decides)
- Error exception types (no discussion — Claude decides)

## Deferred Ideas

None — discussion stayed within phase scope.

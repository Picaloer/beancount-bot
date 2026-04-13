# Skills Directory

Each subdirectory in `backend/skills/` is a skill — a self-contained LLM
capability definition that can be loaded and invoked by the skill framework.

## Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Documentation: YAML front matter + sections |
| `input_schema.py` | Pydantic BaseModel subclass defining the skill's input |
| `output_schema.py` | Pydantic BaseModel subclass defining the skill's output |

## Adding a New Skill

1. Create a new subdirectory under `backend/skills/` using kebab-case naming.
2. Create all three required files (`SKILL.md`, `input_schema.py`, `output_schema.py`).
3. Do not modify any existing code — the skill loader discovers skills automatically.

## Naming Conventions

- Directory name: kebab-case — e.g., `cross-channel-dedup`
- Schema class names: PascalCase of directory name + `Input`/`Output` suffix
  - `cross-channel-dedup` → `CrossChannelDedupInput`, `CrossChannelDedupOutput`

## SKILL.md Format

`SKILL.md` must start with a YAML front matter block (triple-dash delimiters),
containing at minimum `name` (kebab-case) and `description` fields.

Required sections (all must be present):

1. `## Purpose` — what the skill does and when it is used
2. `## System Prompt` — the LLM system prompt (inside a fenced code block)
3. `## Input` — description of what the caller passes in, referencing `input_schema.py`
4. `## Output` — description of what the skill returns, referencing `output_schema.py`
5. `## Usage Example` — a code or data example showing a real invocation

Note: The System Prompt section contains the LLM system prompt inside a fenced code block.

## Schema File Rules

- Import ONLY from stdlib and pydantic — no `from app.*` imports
- Export exactly one class per file named `SkillNameInput` / `SkillNameOutput`
- Use `pass` as placeholder body until the skill is fully designed

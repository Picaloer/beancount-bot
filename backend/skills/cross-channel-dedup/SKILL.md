---
name: cross-channel-dedup
description: Identify suspected duplicate transactions across multiple payment channels using LLM semantic comparison grouped by weekly time windows.
---

## Purpose

Cross-channel deduplication detects cases where the same underlying payment appears in
multiple bill exports — for example, a WeChat Pay deduction that also shows up as a CMB
bank card charge. The skill compares already-imported transactions against newly uploaded
transactions, grouped into 7-day sliding windows, and returns suspected duplicate pairs.

Used by: the import pipeline before classification (Phase 5 gate).

## System Prompt

```
TODO (Phase 4): Add the LLM system prompt here.
```

## Input

Defined in `input_schema.py` — see `CrossChannelDedupInput`.

TODO (Phase 4): Describe the input fields once the schema is finalized.

## Output

Defined in `output_schema.py` — see `CrossChannelDedupOutput`.

TODO (Phase 4): Describe the output fields once the schema is finalized.

## Usage Example

TODO (Phase 4): Add a code snippet showing how to invoke this skill.

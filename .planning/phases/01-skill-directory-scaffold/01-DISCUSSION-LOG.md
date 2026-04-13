# Phase 1: Skill Directory Scaffold - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 01-skill-directory-scaffold
**Areas discussed:** Schema 文件格式, Skill 目录范围, SKILL.md 结构

---

## Schema 文件格式

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic 模型（.py 文件） | 和现有代码保持一致——现有代码大量使用 Pydantic。Phase 2 的 loader 可以 import 这些模型做 runtime 验证。较平缓、有自动补全。 | ✓ |
| JSON Schema（.json 文件） | 语言无关、标准化程度更高。未来可用于自动生成不同语言的客户端。但 Phase 2 需要用 jsonschema 库进行实资验证（现有代码没有这个依赖）。 | |
| 纯模型（dataclass/TypedDict .py） | 用 Python 标准库的 dataclass/TypedDict，无需额外依赖。但没有 Pydantic 那种 runtime 验证能力。 | |

**User's choice:** Pydantic 模型（.py 文件）

---

## Schema 文件组织

| Option | Description | Selected |
|--------|-------------|----------|
| 单个 schema.py（含 input + output） | 一个 schema.py 文件包含 input 和 output 两个 Pydantic 模型。简洁、易找。 | |
| 分离 input_schema.py + output_schema.py | 分离后 input 和 output 契约各自独立阅读，可以分别独立演化。 | ✓ |

**User's choice:** 分离 input_schema.py + output_schema.py

---

## Skill 目录范围

| Option | Description | Selected |
|--------|-------------|----------|
| 只一个：cross-channel-dedup | 只创建 Phase 4 会用到的 cross-channel-dedup/。避免过早对尚不确定的 skill 做定义。 | ✓ |
| 两个（dedup + transfer） | 同时创建 cross-channel-dedup/ 和 internal-transfer-detection/ 两个。整个 skill 体系在 Phase 1 就内容比较完整。 | |
| 只建 _template/ + 规则文档 | 只建一个 _template/ 模板目录，配合一个 README 说明规则。具体 skill 目录在对应 phase 开始时再创建。 | |

**User's choice:** 只一个：cross-channel-dedup

---

## Skill 内容完整度

| Option | Description | Selected |
|--------|-------------|----------|
| Skeleton（结构正确，内容 TBD） | 只建文件、写好结构和字段定义，内容用 TODO/TBD 占位。具体的 prompt 和验证逻辑留到 Phase 4。 | ✓ |
| 完整内容（prompt + 真实模型） | 把 cross-channel-dedup 的完整 prompt 和真实的输入输出模型都写好。不过现在尚不知道详细需求呢。 | |

**User's choice:** Skeleton（结构正确，内容 TBD）

---

## SKILL.md 结构

| Option | Description | Selected |
|--------|-------------|----------|
| Metadata 头 + 描述 + Prompt（三段式） | 包含: 元数据头部 (name/version/model_hint) + 简短描述 + system prompt 正文。简洁且包含 loader 需要的关键信息。 | |
| 纯 prompt 文本（最简） | 就是纯粹的 system prompt 文本。loader 直接读内容作为 system message。最简单，但缺少 metadata（无法知道这个 skill 的 model 建议或版本）。 | |
| 完整文档（含输入输出描述 + 使用示例） | 可以为其他开发者提供丰富上下文。但过重的文档容易过时。 | ✓ |

**User's choice:** 完整文档（含输入输出描述 + 使用示例）
**Notes:** Phase 1 skeleton 中，示例部分用 TBD 占位，结构先明确

---

## SKILL.md Metadata 字段

| Option | Description | Selected |
|--------|-------------|----------|
| name + version + model_hint + description | 足够识别一个 skill，同时让 Phase 2 的 loader 知道需要带什么模型。 | |
| name + description（最小集） | 只需要 name 和 description。不锁定模型——这由 loader 调用时由调用方决定。 | ✓ |

**User's choice:** name + description（最小集）

---

## Claude's Discretion

- 是否添加顶层 `backend/skills/README.md` 说明约定（推荐：是，用于满足 SC-3 可验证性）
- skeleton schemas 中具体的 Pydantic 基类和字段命名
- SKILL.md 是否用 fenced code block 还是 tagged section 来包裹 prompt

## Deferred Ideas

- 迁移现有 classification/insight prompt 到 skills/ 目录（用户选择跳过，Phase 1 不动现有代码）
- internal-transfer-detection/ skill 目录（Phase 7+ 再创建）
- SKILL.md metadata 中的 `model_hint` / `version` 字段（暂不加，后续如有需要再添加）

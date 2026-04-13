# Requirements: Beancount Bot

**Defined:** 2026-04-13
**Core Value:** 用户导入多渠道账单后，得到准确去重的收支流水 — 不重复统计、不混淆内部转账

---

## Existing Capabilities (Validated)

These capabilities are already implemented and validated in the current codebase.

- ✓ WeChat Pay CSV/XLSX import
- ✓ Alipay CSV import (GBK/GB18030 encoding)
- ✓ CMB (招商银行) PDF import with OCR fallback
- ✓ Rule + LLM 4-stage classification pipeline
- ✓ Beancount double-entry entry generation
- ✓ Monthly spend report with AI insights
- ✓ Merchant ranking report
- ✓ Manual transaction reclassification
- ✓ Async import pipeline (Celery + Redis)
- ✓ Same-source duplicate review during import

---

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Skill Framework

- [ ] **SKILL-01**: 建立 `backend/skills/` 目录，每个 skill 以独立子目录形式存放，包含 `SKILL.md`（定义 skill 的 prompt、输入/输出 schema）和必要的 schema 文件
- [ ] **SKILL-02**: 实现 `load_skill(skill_name)` 机制，动态读取 skill 定义并构造 LLM 调用；skill 定义与业务逻辑解耦，便于独立扩展
- [ ] **SKILL-03**: skill 调用结果统一封装，含 structured output、reasoning、confidence

### Cross-Channel Deduplication

- [ ] **DEDUP-01**: 实现 `cross-channel-dedup` skill：输入为「已导入交易」和「本次上传交易」两份数据，按周分组（7 天滑动窗口），多路并发调用 LLM 进行跨源语义比对
- [ ] **DEDUP-02**: skill 输出每组疑似重复的配对，包含 similarity_score、reasoning、建议保留哪条
- [ ] **DEDUP-03**: 去重覆盖场景：渠道（微信/支付宝）与授权扣款银行卡重复；银行卡之间重复；同渠道内部重复（扩展已有 DuplicateReviewGroup）
- [ ] **DEDUP-04**: 疑似重复结果在导入流程中展示，用户逐组确认（保留/全部保留/跳过），确认后被排除的记录不计入任何统计
- [ ] **DEDUP-05**: 去重 skill 运行于分类 pipeline 之前，输出去重后的干净交易列表供后续阶段使用

### Internal Transfer Detection

- [ ] **TRNF-01**: 实现 `internal-transfer-detection` skill：在去重后的单份数据上，按周分组 + 多路并发，LLM 语义识别内部资金流动记录
- [ ] **TRNF-02**: 识别场景覆盖：银行卡 → 微信/支付宝充值；银行卡间转账；微信/支付宝提现到银行卡；购买基金/理财（资金仍属于用户）
- [ ] **TRNF-03**: skill 输出内部资金流动记录列表，每条含 transfer_type（recharge / bank-transfer / withdrawal / investment）和 reasoning
- [ ] **TRNF-04**: 被标记为内部资金流动的交易：归入新「内部资金流动」类别，不计入支出统计，不计入收入统计
- [ ] **TRNF-05**: 内部转移识别运行于跨渠道去重之后、分类 pipeline 之前

### Display Corrections

- [ ] **DISP-01**: 移除所有页面上的「当前余额」「总资产」展示；系统不具备开户余额数据，此类展示对新用户会产生负值误导
- [ ] **DISP-02**: 汇总页与月报页展示三个统计卡片：当期总收入、当期总支出、当期内部资金流动总额
- [ ] **DISP-03**: 交易列表新增「内部资金流动」分类过滤项（与已有的收入/支出过滤并列）

---

## v2 Requirements

Acknowledged but deferred to future milestones.

### Deduplication Enhancements
- **DEDUP-V2-01**: 用户可配置渠道优先级规则（如「微信优先于招行」），减少需要人工确认的情况
- **DEDUP-V2-02**: 去重置信度阈值可调，低置信度的自动放行

### Internal Transfer Enhancements
- **TRNF-V2-01**: 用户可手动将某笔交易标记为「内部资金流动」
- **TRNF-V2-02**: 投资/理财赎回（资金回流）自动与买入记录配对

### Additional Import Sources
- **IMPORT-V2-01**: 工商银行账单解析
- **IMPORT-V2-02**: 光大银行账单解析
- **IMPORT-V2-03**: 美团账单解析
- **IMPORT-V2-04**: 携程账单解析

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| 当前余额/总资产展示 | 无开户余额数据，新用户会出现负值；按设计排除 |
| 完整 beancount 资产负债表 | 系统定位是现金流追踪，非完整复式记账 |
| 实时银行数据同步 | 仅支持 CSV/PDF 文件导入 |
| 多用户/认证系统 | MVP 单用户模式，auth 在本里程碑范围外 |
| 规则配置渠道优先级 | 规则匹配在跨渠道场景不准确，LLM skill 替代；规则配置UI推迟到 v2 |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SKILL-01 | Phase 1 | Pending |
| SKILL-02 | Phase 2 | Pending |
| SKILL-03 | Phase 3 | Pending |
| DEDUP-01 | Phase 4 | Pending |
| DEDUP-02 | Phase 4 | Pending |
| DEDUP-03 | Phase 4 | Pending |
| DEDUP-05 | Phase 5 | Pending |
| DEDUP-04 | Phase 6 | Pending |
| TRNF-01 | Phase 7 | Pending |
| TRNF-02 | Phase 7 | Pending |
| TRNF-03 | Phase 7 | Pending |
| TRNF-04 | Phase 8 | Pending |
| TRNF-05 | Phase 8 | Pending |
| DISP-01 | Phase 9 | Pending |
| DISP-02 | Phase 9 | Pending |
| DISP-03 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after roadmap creation (traceability updated to 9-phase structure)*

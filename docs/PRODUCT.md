---

# 智能账单助手 MVP 设计文档

---

## 一、产品经理出品：产品设计规格

### 1.1 用户画像

| 画像 | 描述 | 核心痛点 |
|------|------|---------|
| **月光族小李** | 25-35岁，工薪族，每月底才发现钱不知去了哪 | 不知道钱花在了哪里 |
| **精打细算小王** | 有记账习惯，但手动整理耗时，想要自动化 | 整理账单太繁琐 |
| **自由职业者小张** | 需要区分个人/业务支出，有报税/财务规划需求 | 账单混乱，多平台难汇总 |

---

### 1.2 MVP 功能优先级矩阵

```
P0 (必须上线)
├── 微信/支付宝账单 CSV 导入 & 解析
├── 自动规则分类（基础一级分类）
├── LLM 二级细化分类
├── 月度消费报告（图表 + 文字总结）
└── 支出/收入统计看板

P1 (第一个迭代)
├── 商家消费排行榜
├── 分类消费趋势折线图（近6个月）
├── 手动调整分类 + 记忆规则
└── AI 生成消费洞察报告

P2 (未来规划，MVP 不做)
├── 预算设置与超支提醒
├── 多账号合并分析
└── 报告 PDF 导出
```

---

### 1.3 核心用户旅程

**旅程一：导入账单**
```
进入首页 → 点击「导入账单」→ 选择平台(微信/支付宝) 
→ 上传 CSV 文件 → 系统解析预览(展示前10条) 
→ 用户确认 → 后台异步处理(分类+入库) 
→ 完成提示 → 跳转报告页
```

**旅程二：查看月度报告**
```
选择年月 → 展示「总支出/总收入/净额」
→ 饼图：各分类占比
→ 柱图：按周消费分布  
→ 排行榜：TOP10 商家
→ AI 洞察段落（个性化文字描述）
```

---

### 1.4 分类体系设计

```
一级分类（规则引擎）          二级分类（LLM细化）
├── 餐饮                    ├── 外卖/堂食/咖啡/奶茶
├── 购物                    ├── 服装/数码/日用品/奢侈品
├── 娱乐                    ├── 游戏/电影/音乐/视频会员
├── 交通                    ├── 打车/公交/加油/高铁
├── 住房                    ├── 房租/水电/物业/家政
├── 医疗健康                 ├── 医院/药店/健身/保险
├── 教育                    ├── 在线课程/书籍/考试
├── 转账/红包               ├── 家人/朋友/还款
└── 其他                    └── 未识别
```

---

### 1.5 成功指标（MVP 验收标准）

| 指标 | 目标值 |
|------|--------|
| 账单解析成功率 | ≥ 99% |
| 自动分类准确率 | ≥ 85% |
| 页面加载时间 | < 2s |
| 报告生成时间 | < 10s（后台异步）|

---

## 二、架构师出品：系统架构设计

### 2.1 整体架构图

```
┌───────────────────────────────────────────────────────┐
│                    Next.js Frontend                    │
│   Dashboard │ Import │ Reports │ Category Management   │
└───────────────────────┬───────────────────────────────┘
                        │ HTTPS / REST
┌───────────────────────▼───────────────────────────────┐
│                   FastAPI (Python)                     │
│   /api/bills  /api/reports  /api/categories  /api/ai  │
└──────┬──────────────────┬────────────────────┬─────────┘
       │                  │                    │
┌──────▼──────┐   ┌───────▼───────┐   ┌───────▼────────┐
│  PostgreSQL  │   │     Redis     │   │  Celery Worker  │
│  (主数据库)  │   │ (队列+缓存)   │   │  (异步任务)     │
└─────────────┘   └───────────────┘   └───────┬────────┘
                                              │
                                    ┌─────────▼────────┐
                                    │   AI Agent 管道   │
                                    │  Claude API       │
                                    │  ├─ 分类 Agent    │
                                    │  └─ 报告 Agent    │
                                    └──────────────────┘
```

---

### 2.2 核心数据模型

```sql
-- 用户表
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 账单导入批次
CREATE TABLE bill_imports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    source      VARCHAR(20) NOT NULL,  -- 'wechat' | 'alipay'
    file_name   VARCHAR(255),
    row_count   INTEGER,
    status      VARCHAR(20) DEFAULT 'pending',  -- pending/processing/done/failed
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

-- 核心：交易记录表
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    import_id       UUID REFERENCES bill_imports(id),
    source          VARCHAR(20) NOT NULL,
    direction       VARCHAR(10) NOT NULL,   -- 'expense' | 'income' | 'transfer'
    amount          NUMERIC(12, 2) NOT NULL,
    currency        VARCHAR(10) DEFAULT 'CNY',
    merchant        VARCHAR(255),
    description     TEXT,
    category_l1     VARCHAR(50),            -- 一级分类（规则引擎）
    category_l2     VARCHAR(50),            -- 二级分类（LLM）
    category_source VARCHAR(20),            -- 'rule' | 'llm' | 'manual'
    transaction_at  TIMESTAMPTZ NOT NULL,
    raw_data        JSONB,                  -- 原始字段备份
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_at DESC);
CREATE INDEX idx_transactions_category  ON transactions(user_id, category_l1, category_l2);

-- 分类规则表（用户自定义规则）
CREATE TABLE category_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    match_field VARCHAR(20),   -- 'merchant' | 'description'
    match_value VARCHAR(255),
    category_l1 VARCHAR(50),
    category_l2 VARCHAR(50),
    priority    INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 月度报告缓存
CREATE TABLE monthly_reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    year_month  VARCHAR(7) NOT NULL,  -- '2025-03'
    data        JSONB NOT NULL,       -- 报告完整JSON
    ai_insight  TEXT,                 -- AI生成的洞察文字
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, year_month)
);
```

---

### 2.3 账单解析器设计

微信和支付宝的 CSV 格式各不相同，需要独立解析器：

```python
# 解析器接口约定
class BillParser(ABC):
    @abstractmethod
    def parse(self, file_content: str) -> list[TransactionDTO]:
        pass
    
    @abstractmethod
    def detect(self, file_content: str) -> bool:
        """自动识别文件是否属于该格式"""
        pass

# 微信账单特征
# 标题行: 微信支付账单明细
# 字段: 交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注

# 支付宝账单特征  
# 标题行: 支付宝交易记录明细查询
# 字段: 交易号,商家订单号,交易创建时间,付款时间,最近修改时间,交易来源地,类型,
#       交易对方,商品名称,金额（元）,收/支,交易状态,服务费（元）,退款（元）,备注,资金状态
```

---

### 2.4 AI Agent 管道设计

```
┌─────────────────────────────────────────────────────┐
│                 分类 Agent Pipeline                  │
│                                                     │
│  Input: [merchant, description, amount, source]     │
│                                                     │
│  Step 1: 规则引擎匹配                               │
│    ├── 命中 → 直接返回，标记 source='rule'          │
│    └── 未命中 → 进入 LLM                           │
│                                                     │
│  Step 2: LLM 批量分类（批次=20条，降低API成本）     │
│    ├── System Prompt: 分类体系 + 少样本示例         │
│    ├── User: 待分类交易列表(JSON)                   │
│    └── Output: 结构化分类结果(JSON)                 │
│                                                     │
│  Step 3: 置信度校验                                 │
│    ├── 置信度 < 0.7 → 归入「其他」                 │
│    └── 置信度 ≥ 0.7 → 存库，标记 source='llm'     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│               报告洞察 Agent Pipeline                │
│                                                     │
│  Input: 月度统计聚合数据 (JSON)                     │
│                                                     │
│  生成内容:                                          │
│  ├── 本月消费特征总结（1段）                        │
│  ├── 最显著变化分析（与上月对比）                   │
│  ├── 消费结构点评（如：餐饮占比偏高）               │
│  └── 个性化小建议（1-2条，非说教式）               │
└─────────────────────────────────────────────────────┘
```

---

### 2.5 关键 API 接口设计

```
POST   /api/bills/import          上传并解析账单文件（返回 import_id）
GET    /api/bills/import/{id}     查询导入状态（轮询）
GET    /api/transactions          获取交易列表（分页+筛选）
PATCH  /api/transactions/{id}     手动修改分类

GET    /api/reports/monthly?month=2025-03   获取月度报告
GET    /api/reports/summary                 获取整体统计概览
GET    /api/reports/ranking?type=merchant   商家排行榜

GET    /api/categories            获取分类体系
POST   /api/categories/rules      新建用户自定义规则
```

---

### 2.6 前端页面结构（Next.js App Router）

```
app/
├── (auth)/
│   └── login/
├── dashboard/                    # 首页看板
│   ├── page.tsx                  # 总览：净值卡片 + 快速导入入口
│   └── components/
│       ├── SummaryCards.tsx
│       └── RecentTransactions.tsx
├── import/                       # 导入页
│   └── page.tsx
├── reports/                      # 报告页
│   ├── [yearMonth]/
│   │   └── page.tsx              # 月度详情
│   └── components/
│       ├── CategoryPieChart.tsx
│       ├── WeeklyBarChart.tsx
│       ├── MerchantRanking.tsx
│       └── AiInsightCard.tsx     # AI洞察展示
└── transactions/                 # 交易明细
    └── page.tsx
```

---

### 2.7 项目目录结构（后端）

```
backend/
├── app/
│   ├── api/                      # FastAPI 路由层
│   ├── services/
│   │   ├── parsers/
│   │   │   ├── wechat.py
│   │   │   └── alipay.py
│   │   ├── classifier/
│   │   │   ├── rule_engine.py
│   │   │   └── llm_agent.py      # Claude API 调用
│   │   └── report_service.py
│   ├── models/                   # SQLAlchemy ORM
│   ├── schemas/                  # Pydantic 数据验证
│   └── tasks/                    # Celery 异步任务
│       ├── classify_task.py
│       └── report_task.py
├── alembic/                      # 数据库迁移
├── tests/
└── pyproject.toml
```

---

## 三、老板决策：MVP 开发优先级排序

| 阶段 | 任务 | 预估复杂度 |
|------|------|-----------|
| **Week 1-2** | 数据库建模 + 微信/支付宝解析器 + 导入API | 中 |
| **Week 3** | 规则引擎分类 + LLM 批量分类 Agent | 中高 |
| **Week 4** | 月度报告统计 + 报告洞察 Agent | 中 |
| **Week 5-6** | Next.js 前端：看板 + 导入 + 报告页 | 中高 |
| **Week 7** | 联调测试 + 分类准确率调优 | 中 |

---

## 四、老板总结与风险提示

**核心风险点：**

1. **LLM 分类成本控制** — 批量请求（每批20条）+ 规则引擎前置过滤，可降低 ~60% API 调用量
2. **账单格式变化** — 微信/支付宝会不定期调整 CSV 格式，解析器需版本化，加单元测试覆盖
3. **数据隐私** — 账单数据极度敏感，MVP 阶段需确认：文件上传后是否留存原始文件（建议解析完即删）
4. **分类冷启动** — 首批规则库质量直接影响用户体验，建议预置 100+ 条高频商家规则

**下一步行动：**
- 确认 LLM 供应商（建议用 Claude API，结构化输出稳定）
- 拍板是否需要用户登录系统（MVP 可先做单用户本地版本，快速验证价值）
- 准备 10 份真实账单样本用于分类准确率测试

---

如需进一步细化任何模块（比如 LLM Prompt 设计、前端组件交互细节、或 CI/CD 方案），告诉我即可继续深入。

用户
2026/3/29 21:35:55
在后端的技术架构上, 尽量引入分层概念, 使得功能可扩展, 这有一份亮点功能清单, 是后期需要进行逐步开发的, 你看一下, 然后再对你的技术架构和产品文档进行调整. 使用UltraThink模式
# AI Agent驱动的Beancount账本记账系统亮点功能菜单

## 概述

本系统结合了beancount的严谨复式记账架构与AI agent的智能化能力，为用户提供从账单导入到财务分析的全流程自动化解决方案。以下是精心设计的亮点功能菜单，供用户选择优先实现的功能。

---

## 功能分类与亮点功能列表

### 1. AI增强功能

#### 功能1：智能预算规划引擎
- **描述**：基于历史消费模式，AI自动推荐个性化的月度预算方案。系统会分析用户过去3-6个月的消费数据，考虑季节性因素（如节假日消费高峰），生成合理的预算分配建议。
- **实现难度**：中
- **预期价值**：★★★★★
- **技术要点**：
  - 时间序列分析算法
  - 消费模式识别
  - 预算优化模型
- **用户价值**：帮助用户建立科学的预算体系，避免超支

#### 功能2：异常消费实时检测
- **描述**：实时监控交易流，检测异常消费行为（如盗刷、冲动消费、异常大额交易）。基于用户历史消费模式和地理位置信息，建立正常消费基线。
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - 异常检测算法（孤立森林、LOF）
  - 实时流处理
  - 多维度风险评估
- **用户价值**：财务安全防护，及时发现可疑交易

#### 功能3：个性化财务建议助手
- **描述**：基于用户的消费习惯、收入水平和财务目标，提供个性化的省钱建议和优化方案。例如："您每月在咖啡上花费500元，建议改用自带杯可节省20%"
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - 消费行为分析
  - 个性化推荐算法
  - 自然语言生成
- **用户价值**：实际可行的省钱建议，提升财务管理效果

### 2. 自动化功能

#### 功能4：全自动对账系统
- **描述**：自动匹配银行流水和账本记录，识别差异并智能建议调整方案。支持微信、支付宝、各大银行账单的自动导入和匹配。
- **实现难度**：高
- **预期价值**：★★★★★
- **技术要点**：
  - 多源账单解析器
  - 模糊匹配算法
  - 差异自动调整
- **用户价值**：节省90%的对账时间，确保账实相符

#### 功能5：智能定期账单管理
- **描述**：自动识别和管理定期账单（如订阅服务、信用卡还款、房贷等），提供到期提醒和自动支付建议。可预测未来现金流影响。
- **实现难度**：低
- **预期价值**：★★★★☆
- **技术要点**：
  - 定期模式识别
  - 日历集成
  - 通知系统
- **用户价值**：避免逾期费用，优化现金流管理

#### 功能6：报税数据自动准备
- **描述**：根据税务要求，自动生成报税所需的数据摘要和分类统计。支持个人所得税、增值税等常见税种的申报准备。
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - 税务规则引擎
  - 数据分类汇总
  - 报表生成
- **用户价值**：简化报税流程，确保数据准确性

### 3. 协作与分享

#### 功能7：家庭账本共享与分摊
- **描述**：支持多家庭成员共同记账，自动计算分摊费用（如房租、水电费、家庭开支）。提供家庭财务总览和成员贡献度分析。
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - 多用户账户体系
  - 费用分摊算法
  - 权限管理系统
- **用户价值**：简化家庭财务管理，减少分摊纠纷

#### 功能8：财务顾问协作模式
- **描述**：允许用户授权财务顾问查看匿名化或脱敏的财务数据，获取专业建议。支持数据沙箱和咨询会话记录。
- **实现难度**：中
- **预期价值**：★★★☆☆
- **技术要点**：
  - 数据脱敏算法
  - 安全访问控制
  - 咨询会话管理
- **用户价值**：获取专业财务建议，保护隐私安全

### 4. 集成扩展

#### 功能9：全渠道账单自动导入
- **描述**：支持微信、支付宝、银行卡、现金、投资账户等全渠道账单的自动导入和解析。提供统一的交易视图。
- **实现难度**：高
- **预期价值**：★★★★★
- **技术要点**：
  - 多渠道适配器
  - OCR识别技术
  - 数据标准化
- **用户价值**：一站式管理所有财务账户，全面掌握财务状况

#### 功能10：第三方应用深度集成
- **描述**：与Notion、Google Sheets、微信机器人等第三方应用深度集成，支持数据同步、自动化工作流和跨平台协作。
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - API集成框架
  - 数据同步机制
  - 工作流引擎
- **用户价值**：融入现有工作流，提升使用便利性

### 5. 用户体验创新

#### 功能11：自然语言财务查询
- **描述**：用户可以用自然语言提问，如"我上个月在餐饮上花了多少钱？"、"这个月哪个类别超支最多？"，系统自动解析并返回结果。
- **实现难度**：中
- **预期价值**：★★★★★
- **技术要点**：
  - 自然语言理解
  - SQL查询生成
  - 对话式交互
- **用户价值**：降低使用门槛，提升查询效率

#### 功能12：语音记账助手
- **描述**：通过语音快速记录现金交易，支持多语言和方言识别。例如："今天现金买咖啡花了35元"
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - 语音识别（ASR）
  - 意图识别
  - 实时处理
- **用户价值**：简化现金记账，提升记录及时性

#### 功能13：交互式财务仪表盘
- **描述**：提供可定制的交互式财务仪表盘，支持拖拽式图表配置、实时数据刷新和深度下钻分析。
- **实现难度**：高
- **预期价值**：★★★★★
- **技术要点**：
  - 可视化引擎
  - 实时数据流
  - 交互式图表
- **用户价值**：直观掌握财务状况，支持深度分析

### 6. 高级分析

#### 功能14：消费行为深度分析
- **描述**：深度分析消费行为模式，识别如"每周咖啡花费"、"月度购物高峰"等规律，提供行为洞察和优化建议。
- **实现难度**：中
- **预期价值**：★★★★☆
- **技术要点**：
  - 行为模式挖掘
  - 聚类分析
  - 趋势预测
- **用户价值**：理解消费习惯，支持理性消费决策

#### 功能15：投资组合智能跟踪
- **描述**：集成股票、基金、加密货币等投资账户，自动计算收益率、风险评估和资产配置建议。
- **实现难度**：高
- **预期价值**：★★★★★
- **技术要点**：
  - 投资API集成
  - 投资组合分析
  - 风险评估模型
- **用户价值**：全面掌握投资状况，优化资产配置

#### 功能16：净资产自动计算与预测
- **描述**：自动计算个人/家庭净资产，基于历史趋势预测未来净资产变化，支持"财务自由"进度跟踪。
- **实现难度**：低
- **预期价值**：★★★★☆
- **技术要点**：
  - 净资产计算模型
  - 趋势预测算法
  - 目标跟踪
- **用户价值**：清晰掌握财富状况，激励财务目标达成

---

## 功能优先级推荐

### 第一优先级（MVP核心功能）
1. **全自动对账系统** - 解决核心痛点
2. **全渠道账单自动导入** - 基础数据来源
3. **自然语言财务查询** - 提升用户体验
4. **交互式财务仪表盘** - 核心价值展示

### 第二优先级（增强功能）
5. **智能预算规划引擎** - 核心AI价值
6. **异常消费实时检测** - 安全防护
7. **个性化财务建议助手** - 差异化优势
8. **消费行为深度分析** - 深度洞察

### 第三优先级（扩展功能）
9. **家庭账本共享与分摊** - 扩展用户群体
10. **投资组合智能跟踪** - 高级用户需求
11. **第三方应用深度集成** - 生态建设
12. **语音记账助手** - 创新体验

### 第四优先级（专业功能）
13. **报税数据自动准备** - 专业需求
14. **财务顾问协作模式** - B端扩展
15. **智能定期账单管理** - 便利性增强
16. **净资产自动计算与预测** - 长期跟踪

---

## 实施路线图建议

### 阶段一：基础自动化（1-3个月）
- 实现账单自动导入和基础分类
- 开发核心对账引擎
- 构建基础Web界面

### 阶段二：AI智能化（3-6个月）
- 集成AI分类和预算规划
- 开发自然语言查询
- 实现基础分析功能

### 阶段三：体验优化（6-9个月）
- 开发交互式仪表盘
- 实现多用户协作
- 优化移动端体验

### 阶段四：生态扩展（9-12个月）
- 第三方应用集成
- 投资账户支持
- 开放API平台

---

## 技术架构建议

### 核心组件
1. **账单解析引擎**：支持多格式账单解析
2. **AI分类服务**：基于大模型的智能分类
3. **对账匹配引擎**：智能匹配和差异处理
4. **数据分析引擎**：实时计算和预测
5. **用户交互层**：Web、移动、语音多端支持

### 技术栈推荐
- **后端**：Python + FastAPI + PostgreSQL
- **AI服务**：OpenAI/Claude API + 本地模型降级
- **前端**：React + TypeScript + ECharts
- **移动端**：React Native
- **基础设施**：Docker + Kubernetes + Redis

---

## 风险评估与缓解

### 技术风险
1. **AI分类准确率不足**
   - 缓解：多模型投票 + 人工审核 + 持续训练
   
2. **账单格式频繁变化**
   - 缓解：插件化架构 + 社区贡献 + 自动检测

3. **数据安全与隐私**
   - 缓解：端到端加密 + 本地处理选项 + 透明政策

### 业务风险
1. **用户接受度低**
   - 缓解：渐进式引导 + 免费增值模式 + 社区建设

2. **市场竞争激烈**
   - 缓解：专注beancount生态 + 开源策略 + 差异化功能

---

## 成功指标

### 技术指标
- 分类准确率 > 90%
- 对账匹配率 > 95%
- 系统响应时间 < 2秒
- 可用性 > 99.5%

### 业务指标
- 用户手动干预率 < 10%
- 月度活跃用户增长率 > 20%
- 用户满意度 > 4.5/5
- 功能使用率 > 70%

---

## 总结

本AI agent驱动的beancount账本记账系统通过16个亮点功能，全面覆盖了从基础记账到高级财务分析的各个层面。系统设计充分考虑了用户的实际需求和技术可行性，提供了清晰的优先级和实施路径。

**核心价值主张**：
1. **全自动化**：减少90%的手动记账工作
2. **智能化**：AI驱动的分类、预算和建议
3. **全面性**：支持全渠道账单和深度分析
4. **易用性**：自然语言交互和直观可视化

建议从第一优先级的4个核心功能开始实施，快速验证市场反应，然后逐步扩展其他功能，最终构建一个完整的智能财务管理生态系统。

AI
2026/3/29 21:38:24
收到，我来深度重构架构设计。这份功能菜单揭示了两个关键信号：**核心引擎是 Beancount 复式记账**，以及**系统需要插件化扩展能力**。

---

# 智能账单助手 · 架构与产品文档 V2

---

## 一、架构设计原则（老板定调）

面对 16 个亮点功能的扩展需求，架构必须满足：

| 原则 | 说明 |
|------|------|
| **分层隔离** | 各层只依赖下层接口，不依赖具体实现 |
| **适配器模式** | 解析器、LLM、存储均可替换 |
| **插件注册** | 新数据源/新 Agent 无需修改核心代码 |
| **事件驱动** | 通过领域事件解耦功能模块 |
| **Beancount 为核** | 所有分类账目最终生成 Beancount 分录，保证复式记账严谨性 |

---

## 二、完整分层架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                            │
│          Next.js Web  │  Mobile(未来)  │  Voice Interface(未来)      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST / WebSocket
┌──────────────────────────────▼──────────────────────────────────────┐
│                         API Gateway Layer                            │
│         FastAPI  │  JWT Auth  │  Rate Limit  │  WebSocket Hub        │
│         /api/v1/bills  /reports  /query  /budgets  /integrations     │
└─────────────┬────────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────────┐
│                      Application Services Layer                       │
│                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐ │
│  │  ImportService  │  │ ReportService   │  │  AgentOrchestrator   │ │
│  │  (账单导入流程)  │  │  (报告生成)     │  │  (AI Agent 调度)     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐ │
│  │ AnalysisService │  │ BudgetService   │  │ IntegrationService   │ │
│  │ (统计分析)       │  │ (预算规划)      │  │ (第三方集成)         │ │
│  └─────────────────┘  └─────────────────┘  └──────────────────────┘ │
│                                                                       │
│                    ← 通过 EventBus 互相解耦 →                         │
└─────────────┬────────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────────┐
│                          Domain Layer                                 │
│                                                                       │
│  ┌────────────────────────┐   ┌─────────────────────────────────┐   │
│  │   Transaction Domain   │   │      Beancount Engine           │   │
│  │  - RawTransaction      │   │  Transaction → Journal Entry    │   │
│  │  - Transaction         │   │  双向验证 + Balance Assertion    │   │
│  │  - DomainEvents        │   │  bql 查询接口                   │   │
│  └────────────────────────┘   └─────────────────────────────────┘   │
│                                                                       │
│  ┌────────────────────────┐   ┌─────────────────────────────────┐   │
│  │  Classification Domain │   │      Budget & Goal Domain       │   │
│  │  ClassificationPipeline│   │   BudgetPlan / SpendingGoal     │   │
│  │  (责任链模式)           │   │   财务目标追踪                  │   │
│  └────────────────────────┘   └─────────────────────────────────┘   │
│                                                                       │
│  ┌────────────────────────┐   ┌─────────────────────────────────┐   │
│  │   Analysis Domain      │   │     Collaboration Domain        │   │
│  │  AnomalyDetector       │   │   FamilyLedger / Sharing        │   │
│  │  BehaviorPatternMiner  │   │   (未来扩展)                    │   │
│  └────────────────────────┘   └─────────────────────────────────┘   │
└─────────────┬────────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────────┐
│                       Infrastructure Layer                            │
│                                                                       │
│  ┌────────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │   Parser Registry  │  │   LLM Adapter   │  │  Storage Adapter │  │
│  │ ┌────────────────┐ │  │ ┌─────────────┐ │  │ ┌──────────────┐ │  │
│  │ │ WeChatParser   │ │  │ │ ClaudeClient│ │  │ │  PostgreSQL  │ │  │
│  │ │ AlipayParser   │ │  │ │ OpenAIClient│ │  │ │  Repository  │ │  │
│  │ │ OCRParser(未来)│ │  │ │ LocalModel  │ │  │ └──────────────┘ │  │
│  │ │ BankParser(未来│ │  │ └─────────────┘ │  │ ┌──────────────┐ │  │
│  │ └────────────────┘ │  └─────────────────┘  │ │  Beancount   │ │  │
│  └────────────────────┘                        │ │  File Store  │ │  │
│                                                │ └──────────────┘ │  │
│  ┌────────────────────┐  ┌─────────────────┐  └──────────────────┘  │
│  │  Agent Registry    │  │  Task Queue     │                         │
│  │ ┌────────────────┐ │  │  Redis + Celery │  ┌──────────────────┐  │
│  │ │ClassifyAgent   │ │  │                 │  │ Integration Adpt │  │
│  │ │InsightAgent    │ │  │                 │  │ Notion/GSheets   │  │
│  │ │NLQueryAgent    │ │  │                 │  │ WeChatBot(未来)  │  │
│  │ │AnomalyAgent    │ │  │                 │  └──────────────────┘  │
│  │ │BudgetAgent(未来│ │  │                 │                         │
│  │ └────────────────┘ │  └─────────────────┘                         │
│  └────────────────────┘                                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心扩展机制设计

### 3.1 解析器注册表（Parser Registry）

新增数据源只需实现接口并注册，零修改核心代码：

```python
# infrastructure/parsers/base.py
class BillParserAdapter(ABC):
    @property
    @abstractmethod
    def source_type(self) -> str: ...        # 'wechat' | 'alipay' | 'bank_cmb'

    @abstractmethod
    def can_parse(self, content: str) -> bool: ...   # 自动识别格式

    @abstractmethod
    def parse(self, content: str) -> list[RawTransaction]: ...

# infrastructure/parsers/registry.py
class ParserRegistry:
    _parsers: dict[str, BillParserAdapter] = {}

    @classmethod
    def register(cls, parser: BillParserAdapter):
        cls._parsers[parser.source_type] = parser

    @classmethod
    def auto_detect(cls, content: str) -> BillParserAdapter:
        for parser in cls._parsers.values():
            if parser.can_parse(content):
                return parser
        raise UnsupportedFormatError()

# 注册新解析器（未来银行账单）
ParserRegistry.register(CMBBankParser())   # 招商银行
ParserRegistry.register(ICBCParser())      # 工商银行
```

---

### 3.2 分类管道（Classification Pipeline）— 责任链模式

```python
# domain/classification/pipeline.py
@dataclass
class ClassificationResult:
    category_l1: str
    category_l2: str | None
    confidence: float
    source: Literal['user_rule', 'system_rule', 'llm', 'fallback']

class ClassificationStage(ABC):
    @abstractmethod
    def classify(self, tx: RawTransaction) -> ClassificationResult | None:
        """返回 None 表示传递给下一级"""
        ...

class ClassificationPipeline:
    # 各阶段按优先级排列，前置命中则短路
    stages: list[ClassificationStage] = [
        UserDefinedRuleStage(),   # 用户自定义规则（最高优先级）
        SystemRuleStage(),        # 内置规则库（500+ 高频商家）
        LLMClassificationStage(), # Claude API 兜底
        FallbackStage(),          # 归入「其他」
    ]

    def run(self, tx: RawTransaction) -> ClassificationResult:
        for stage in self.stages:
            result = stage.classify(tx)
            if result is not None:
                return result
```

---

### 3.3 Beancount 引擎（核心账务层）

```python
# domain/beancount/engine.py
class BeancountEngine:
    """
    将分类后的交易转换为 Beancount 复式记账分录
    保证借贷平衡，支持 bql 查询
    """
    def generate_entry(self, tx: Transaction) -> BeancountEntry:
        """
        生成示例:
        2025-03-15 * "美团外卖" "晚餐 黄焖鸡米饭"
          Expenses:Food:Delivery    35.00 CNY
          Assets:WeChat             -35.00 CNY
        """
        debit_account  = self._resolve_expense_account(tx)  # Expenses:Food:Delivery
        credit_account = self._resolve_asset_account(tx)    # Assets:WeChat / Assets:Alipay

        return BeancountEntry(
            date=tx.transaction_at.date(),
            flag="*",
            payee=tx.merchant,
            narration=tx.description,
            postings=[
                Posting(account=debit_account,  amount=tx.amount),
                Posting(account=credit_account, amount=-tx.amount),
            ],
            meta={"source": tx.source, "tx_id": str(tx.id)}
        )

    def query(self, bql: str) -> QueryResult:
        """支持自然语言转 BQL（未来 NLQueryAgent 的底层接口）"""
        ...
```

---

### 3.4 Agent 注册表（Agent Registry）

每个 AI 功能是独立 Agent，可按需启用：

```python
# infrastructure/ai/agents/base.py
class AIAgent(ABC):
    agent_id: str
    description: str

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult: ...

# infrastructure/ai/registry.py
class AgentRegistry:
    _agents: dict[str, AIAgent] = {}

    @classmethod
    def register(cls, agent: AIAgent):
        cls._agents[agent.agent_id] = agent

# 已注册（MVP）
AgentRegistry.register(ClassificationAgent())   # 分类
AgentRegistry.register(InsightAgent())          # 月度洞察

# 待注册（后续迭代）
# AgentRegistry.register(NLQueryAgent())        # 自然语言查询
# AgentRegistry.register(AnomalyDetectorAgent())# 异常检测
# AgentRegistry.register(BudgetPlannerAgent())  # 预算规划
```

---

### 3.5 领域事件总线（EventBus）— 模块解耦

```python
# core/events.py
@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TransactionImported(DomainEvent):
    import_id: str
    user_id: str
    transaction_ids: list[str]

@dataclass
class TransactionClassified(DomainEvent):
    transaction_id: str
    category_l1: str
    category_l2: str | None

@dataclass
class MonthlyReportRequested(DomainEvent):
    user_id: str
    year_month: str   # '2025-03'

# 事件流示例：导入完成后的自动触发链
TransactionImported
  → ClassificationTask (Celery)
  → TransactionClassified (每条)
    → BeancountEntryGenerated
    → [未来] AnomalyDetectionTask
  → [未来] RecurringBillDetection
```

---

## 四、更新后的项目目录结构

```
backend/
├── app/
│   ├── api/                          # Presentation Layer
│   │   └── v1/
│   │       ├── bills.py              # 账单导入
│   │       ├── transactions.py       # 交易管理
│   │       ├── reports.py            # 报告
│   │       ├── categories.py         # 分类管理
│   │       ├── query.py              # NL查询（迭代2）
│   │       ├── budgets.py            # 预算（迭代2）
│   │       └── integrations.py       # 第三方集成（迭代3）
│   │
│   ├── application/                  # Application Services Layer
│   │   ├── import_service.py         # 导入编排
│   │   ├── classification_service.py # 分类编排
│   │   ├── report_service.py         # 报告生成
│   │   ├── analysis_service.py       # 统计分析
│   │   ├── budget_service.py         # 预算服务（迭代2）
│   │   └── integration_service.py    # 集成服务（迭代3）
│   │
│   ├── domain/                       # Domain Layer
│   │   ├── transaction/
│   │   │   ├── models.py             # 领域模型
│   │   │   ├── events.py             # 领域事件定义
│   │   │   └── repository.py         # 仓储接口（ABC）
│   │   ├── classification/
│   │   │   ├── pipeline.py           # 分类管道（责任链）
│   │   │   ├── rule_engine.py        # 规则引擎
│   │   │   └── category_tree.py      # 分类体系树
│   │   ├── beancount/
│   │   │   ├── engine.py             # 核心：生成 Beancount 分录
│   │   │   ├── account_resolver.py   # 账户映射逻辑
│   │   │   ├── validator.py          # 借贷平衡验证
│   │   │   └── exporter.py           # 导出 .beancount 文件
│   │   ├── analysis/
│   │   │   ├── aggregator.py         # 统计聚合
│   │   │   ├── anomaly_detector.py   # 异常检测（迭代2）
│   │   │   └── pattern_miner.py      # 行为模式挖掘（迭代2）
│   │   └── budget/                   # 预算领域（迭代2）
│   │       ├── models.py
│   │       └── planner.py
│   │
│   ├── infrastructure/               # Infrastructure Layer
│   │   ├── parsers/
│   │   │   ├── base.py               # BillParserAdapter ABC
│   │   │   ├── registry.py           # 解析器注册表
│   │   │   ├── wechat.py
│   │   │   ├── alipay.py
│   │   │   └── ocr.py                # OCR解析（迭代3）
│   │   ├── ai/
│   │   │   ├── base.py               # LLMAdapter ABC
│   │   │   ├── claude_client.py      # Claude API 实现
│   │   │   ├── openai_client.py      # 备用（迭代后）
│   │   │   └── agents/
│   │   │       ├── base.py           # AIAgent ABC
│   │   │       ├── registry.py       # Agent 注册表
│   │   │       ├── classification_agent.py
│   │   │       ├── insight_agent.py
│   │   │       ├── nl_query_agent.py     # 迭代2
│   │   │       ├── anomaly_agent.py      # 迭代2
│   │   │       └── budget_planner_agent.py # 迭代2
│   │   ├── persistence/
│   │   │   ├── models/               # SQLAlchemy ORM
│   │   │   └── repositories/         # 仓储实现
│   │   ├── queue/
│   │   │   ├── import_tasks.py
│   │   │   ├── classification_tasks.py
│   │   │   └── analysis_tasks.py
│   │   └── integrations/             # 迭代3
│   │       ├── notion_adapter.py
│   │       ├── gsheets_adapter.py
│   │       └── wechat_bot_adapter.py
│   │
│   └── core/                         # 横切关注点
│       ├── config.py
│       ├── event_bus.py              # 领域事件总线
│       ├── exceptions.py
│       └── logging.py
│
├── tests/
│   ├── unit/
│   │   ├── test_parsers/             # 解析器单测
│   │   ├── test_classification/      # 分类管道单测
│   │   └── test_beancount/           # Beancount 分录单测
│   └── integration/
│       ├── test_import_flow.py       # 完整导入流程
│       └── test_report_generation.py
└── pyproject.toml
```

---

## 五、更新后的数据模型

```sql
-- 新增：Beancount 分录表
CREATE TABLE beancount_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID REFERENCES transactions(id) UNIQUE,
    user_id         UUID REFERENCES users(id),
    entry_date      DATE NOT NULL,
    flag            CHAR(1) DEFAULT '*',
    payee           VARCHAR(255),
    narration       TEXT,
    postings        JSONB NOT NULL,   -- [{account, amount, currency}]
    raw_beancount   TEXT NOT NULL,    -- 原始 beancount 文本，可直接导出
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 新增：预算表（迭代2）
CREATE TABLE budget_plans (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    year_month  VARCHAR(7) NOT NULL,
    category_l1 VARCHAR(50) NOT NULL,
    amount      NUMERIC(12,2) NOT NULL,
    source      VARCHAR(20) DEFAULT 'ai',  -- 'ai' | 'manual'
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 新增：异常交易标记表（迭代2）
CREATE TABLE anomaly_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID REFERENCES transactions(id),
    anomaly_type    VARCHAR(50),   -- 'large_amount' | 'unusual_merchant' | 'duplicate'
    confidence      NUMERIC(4,3),
    detail          JSONB,
    is_confirmed    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 新增：自然语言查询日志（迭代2）
CREATE TABLE nl_query_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    nl_input    TEXT NOT NULL,
    bql_output  TEXT,              -- 生成的 Beancount Query Language
    sql_output  TEXT,              -- 或转为 SQL
    result_rows INTEGER,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 六、更新后的产品路线图（对齐功能菜单）

### Phase 1 — MVP 基础自动化（对应功能菜单第一优先级）

```
功能菜单 → MVP 对应
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
全渠道账单导入 [部分]   → 微信 + 支付宝解析器注册
全自动对账系统 [基础]   → 规则+LLM 分类 + Beancount 分录生成
交互式财务仪表盘 [基础] → 月度报告 + 消费分布图表
自然语言查询 [不做]     → 架构预留 NLQueryAgent 接口
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
交付物: 可跑通的完整导入→分类→Beancount→报告 链路
```

### Phase 2 — AI 智能化（对应功能菜单第二优先级）

```
功能菜单 → Phase 2 实现
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
智能预算规划引擎     → BudgetPlannerAgent + budget_plans 表
异常消费实时检测     → AnomalyDetectorAgent + 领域事件触发
个性化财务建议助手   → InsightAgent 升级（对话式）
消费行为深度分析     → PatternMiner + 聚类分析
自然语言财务查询     → NLQueryAgent (NL → BQL/SQL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Phase 3 — 体验与协作（对应功能菜单第三优先级）

```
家庭账本共享与分摊   → Collaboration Domain + 多用户体系
投资组合智能跟踪     → 新解析器(证券账单) + Investment Domain
第三方应用深度集成   → IntegrationRegistry (Notion/GSheets)
语音记账助手         → ASR → NL → BeancountEntry 管道
```

### Phase 4 — 专业与生态（对应功能菜单第四优先级）

```
报税数据自动准备     → 税务规则引擎 + Beancount 汇总导出
财务顾问协作模式     → 数据脱敏层 + 沙箱账本
净资产自动计算与预测 → 净资产 Domain + 时序预测模型
开放 API 平台        → API Key 管理 + 开发者文档
```

---

## 七、各亮点功能的架构扩展点

| 亮点功能 | 扩展位置 | 改动范围 |
|---------|---------|---------|
| 新增银行账单来源 | `ParserRegistry.register()` | 仅新增一个文件 |
| 新增 AI 功能 | `AgentRegistry.register()` | 仅新增 Agent 实现 |
| 切换 LLM 供应商 | `LLMAdapter` 实现替换 | 不影响业务层 |
| 异常检测上线 | 订阅 `TransactionClassified` 事件 | 零修改已有代码 |
| 家庭协作 | 新增 Collaboration Domain | 与现有 Transaction 隔离 |
| 第三方集成 | `IntegrationRegistry` + Adapter | 独立 infrastructure 模块 |

---

## 八、老板决策：关键架构取舍

1. **Beancount 作为账务核心**：不仅是文件格式，其复式验证机制从源头保证账目一致性，`beancount query` 也是未来自然语言查询的底层引擎
2. **事件驱动 > 直接调用**：TransactionImported 事件让「异常检测」「定期账单识别」等后续功能可以无侵入地接入
3. **MVP 不做用户登录**：先做单用户本地版本（`user_id` 字段预留），验证核心价值后再加认证体系
4. **解析器测试数据**：工程启动第一周需收集 3 个月真实账单样本（脱敏），作为持续集成的回归测试基准，防止格式变化造成线上事故


# AI Shopping Guide 开发推进计划

## Summary

项目放在 `D:/code/ai-shopping-guide`，采用“两级计划”推进：先按里程碑控制整体方向，再把每个里程碑拆成每日小目标，避免一次做太多导致项目不稳定。

项目内创建两个核心管理目录：

- `docs/`：存放需求、技术方案、设计规范、接口标准、执行步骤等文档。
- `devlogs/`：存放每日开发日志，记录当天完成事项、问题、风险和下一步待办。

每日开发日志采用“两者结合”方式：项目内提供日志模板和脚本，同时后续可配置 Codex 每日提醒，帮助自动沉淀当天进展。

## Project Structure

建议初始化目录结构如下：

```text
D:/code/ai-shopping-guide/
├── client/                  # Next.js + React 前端
├── server/                  # 后端 API、RAG、模型调用
├── data/                    # 商品数据、图片、向量库导入源
├── docs/                    # 项目文档
├── devlogs/                 # 每日开发日志
├── scripts/                 # 初始化、数据导入、日志生成等脚本
├── docker/                  # Docker / 部署相关配置
├── README.md
└── .env.example
```

`docs/` 文档：

```text
docs/
├── 01-requirements.md              # 项目需求说明
├── 10-ai-shopping-guide-dev-plan.md # 详细开发计划（本文档）
├── 11-execution-rules.md           # 执行规则
└── 12-backend-agent-design.md      # 后端 Agent 详细设计
```

`devlogs/` 采用日期命名：

```text
devlogs/
├── 2026-05-25.md
├── 2026-05-26.md
└── template.md
```

每日日志模板固定包含：

```md
# 开发日志 - YYYY-MM-DD

## 今日目标

## 已完成

## 遇到的问题

## 风险与决策

## 明日待办
```

## Development Milestones

### Milestone 1：项目骨架与文档体系

目标：先把项目结构、文档、日志机制搭好。

每日小目标：

- Day 1：创建 `D:/code/ai-shopping-guide` 项目目录，初始化 `docs/`、`devlogs/`、`client/`、`server/`、`data/`、`scripts/`。
- Day 1：写入需求文档、开发计划、日志模板。
- Day 2：确定技术架构、数据 schema、API 草案和 UI 设计规范。

验收标准：

- 项目目录清晰。
- `docs/` 包含需求说明、开发计划、执行规则、后端设计文档。
- `devlogs/` 能按日期记录每日进展。

### Milestone 2：UI 设计与前端原型

目标：先完成 Figma 设计方向，再实现低风险前端骨架。

每日小目标：

- Day 3：整理 Figma 页面结构，包括登录页、导购聊天页、商品卡片、购物车、订单确认页。
- Day 4：初始化 Next.js + React 前端项目。
- Day 5：实现静态页面骨架，不接真实接口，只用 mock 数据验证布局。

验收标准：

- 前端能本地启动。
- 能看到登录页、聊天页、商品卡片、购物车抽屉。
- UI 风格接近智能导购产品，而不是普通后台页面。

### Milestone 3：数据 schema 与数据导入

目标：基于提供的数据集，完成数据导入和校验。

每日小目标：

- Day 6：基于提供的 JSON 示例定义统一商品 schema。
- Day 7：导入数据集到项目 `data/` 目录，按类目组织（美妆护肤、数码电子、服饰运动、食品饮料）。
- Day 8：校验数据完整性（图片路径、SKU 结构、RAG 字段），编写 validate-products.js 脚本。
- Day 9：前端数据格式适配，确保所有页面使用新的商品数据结构。

验收标准：

- 4 个类目的商品 JSON 数据全部导入并可通过校验。
- 图片路径与商品 JSON 能正确关联。
- 每条商品数据满足 RAG 检索需要。
- 前端所有页面使用真实数据替代 mock 数据。

### Milestone 4a：后端骨架 + 数据服务 + 认证

目标：搭建后端基础设施，跑通所有 REST API。

每日小目标：

- Day 10：初始化 FastAPI 后端项目（骨架 + config + 数据模型 + SQLite + .env 配置），创建数据目录结构（`data/{类目}/data/`、`data/{类目}/images/`、`data/chroma/`）。数据模型以商品 JSON 为准（不含 tags/attributes/sales_count/stock_status）。图片路径统一为 `/data/{image_path}`，FastAPI 挂载 `StaticFiles(directory="data", path="/data")`。sessions 表包含 state 和 summary_text 列。
- Day 11：实现认证服务（简单登录 + JWT）+ 商品数据服务（加载 JSON + 列表/详情 API + 静态图片服务 `/data/` 路径）。
- Day 12：实现购物车服务（cart_add 工具 sku_id 非必填，自动选择默认 SKU）+ 订单服务 CRUD API + 会话管理 API（创建/查询/删除会话，含 state/summary_text 读写）+ 依赖注入（get_db, get_current_user）+ 统一错误处理（ErrorResponse + 7 种错误码）。

验收标准：

- `uvicorn server.main:app` 能启动，Swagger UI 可调用所有 REST API。
- 商品列表/详情返回真实 JSON 数据，图片可通过 `/data/{类目}/images/{文件名}` URL 访问。
- 购物车和订单 API 完整可用，需 JWT 认证。
- 会话 API 可创建/查询/删除会话，state 和 summary_text 字段可读写。
- 错误响应统一返回 `{code, message, details}` 格式。

### Milestone 4b：RAG Pipeline

目标：跑通最小可用 RAG 链路。

每日小目标：

- Day 13：封装智谱客户端（LLM chat/stream + Embedding + API 调用成本追踪），实现商品知识分块（marketing/faq/review_positive/review_negative 四类）。
- Day 14：接入 Chroma，完成向量导入 + 检索 + 结构化过滤（类目/品牌/价格区间/exclude_keywords 关键词排除）。
- Day 15：实现 RAG Service（检索 + 过滤 + 重排 + 结果组装，不含 tags 字段）+ seed_products.py 数据导入脚本，验证端到端检索。

验收标准：

- `rag_service.search("适合油皮的护肤品")` 返回正确商品。
- 结构化过滤（类目/品牌/价格区间/关键词排除）正常工作。
- `python -m server.scripts.seed_products` 可一键导入商品数据到 Chroma。

### Milestone 5：Agent 层 + Chat API

目标：实现完整 Agent 系统，跑通聊天→推荐→加购→下单闭环。

每日小目标：

- Day 16：实现 Agent 基类 + 工具注册表 + 核心循环 + Router Agent（意图识别 + 混合意图分发，输出 list[RouteResult]）+ Prompt 模板创建与调优（Router/Guide/Cart/Order 四个 .md）。
- Day 17：实现导购 Agent + search_products（含 exclude_keywords）/get_product_detail/compare_products 工具。
- Day 18：实现购物车 Agent（cart_add sku_id 非必填，自动选择默认 SKU /cart_remove/cart_update/cart_view）+ 订单 Agent（order_preview/order_create）。
- Day 19：实现 Agent 编排器（混合意图顺序执行 + 状态转换 + Fallback）+ SSE 流式返回（text_delta/product_cards/tool_result/done/error 事件）+ Chat API（含 image_url 参数支持图片找货）+ 错误处理（Router 失败 Fallback、LLM 调用重试、工具执行异常捕获）。
- Day 20：实现上下文管理（状态推断 + 状态持久化 + 滑动窗口 + 摘要压缩 SummaryService）+ 指代消解 + 输出校验（幻觉防控第 5 层，P1 必须）。

验收标准：

- 通过 API 发送聊天消息，收到 SSE 流式回复 + 商品卡片。
- 用户可以说"把第二个加入购物车"。
- 用户可以说"推荐一个面霜，然后把刚才那个耳机加入购物车"（混合意图）。
- 用户可以完成模拟下单并生成订单号。
- 检索无结果时不编造商品，返回澄清问题。
- Router 正确分发到对应 Agent，Fallback 机制可用。
- LLM 调用失败时自动重试 1 次，仍失败返回 error 事件。
- 工具执行异常时 Agent 收到错误信息并决定是否重试。
- 对话状态正确持久化，跨轮对话可利用状态信息。
- 消息超过 10 条时自动生成摘要并注入上下文。

### Milestone 6：前后端联调 + 多模态

目标：前端对接后端，加入多模态能力。

每日小目标：

- Day 21：前端对接后端 Chat API + SSE 事件处理 + 购物车/订单 REST API。
- Day 22：实现图片上传 + 智谱视觉理解（提取商品特征→RAG 检索）+ 图片找货流程。
- Day 23：实现语音输入支持（Web Speech API / 后端 ASR）+ TTS 播报。
- Day 24：前后端联调修复，确保完整闭环。

验收标准：

- 前端完整跑通"聊天→推荐→加购→下单"闭环。
- 上传商品图片后，智谱多模态模型提取特征并返回相似商品。
- 语音输入能进入正常 RAG 流程。

### Milestone 7：部署 + 答辩

目标：补齐交付能力和演示完整度。

每日小目标：

- Day 25：Docker 部署配置 + 云端部署。
- Day 26：演示脚本 + 测试用例。
- Day 27：答辩材料 + 最终修复。

验收标准：

- 本地可一键启动。
- 云端可部署演示。
- 有 3-5 分钟 Demo 演示路线。

## Daily Workflow

每天开发按这个节奏推进：

1. 开始前查看 `devlogs/` 最新日志，确认昨日待办。
2. 只选择 1-3 个今日目标。
3. 完成后更新当天日志。
4. 把新增决策同步到 `docs/` 对应文档。
5. 每个小阶段结束后做一次可运行验证。

推荐当天日志文件命名：

```text
devlogs/YYYY-MM-DD.md
```

推荐脚本：

```text
scripts/new-devlog.ps1
```

脚本职责：

- 检查当天日志是否存在。
- 不存在则从 `devlogs/template.md` 创建。
- 自动填入日期。
- 保留“今日目标、已完成、遇到的问题、风险与决策、明日待办”结构。

## Acceptance Criteria

- 项目始终保持可运行，不长期停留在半成品状态。
- 每个里程碑完成后都有可验证结果。
- 所有关键决策进入 `docs/`。
- 每天开发结束后都有 `devlogs/YYYY-MM-DD.md`。
- RAG 回复必须基于商品库，不编造商品、价格、库存、优惠或 SKU。
- 所有购物车/订单操作通过 Tool Calling 执行，不由 LLM 自由生成。
- 前端、后端、数据、文档、部署材料都能支撑最终 Demo 和答辩。

## Assumptions

- 项目目录使用 `D:/code/ai-shopping-guide`。
- 开发节奏采用“两级计划”：里程碑 + 每日小目标。
- 每日开发日志采用“项目内脚本 + Codex 每日提醒”结合方式。
- 首版先保证稳定闭环，再逐步增强多模态、购物车、下单和部署能力。

# 后端 Agent 详细设计：Router + 专项 Agent 多 Agent 架构

## 0. 技术选型

### 0.1 核心决策：手写 Agent 循环 + zhipuai SDK 直调

本项目采用**手写 Agent 循环 + 智谱原生 SDK**，不引入 LangGraph / LangChain 等框架。

| 层 | 选型 | 理由 |
|----|------|------|
| Agent 编排 | 手写 `while` 循环 + 状态转换表 | Agent 循环核心仅 50 行，不值得引入框架；零抽象泄漏，调试透明 |
| LLM 调用 | `zhipuai` SDK 原生 `chat.completions` | 原生支持 Function Calling + 流式，无格式转换摩擦 |
| Embedding | `zhipuai` SDK 原生 `embeddings` | 与 LLM 同一 SDK，统一管理 |
| 向量库 | `chromadb` 原生 API | 轻量本地持久化，无需中间层 |
| Web 框架 | `fastapi` + `sse-starlette` | 原生 async + SSE 支持 |
| 数据库 | `aiosqlite` | SQLite 异步驱动，零运维 |

### 0.2 为什么不用 LangGraph

评估过三个方案后选择手写，核心考量：

| 维度 | 手写 + zhipuai SDK | LangGraph + zhipuai 直调 | 全 LangGraph + langchain-zhipu |
|------|:---:|:---:|:---:|
| 消息格式转换 | 无 | 每个 Node 都要写 | 无（自动适配） |
| 流式输出 | async generator 自然顺畅 | 需绕开 LangGraph 单独处理 | `astream_events` 自动 |
| Tool Calling 循环 | while + for，50 行 | LangGraph 边 + 转换层 | LangGraph 边，自动 |
| 调试透明度 | 100% | 70%（转换层是黑盒） | 60%（LangChain 抽象是黑盒） |
| 依赖数 | 12 | ~45 | ~45 |
| 维护负担 | 低 | 中高（两套格式持续维护） | 中（等 langchain-zhipu 更新） |

**关键结论**：LangGraph + zhipuai 直调的混合方案是三者中性价比最低的——承担了 LangGraph 的依赖开销和格式转换摩擦，却没得到流式输出和 Tool Calling 自动化的核心好处。手写方案虽然多 100 行代码，但零摩擦、零黑盒、零依赖风险。

## 1. 架构总览

### 1.1 设计理念

采用 **Router + 专项 Agent** 架构，核心思想是"意图识别与执行分离"：

- **Router Agent**：轻量级意图分类器，只负责识别用户意图并分发给对应 Agent
- **专项 Agent**：每个 Agent 拥有独立的 System Prompt 和工具集，专注处理一类任务
- **工具层**：所有确定性操作（检索、购物车、订单）通过 Tool Calling 执行，LLM 不自由生成结果

这种架构的优势在于：

1. 每个 Agent 的 Prompt 更短更精准，幻觉控制更好
2. 购物车/订单等确定性操作与推荐等创造性操作完全解耦
3. 各 Agent 可独立测试和优化
4. 扩展新 Agent 不影响现有逻辑

### 1.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                         │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Auth     │  │ Product  │  │ Chat     │  │ Cart     │  Order    │
│  │ Router   │  │ Router   │  │ Router   │  │ Router   │  Router   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  ────────│
│       │              │             │              │                 │
│  ┌────┴─────┐  ┌─────┴────┐  ┌────┴─────────────┴──────┐         │
│  │ Auth     │  │ Product  │  │     Agent Orchestrator   │         │
│  │ Service  │  │ Service  │  │                          │         │
│  └──────────┘  └──────────┘  │  ┌──────────────────┐   │         │
│                               │  │  Router Agent    │   │         │
│                               │  │  意图识别 + 分发  │   │         │
│                               │  └───────┬──────────┘   │         │
│                               │          │              │         │
│                               │    ┌─────┼──────┐       │         │
│                               │    ▼     ▼      ▼       │         │
│                               │ ┌────┐┌────┐┌────┐     │         │
│                               │ │导购 ││购物车││订单 │     │         │
│                               │ │Agent││Agent││Agent│     │         │
│                               │ └─┬──┘└──┬─┘└──┬─┘     │         │
│                               │   │      │     │        │         │
│                               │   ▼      ▼     ▼        │         │
│                               │ ┌──────────────────┐    │         │
│                               │ │   Tool Registry  │    │         │
│                               │ └────────┬─────────┘    │         │
│                               └──────────┼──────────────┘         │
│                                          │                        │
│  ┌───────────────────────────────────────┼───────────────────┐    │
│  │              Service Layer            │                   │    │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┴───────┐ ┌──────┐│    │
│  │  │ Session  │ │ Cart     │ │ Order           │ │RAG   ││    │
│  │  │ Service  │ │ Service  │ │ Service         │ │Service││    │
│  │  └──────────┘ └──────────┘ └─────────────────┘ └──┬───┘│    │
│  └────────────────────────────────────────────────────┼────┘    │
│                                                       │         │
│  ┌────────────────────────────────────────────────────┼────┐    │
│  │              Data & Model Layer                    │    │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┴──┐ │    │
│  │  │ SQLite   │ │ Chroma   │ │ Product  │ │ 智谱模型   │ │    │
│  │  │ (会话/   │ │ 向量库   │ │ JSON数据 │ │ 网关      │ │    │
│  │  │  购物车/ │ │          │ │          │ │ LLM/Emb/  │ │    │
│  │  │  订单)   │ │          │ │          │ │ 多模态    │ │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘ │    │
│  └───────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 请求处理主流程

```
用户发送消息 (POST /api/chat/stream)
  │
  ▼
ChatRouter 接收请求
  │
  ├─ 验证 Token → 获取 user_id
  ├─ 加载/创建 Session
  ├─ 追加用户消息到 Session History
  │
  ▼
AgentOrchestrator.run(user_id, session_id, user_message, context)
  │
  ├─ 1. Router Agent 分类意图
  │     输入：用户消息 + 最近 N 轮对话 + 当前购物车摘要
  │     输出：routes[]（支持混合意图，多个 intent + 提取的参数）
  │
  ├─ 2. 按顺序选择目标 Agent
  │     routes[0].intent → guide_agent / cart_agent / order_agent
  │     routes[1].intent → ...（混合意图时顺序执行）
  │
  ├─ 3. 目标 Agent 执行（每个 route 依次执行）
  │     构建 Prompt (system + history + context)
  │     调用 LLM (带 Tool Definitions)
  │     LLM 返回 → 文本流 / Tool Call
  │     Tool Call → 执行工具 → 结果注入 → 继续生成
  │
  ├─ 4. SSE 事件流输出
  │     text_delta / product_cards / tool_result / done / error
  │
  └─ 5. 更新 Session History + 对话状态 + 摘要压缩
```

---

## 2. 目录结构

```text
server/
├── main.py                          # FastAPI 应用入口
├── config.py                        # 配置管理（环境变量、常量）
├── requirements.txt                 # Python 依赖
│
├── api/                             # API 路由层
│   ├── __init__.py
│   ├── deps.py                      # 依赖注入（get_db, get_current_user 等）
│   ├── auth.py                      # POST /api/auth/login
│   ├── products.py                  # GET /api/products, GET /api/products/{id}
│   ├── chat.py                      # POST /api/chat/stream, POST/GET /api/chat/sessions
│   ├── cart.py                      # GET/PATCH/POST/DELETE /api/cart/**
│   └── orders.py                    # POST /api/orders/preview, POST /api/orders
│
├── agents/                          # Agent 层
│   ├── __init__.py
│   ├── orchestrator.py              # Agent 编排器（Router 分发 + Agent 调用）
│   ├── router_agent.py              # 意图识别 Agent
│   ├── guide_agent.py               # 导购推荐 Agent
│   ├── cart_agent.py                # 购物车 Agent
│   ├── order_agent.py               # 订单 Agent
│   └── base.py                      # Agent 基类
│
├── tools/                           # 工具层（Function Calling 工具定义与实现）
│   ├── __init__.py
│   ├── registry.py                  # 工具注册表
│   ├── search_products.py           # 商品检索工具（RAG）
│   ├── get_product_detail.py        # 商品详情工具
│   ├── compare_products.py          # 商品对比工具
│   ├── cart_add.py                  # 加入购物车
│   ├── cart_remove.py               # 移除购物车项
│   ├── cart_update_quantity.py      # 修改购物车数量
│   ├── cart_view.py                 # 查看购物车
│   ├── order_preview.py             # 订单预览
│   └── order_create.py              # 创建订单
│
├── services/                        # 业务服务层
│   ├── __init__.py
│   ├── auth_service.py              # 认证服务
│   ├── session_service.py           # 会话管理服务
│   ├── product_service.py           # 商品数据服务
│   ├── cart_service.py              # 购物车服务
│   ├── order_service.py             # 订单服务
│   └── rag_service.py               # RAG 检索服务（向量检索 + 结构化过滤 + 重排）
│
├── models/                          # 数据模型层
│   ├── __init__.py
│   ├── product.py                   # 商品 Pydantic 模型
│   ├── session.py                   # 会话模型
│   ├── cart.py                      # 购物车模型
│   ├── order.py                     # 订单模型
│   ├── user.py                      # 用户模型
│   └── chat.py                      # 聊天消息/事件模型
│
├── db/                              # 数据库层
│   ├── __init__.py
│   ├── database.py                  # SQLite 连接管理
│   └── migrations/                  # 数据库迁移脚本
│       └── init.sql
│
├── llm/                             # LLM 调用层
│   ├── __init__.py
│   ├── zhipu_client.py              # 智谱 API 客户端（LLM、Embedding、多模态）
│   └── prompts/                     # Prompt 模板
│       ├── router_system.md         # Router Agent System Prompt
│       ├── guide_system.md          # 导购 Agent System Prompt
│       ├── cart_system.md           # 购物车 Agent System Prompt
│       └── order_system.md          # 订单 Agent System Prompt
│
├── rag/                             # RAG 组件层
│   ├── __init__.py
│   ├── chunker.py                   # 商品知识分块
│   ├── embedder.py                  # 向量化（调用智谱 Embedding）
│   ├── vector_store.py              # Chroma 向量库操作
│   ├── retriever.py                 # 检索器（向量检索 + 结构化过滤）
│   └── reranker.py                  # 重排器
│
└── scripts/                         # 脚本
    ├── seed_products.py             # 导入商品数据到 JSON + Chroma
    └── reset_db.py                  # 重置数据库
```

---

## 3. Agent 基类与核心循环

### 3.1 Agent 基类设计

所有 Agent 继承自 `BaseAgent`，核心是 `run()` 方法中的 **while 循环**——这是整个系统最关键的 50 行代码：

```python
class BaseAgent(ABC):
    def __init__(
        self,
        llm_client: ZhipuClient,
        tool_registry: ToolRegistry,
        system_prompt: str,
        tool_schemas: list[dict],
        model: str = "glm-4-plus",
        temperature: float = 0.7,
        max_tool_rounds: int = 5,
    ):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.tool_schemas = tool_schemas
        self.model = model
        self.temperature = temperature
        self.max_tool_rounds = max_tool_rounds

    @abstractmethod
    def build_messages(self, user_message: str, context: ConversationContext) -> list[dict]:
        pass

    async def run(
        self,
        user_message: str,
        context: ConversationContext,
    ) -> AsyncGenerator[SSEEvent, None]:
        messages = self.build_messages(user_message, context)

        for _ in range(self.max_tool_rounds):
            text_buffer = ""
            tool_calls_buffer = []

            async for chunk in self.llm_client.chat_stream(
                messages=messages,
                tools=self.tool_schemas,
                model=self.model,
                temperature=self.temperature,
            ):
                if chunk.delta and chunk.delta.content:
                    text_buffer += chunk.delta.content
                    yield SSEEvent(type="text_delta", data={"content": chunk.delta.content})

                if chunk.delta and chunk.delta.tool_calls:
                    tool_calls_buffer.extend(chunk.delta.tool_calls)

            if not tool_calls_buffer:
                break

            messages.append({
                "role": "assistant",
                "content": text_buffer or None,
                "tool_calls": [tc.model_dump() for tc in tool_calls_buffer],
            })

            for tool_call in tool_calls_buffer:
                tool_result = await self.tool_registry.execute(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                    context=context,
                )

                yield SSEEvent(type="tool_result", data={
                    "tool": tool_call.function.name,
                    "result": tool_result,
                })

                if tool_call.function.name == "search_products" and tool_result.get("products"):
                    yield SSEEvent(type="product_cards", data={"products": tool_result["products"]})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

        yield SSEEvent(type="done", data={})
```

### 3.2 核心循环解读

```
while 没有超出最大工具调用轮次:
    调用智谱 LLM (流式)
    │
    ├─ 收到文本 chunk → yield text_delta 事件
    ├─ 收到 tool_calls → 收集到缓冲区
    │
    if 没有 tool_calls:
        break  ← LLM 生成完毕，退出循环
    │
    for 每个 tool_call:
        执行工具 → yield tool_result 事件
        if 是 search_products → yield product_cards 事件
        将工具结果追加到 messages
    │
    继续循环 ← LLM 基于工具结果继续生成
```

关键设计点：
- **`max_tool_rounds=5`**：防止 LLM 陷入无限工具调用循环
- **流式优先**：文本增量实时 yield，不等整个响应完成
- **工具结果即时推送**：每个工具执行完就发 SSE 事件，前端可以实时展示
- **商品卡片特殊处理**：`search_products` 结果额外发 `product_cards` 事件

### 3.3 状态转换表

编排器通过状态转换表控制 Agent 间的流转，借鉴了 LangGraph 的状态机思想但手写实现：

```python
TRANSITIONS = {
    "router": {
        "guide": "guide_agent",
        "cart": "cart_agent",
        "order": "order_agent",
    },
    "guide_agent": {
        "tools": "guide_agent",
        "end": None,
    },
    "cart_agent": {
        "tools": "cart_agent",
        "end": None,
    },
    "order_agent": {
        "tools": "order_agent",
        "end": None,
    },
}
```

等价的状态机图（答辩时可直接展示）：

```
         ┌─────────────────────────────────────┐
         │              router                  │
         └──────┬──────────┬──────────┬────────┘
                │          │          │
         guide  │   cart   │  order   │
                ▼          ▼          ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
      ┌─►│  guide   │ │   cart   │ │  order   │
      │  │  agent   │ │  agent   │ │  agent   │
      │  └────┬─────┘ └────┬─────┘ └────┬─────┘
      │       │            │            │
      │  tools│       tools│       tools│
      │       │            │            │
      │  ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐
      │  │  tools   │ │  tools   │ │  tools   │
      │  │executor  │ │executor  │ │executor  │
      │  └────┬─────┘ └────┬─────┘ └────┬─────┘
      │       │            │            │
      └───────┘            │            │
                (end)      (end)       (end)
```

混合意图时，编排器按 Router 输出的 routes 顺序依次执行多个 Agent，每个 Agent 独立完成自己的工具循环。Agent 之间通过 `\n\n---\n\n` 分隔符在 SSE 流中分隔。

---

## 4. Router Agent 设计

### 4.1 职责

Router Agent 是整个系统的入口调度器，只做一件事：**分析用户消息，识别意图，输出结构化路由结果**。

它不做任何业务执行，不调用任何工具，只做分类。

### 4.2 意图定义

```python
class IntentType(str, Enum):
    PRODUCT_RECOMMEND = "product_recommend"       # 推荐商品（"推荐面霜"、"有什么好用的耳机"）
    PRODUCT_FILTER = "product_filter"             # 条件筛选（"500以内的耳机"、"不要含酒精的"）
    PRODUCT_COMPARE = "product_compare"           # 商品对比（"A和B哪个好"）
    PRODUCT_DETAIL = "product_detail"             # 查看详情（"这个商品详情"、"更多评价"）
    CART_ADD = "cart_add"                         # 加入购物车（"加入购物车"、"买这个"）
    CART_REMOVE = "cart_remove"                   # 移除购物车（"删掉那个"、"不要了"）
    CART_UPDATE = "cart_update"                   # 修改数量（"数量改成2"、"再加一个"）
    CART_VIEW = "cart_view"                       # 查看购物车（"看看购物车"、"我买了什么"）
    ORDER_PREVIEW = "order_preview"               # 订单预览（"结算"、"看看总价"）
    ORDER_CREATE = "order_create"                 # 创建订单（"下单"、"确认购买"）
    GENERAL_CHAT = "general_chat"                 # 闲聊/追问/模糊意图
```

### 4.3 Agent 到意图的映射

```python
INTENT_AGENT_MAP = {
    IntentType.PRODUCT_RECOMMEND: "guide_agent",
    IntentType.PRODUCT_FILTER:    "guide_agent",
    IntentType.PRODUCT_COMPARE:   "guide_agent",
    IntentType.PRODUCT_DETAIL:    "guide_agent",
    IntentType.CART_ADD:          "cart_agent",
    IntentType.CART_REMOVE:       "cart_agent",
    IntentType.CART_UPDATE:       "cart_agent",
    IntentType.CART_VIEW:         "cart_agent",
    IntentType.ORDER_PREVIEW:     "order_agent",
    IntentType.ORDER_CREATE:      "order_agent",
    IntentType.GENERAL_CHAT:      "guide_agent",
}
```

### 4.4 Router 输出格式

Router Agent 使用 Function Calling 返回结构化路由结果。支持**混合意图**：当用户一条消息包含多个意图时（如"推荐一个面霜，然后把刚才那个耳机加入购物车"），Router 输出多个路由结果，编排器按顺序依次执行。

```json
{
  "name": "route_intent",
  "parameters": {
    "routes": [
      {
        "intent": "product_recommend",
        "target_agent": "guide_agent",
        "extracted_params": {
          "query": "面霜",
          "category": null,
          "price_max": null,
          "exclude_keywords": []
        },
        "confidence": 0.95
      },
      {
        "intent": "cart_add",
        "target_agent": "cart_agent",
        "extracted_params": {
          "product_id": "p_digital_003",
          "sku_id": null,
          "quantity": 1
        },
        "confidence": 0.88
      }
    ],
    "is_multi_intent": true
  }
}
```

单意图时 `routes` 只包含一个元素，`is_multi_intent` 为 `false`：

```json
{
  "name": "route_intent",
  "parameters": {
    "routes": [
      {
        "intent": "product_recommend",
        "target_agent": "guide_agent",
        "extracted_params": {
          "query": "适合油皮的护肤品",
          "category": "美妆护肤",
          "price_max": null,
          "exclude_keywords": []
        },
        "confidence": 0.95
      }
    ],
    "is_multi_intent": false
  }
}
```

#### RouteResult 数据模型

```python
class RouteResult(BaseModel):
    intent: IntentType
    target_agent: str
    extracted_params: dict
    confidence: float

class RouteOutput(BaseModel):
    routes: list[RouteResult]
    is_multi_intent: bool = False
```

### 4.5 Router System Prompt

```markdown
你是一个意图识别路由器。你的任务是分析用户消息，识别用户意图，并输出结构化路由结果。

## 可选意图

| 意图 | 说明 | 目标 Agent |
|------|------|-----------|
| product_recommend | 用户想找商品推荐 | guide_agent |
| product_filter | 用户有明确筛选条件 | guide_agent |
| product_compare | 用户想对比多个商品 | guide_agent |
| product_detail | 用户想了解商品详情 | guide_agent |
| cart_add | 用户想加入购物车 | cart_agent |
| cart_remove | 用户想移除购物车商品 | cart_agent |
| cart_update | 用户想修改购物车数量 | cart_agent |
| cart_view | 用户想查看购物车 | cart_agent |
| order_preview | 用户想看订单预览 | order_agent |
| order_create | 用户想确认下单 | order_agent |
| general_chat | 闲聊、追问或模糊意图 | guide_agent |

## 判断规则

1. 如果用户提到"推荐"、"有什么"、"想买"、"找"等词，且不涉及购物车操作 → product_recommend
2. 如果用户提到价格范围、品牌、类目等筛选条件 → product_filter
3. 如果用户提到"A和B"、"哪个好"、"对比" → product_compare
4. 如果用户提到"详情"、"更多"、"评价" → product_detail
5. 如果用户提到"加入购物车"、"买这个"、"要这个" → cart_add
6. 如果用户提到"删掉"、"不要了"、"移除" → cart_remove
7. 如果用户提到"数量"、"改成"、"再加" → cart_update
8. 如果用户提到"购物车"、"买了什么" → cart_view
9. 如果用户提到"结算"、"总价"、"结账" → order_preview
10. 如果用户提到"下单"、"确认购买"、"付款" → order_create
11. 其他情况 → general_chat

## 混合意图处理

当用户一条消息中包含多个不同意图时（例如"推荐一个面霜，然后把刚才那个耳机加入购物车"），需要在 routes 数组中输出多个路由结果，按用户提到的顺序排列。

判断是否为混合意图：
- 用户消息中同时包含推荐类意图和购物车/订单操作意图 → 混合意图
- 用户消息中同时包含购物车操作和下单意图 → 混合意图
- 同一类别的多个操作（如"把第一个和第二个都加入购物车"）→ 单意图 cart_add，不是混合意图
- 推荐类意图的细化追问（如"推荐面霜，不要含酒精的"）→ 单意图 product_filter，不是混合意图

## 注意

- 只输出路由结果，不要回答用户问题
- 提取用户消息中的关键参数（类目、品牌、价格、排除条件等）
- 如果意图模糊，优先归为 general_chat
- 置信度低于 0.6 时归为 general_chat
- 混合意图时，每个意图的 confidence 独立评估
```

### 4.6 Router 调用方式

Router 使用**单次 LLM 调用 + Function Calling**，不走多轮循环：

```python
async def route(self, user_message: str, context: ConversationContext) -> RouteOutput:
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": f"当前购物车摘要：{context.cart_summary}\n最近对话：{context.recent_history}\n用户消息：{user_message}"},
    ]

    response = await self.llm_client.chat(
        messages=messages,
        tools=[ROUTE_INTENT_TOOL_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "route_intent"}},
        temperature=0.1,
    )

    route_args = response.tool_calls[0].function.arguments
    return RouteOutput(**route_args)
```

关键设计决策：
- `temperature=0.1`：Router 需要确定性输出，不鼓励创造性
- `tool_choice` 强制调用 `route_intent`：确保输出格式一致
- 不走多轮：Router 只做一次调用，快速返回

---

## 5. 导购 Agent 设计

### 5.1 职责

导购 Agent 是系统的核心 Agent，负责所有与商品推荐相关的交互：

- 商品推荐（基于 RAG 检索）
- 条件筛选（价格/类目/品牌/排除条件）
- 商品对比
- 商品详情解读
- 多轮追问与上下文延续
- 闲聊与引导

### 5.2 可用工具

| 工具名 | 功能 | 触发条件 |
|--------|------|----------|
| `search_products` | 语义+结构化检索商品 | 用户需要推荐/筛选商品 |
| `get_product_detail` | 获取商品详情/SKU/评价 | 用户想了解某个商品详情 |
| `compare_products` | 多商品结构化对比 | 用户想对比商品 |

### 5.3 工具 Schema 定义

#### search_products

```json
{
  "name": "search_products",
  "description": "从商品知识库中检索商品。支持语义搜索和结构化过滤。当用户需要推荐、筛选或查找商品时使用此工具。",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "用户的语义查询，如'适合油皮的护肤品'、'降噪耳机'"
      },
      "category": {
        "type": "string",
        "enum": ["美妆护肤", "数码电子", "服饰运动", "食品饮料"],
        "description": "商品类目过滤，如果用户明确提到类目则填写"
      },
      "brand": {
        "type": "string",
        "description": "品牌过滤"
      },
      "price_min": {
        "type": "number",
        "description": "最低价格"
      },
      "price_max": {
        "type": "number",
        "description": "最高价格"
      },
      "exclude_keywords": {
        "type": "array",
        "items": {"type": "string"},
        "description": "需要排除的关键词，如['含酒精','孕妇慎用','敏感肌']。匹配商品标题、品牌、类目中的关键词"
      },
      "top_k": {
        "type": "integer",
        "default": 5,
        "description": "返回商品数量"
      }
    },
    "required": ["query"]
  }
}
```

#### get_product_detail

```json
{
  "name": "get_product_detail",
  "description": "获取指定商品的详细信息，包括SKU、价格、评价、FAQ等。当用户想了解某个商品详情时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "product_id": {
        "type": "string",
        "description": "商品ID"
      }
    },
    "required": ["product_id"]
  }
}
```

#### compare_products

```json
{
  "name": "compare_products",
  "description": "对比多个商品的详细信息，返回结构化对比数据。当用户想对比两个或多个商品时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "product_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "要对比的商品ID列表",
        "minItems": 2,
        "maxItems": 4
      },
      "dimensions": {
        "type": "array",
        "items": {"type": "string"},
        "description": "对比维度，如['价格','适用肤质','功效']。不填则对比所有维度。"
      }
    },
    "required": ["product_ids"]
  }
}
```

### 5.4 导购 Agent System Prompt

```markdown
你是「AI Shopping Guide」的智能导购助手。你的职责是帮助用户找到最合适的商品。

## 核心原则

1. **只推荐知识库中存在的商品**：你必须通过 search_products 工具检索商品，绝不能编造商品。
2. **价格和SKU必须来自工具返回的结构化数据**：不得编造、修改或推测价格、库存、优惠和SKU信息。
3. **检索无结果时诚实告知**：如果检索不到合适的商品，告诉用户并建议补充或修改条件。
4. **主动引导**：当用户需求模糊时，主动追问以细化需求。

## 工具使用规则

- 用户需要推荐商品 → 调用 search_products
- 用户需要筛选商品 → 调用 search_products（带过滤参数）
- 用户想了解商品详情 → 调用 get_product_detail
- 用户想对比商品 → 调用 compare_products
- 用户想加入购物车 → 提示用户点击商品卡片上的"加入购物车"按钮，或告诉用户你将为其添加
- 不要在未调用工具的情况下回答关于具体商品的问题

## 回复风格

- 友好、专业、简洁
- 推荐商品时给出理由，结合用户需求说明为什么适合
- 可以适当使用emoji增加亲和力
- 回复中引用商品时，必须使用工具返回的准确信息

## 幻觉防控

- 绝不编造不存在的商品
- 绝不编造价格、优惠、库存、SKU
- 绝不编造用户评价或FAQ内容
- 如果不确定某个信息，明确告知用户"我暂时无法确认这个信息"
- 商品卡片数据只来自工具返回的结构化结果
```

### 5.5 导购 Agent 执行流程

```python
async def run(self, user_message: str, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
    messages = self._build_messages(user_message, context)

    while True:
        response = await self.llm_client.chat(
            messages=messages,
            tools=self.tool_schemas,
            stream=True,
        )

        tool_calls_collected = []
        text_buffer = ""

        async for chunk in response:
            if chunk.delta.content:
                text_buffer += chunk.delta.content
                yield SSEEvent(type="text_delta", data={"content": chunk.delta.content})

            if chunk.delta.tool_calls:
                tool_calls_collected.append(chunk.delta.tool_calls)

        if not tool_calls_collected:
            break

        for tool_call in tool_calls_collected:
            tool_result = await self.tool_registry.execute(
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                context=context,
            )

            yield SSEEvent(type="tool_result", data={
                "tool": tool_call.function.name,
                "result": tool_result,
            })

            if tool_call.function.name == "search_products" and tool_result.get("products"):
                yield SSEEvent(type="product_cards", data={"products": tool_result["products"]})

            messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(tool_result)})

    yield SSEEvent(type="done", data={})
```

---

## 6. 购物车 Agent 设计

### 6.1 职责

购物车 Agent 专门处理所有购物车相关操作，核心特点是**纯确定性操作**——不涉及任何创造性生成，所有操作通过工具精确执行。

### 6.2 可用工具

| 工具名 | 功能 |
|--------|------|
| `cart_add` | 加入购物车（指定商品ID和SKU） |
| `cart_remove` | 移除购物车项 |
| `cart_update_quantity` | 修改购物车商品数量 |
| `cart_view` | 查看当前购物车内容 |

### 6.3 工具 Schema 定义

#### cart_add

```json
{
  "name": "cart_add",
  "description": "将指定商品的某个SKU加入购物车。当用户说'加入购物车'、'买这个'、'要这个'时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "product_id": {
        "type": "string",
        "description": "商品ID"
      },
      "sku_id": {
        "type": "string",
        "description": "SKU ID。如果用户未指定规格，留空即可，系统将自动选择默认第一个SKU。"
      },
      "quantity": {
        "type": "integer",
        "default": 1,
        "description": "数量"
      }
    },
    "required": ["product_id"]
  }
}
```

#### cart_remove

```json
{
  "name": "cart_remove",
  "description": "从购物车中移除指定商品。当用户说'删掉'、'不要了'、'移除'时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "item_id": {
        "type": "string",
        "description": "购物车项ID"
      }
    },
    "required": ["item_id"]
  }
}
```

#### cart_update_quantity

```json
{
  "name": "cart_update_quantity",
  "description": "修改购物车中某个商品的数量。当用户说'数量改成X'、'再加一个'、'少买一个'时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "item_id": {
        "type": "string",
        "description": "购物车项ID"
      },
      "quantity": {
        "type": "integer",
        "description": "新的数量（不是增量，是最终数量）"
      }
    },
    "required": ["item_id", "quantity"]
  }
}
```

#### cart_view

```json
{
  "name": "cart_view",
  "description": "查看当前购物车内容。当用户说'看看购物车'、'我买了什么'时使用。",
  "parameters": {
    "type": "object",
    "properties": {}
  }
}
```

### 6.4 购物车 Agent System Prompt

```markdown
你是「AI Shopping Guide」的购物车管理助手。你的职责是准确执行用户的购物车操作。

## 核心原则

1. **所有购物车操作必须通过工具执行**：绝不模拟、编造或猜测操作结果。
2. **精确匹配商品**：当用户说"把第二个加入购物车"时，根据对话上下文中最近展示的商品列表确定具体商品。
3. **操作后确认**：每次操作后告知用户操作结果（成功/失败）。
4. **不编造购物车内容**：如果不确定购物车状态，调用 cart_view 查看后再回答。

## 商品引用解析规则

当用户使用指代词时，按以下规则解析：
- "第一个/第二个/第三个" → 对话中最近出现的商品卡片列表中的对应位置
- "刚才那个" → 对话中最近提到的商品
- 商品名/品牌名 → 按名称匹配

## 回复风格

- 简洁确认操作结果
- 如有异常（商品不存在、库存不足等）明确告知
- 适当提示下一步操作（如"还需要其他商品吗？"）
```

### 6.5 指代消解机制

用户说"把第二个加入购物车"时，需要从对话上下文中解析"第二个"指代哪个商品。这是购物车 Agent 的关键难点。

```python
class ReferenceResolver:
    """解析用户消息中的指代词，映射到具体商品ID"""

    def resolve(self, user_message: str, context: ConversationContext) -> dict:
        recent_products = context.recent_product_cards  # 最近一次展示的商品卡片列表

        if not recent_products:
            return {"resolved": False, "reason": "对话中没有展示过商品"}

        patterns = {
            r"第([一二三四五六七八九十\d]+)个": self._resolve_ordinal,
            r"刚才那个|上面那个|这个": self._resolve_recent,
            r"全部|所有|都": self._resolve_all,
        }

        for pattern, resolver in patterns.items():
            match = re.search(pattern, user_message)
            if match:
                return resolver(match, recent_products)

        return {"resolved": False, "reason": "无法识别指代"}
```

指代消解结果会注入到 LLM 的上下文中，帮助 LLM 正确调用 `cart_add` 等工具。

---

## 7. 订单 Agent 设计

### 7.1 职责

订单 Agent 负责订单预览和模拟下单流程，核心是**流程化引导**——收集必要信息（地址确认）、展示订单汇总、生成模拟订单。

### 7.2 可用工具

| 工具名 | 功能 |
|--------|------|
| `order_preview` | 生成订单预览（商品汇总 + 金额计算） |
| `order_create` | 创建模拟订单（生成订单号） |
| `cart_view` | 查看购物车（确认商品信息） |

### 7.3 工具 Schema 定义

#### order_preview

```json
{
  "name": "order_preview",
  "description": "生成订单预览信息，包含商品汇总、金额计算。当用户说'结算'、'看看总价'时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "address": {
        "type": "string",
        "description": "收货地址。如果用户未提供，提示用户提供。"
      }
    },
    "required": []
  }
}
```

#### order_create

```json
{
  "name": "order_create",
  "description": "确认下单，创建模拟订单。当用户确认购买时使用。下单前必须先调用 order_preview。",
  "parameters": {
    "type": "object",
    "properties": {
      "address": {
        "type": "string",
        "description": "收货地址"
      }
    },
    "required": ["address"]
  }
}
```

### 7.4 订单 Agent System Prompt

```markdown
你是「AI Shopping Guide」的订单管理助手。你的职责是引导用户完成下单流程。

## 核心原则

1. **下单前必须预览**：用户确认下单前，必须先调用 order_preview 展示订单汇总。
2. **必须收集地址**：创建订单需要收货地址，如果用户未提供，主动询问。
3. **模拟订单**：这是模拟下单，不涉及真实支付和物流。订单号由系统自动生成。
4. **金额计算由工具完成**：不自行计算金额，所有金额数据来自工具返回。

## 下单流程

1. 用户说"结算/下单" → 调用 cart_view 确认购物车
2. 如果购物车为空 → 提示用户先添加商品
3. 询问收货地址（首版可使用模拟地址）
4. 调用 order_preview 展示订单汇总
5. 用户确认 → 调用 order_create 创建订单
6. 返回订单号和确认信息

## 回复风格

- 清晰展示订单信息（商品、数量、金额）
- 逐步引导，不跳步
- 确认关键信息后再执行操作
```

---

## 8. RAG Pipeline 设计

### 8.1 整体流程

```
search_products(query, category?, brand?, price_min?, price_max?, exclude_keywords?, top_k?)
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│                    RAG Pipeline                          │
│                                                          │
│  Step 1: Query Enhancement                               │
│  ├─ 如果有 category，映射到类目关键词                      │
│  ├─ 如果有 exclude_keywords，构建排除条件                    │
│  └─ 组装增强查询文本                                      │
│                                                          │
│  Step 2: Vector Retrieval                                │
│  ├─ 智谱 Embedding → 向量化 query                        │
│  ├─ Chroma 相似度检索 Top-K*3 (扩大候选集)                │
│  └─ 返回 (chunk_id, product_id, score, text)             │
│                                                          │
│  Step 3: Structured Filtering                            │
│  ├─ 按 category 过滤（如果指定）                          │
│  ├─ 按 brand 过滤（如果指定）                             │
│  ├─ 按 price_min / price_max 过滤                        │
│  ├─ 按 exclude_keywords 排除                               │
│  └─ 去重（按 product_id）                                │
│                                                          │
│  Step 4: Reranking                                       │
│  ├─ 计算综合得分 = 向量相似度 * 0.6 + 结构化匹配度 * 0.4  │
│  └─ 取 Top-K                                             │
│                                                          │
│  Step 5: Result Assembly                                 │
│  ├─ 从商品 JSON 读取结构化字段（价格、SKU、图片等）        │
│  ├─ 组装返回结果（不包含 rag_knowledge 原文）              │
│  └─ 返回商品卡片数据                                     │
└──────────────────────────────────────────────────────────┘
```

### 8.2 Chunk 策略

每个商品生成 3 类 Chunk，分别入库：

| Chunk 类型 | 内容 | 元数据 |
|-----------|------|--------|
| marketing | `rag_knowledge.marketing_description` | product_id, category, sub_category, brand, base_price |
| faq | 每个 FAQ 问答对拼接为 "Q: {question} A: {answer}" | product_id, category, sub_category, brand |
| review_positive | 好评聚合摘要（rating >= 4 的评价聚合为一段文本） | product_id, category, sub_category, brand, rating_avg |
| review_negative | 差评聚合摘要（rating <= 2 的评价聚合为一段文本） | product_id, category, sub_category, brand, rating_avg |

评价按情感分桶聚合，而非简单拼接全部评价。这样做的优势：

1. **差评单独成块**：当用户问"这个商品有什么缺点"时，能精准检索到差评信息
2. **控制 Chunk 长度**：避免评价过多导致 Chunk 过长
3. **情感标签辅助过滤**：元数据中可标注情感极性

聚合示例（以实际数据 p_beauty_001 为例）：

```
review_positive chunk:
"好评汇总：用户'张雅静'评分5星，评价'熬夜党救星！每晚3滴吸收超快不黏腻，
第二天皮肤不暗沉。半个月后眼角干纹淡了，皮肤也紧致些，已经回购50ml加大装'。"

review_negative chunk:
"差评汇总：用户'李小米'评分1星，评价'用了两次就脸颊泛红刺痛，敏感肌可能不适用'；
用户'王梓涵'评分2星，评价'用了一个月淡纹紧致完全没效果，性价比太低'；
用户'刘梦琪'评分2星，评价'包装设计有问题瓶口残留，用了三周只有保湿效果'；
用户'陈宇飞'评分1星，评价'混油皮用了反而更干还冒闭口，不适合混油皮'。"
```

Chunk 元数据中保存结构化字段，用于 Step 3 的结构化过滤。

### 8.3 Chroma Collection 设计

```python
collection = chroma_client.get_or_create_collection(
    name="product_knowledge",
    metadata={"hnsw:space": "cosine"},
)

# 以实际商品 p_beauty_001（雅诗兰黛小棕瓶）为例
collection.add(
    ids=[
        "p_beauty_001_marketing",
        "p_beauty_001_faq_0",
        "p_beauty_001_faq_1",
        "p_beauty_001_faq_2",
        "p_beauty_001_review_positive",
        "p_beauty_001_review_negative",
    ],
    documents=[
        "雅诗兰黛特润修护肌活精华露（小棕瓶）是品牌经典抗初老单品...",
        "Q: 这款精华的核心成分二裂酵母发酵产物溶胞物有什么作用？ A: 二裂酵母发酵产物溶胞物是这款精华的核心修护成分...",
        "Q: 不同规格的小棕瓶怎么选？ A: 不同规格的选择可根据使用需求和频率...",
        "Q: 这款精华适合敏感肌吗？ A: 这款精华大部分肤质适用，但敏感肌需谨慎...",
        "好评汇总：用户'张雅静'评分5星，评价'熬夜党救星！每晚3滴吸收超快不黏腻...'",
        "差评汇总：用户'李小米'评分1星，评价'用了两次就脸颊泛红刺痛...'; 用户'王梓涵'评分2星...",
    ],
    embeddings=[emb_marketing, emb_faq_0, emb_faq_1, emb_faq_2, emb_review_pos, emb_review_neg],
    metadatas=[
        {"product_id": "p_beauty_001", "chunk_type": "marketing", "category": "美妆护肤", "sub_category": "精华", "brand": "雅诗兰黛", "base_price": 720.0},
        {"product_id": "p_beauty_001", "chunk_type": "faq", "category": "美妆护肤", "sub_category": "精华", "brand": "雅诗兰黛"},
        {"product_id": "p_beauty_001", "chunk_type": "faq", "category": "美妆护肤", "sub_category": "精华", "brand": "雅诗兰黛"},
        {"product_id": "p_beauty_001", "chunk_type": "faq", "category": "美妆护肤", "sub_category": "精华", "brand": "雅诗兰黛"},
        {"product_id": "p_beauty_001", "chunk_type": "review_positive", "category": "美妆护肤", "sub_category": "精华", "brand": "雅诗兰黛", "rating_avg": 2.2},
        {"product_id": "p_beauty_001", "chunk_type": "review_negative", "category": "美妆护肤", "sub_category": "精华", "brand": "雅诗兰黛", "rating_avg": 2.2},
    ],
)
```

### 8.4 检索实现

```python
class RAGService:
    async def search(
        self,
        query: str,
        category: str | None = None,
        brand: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        exclude_keywords: list[str] | None = None,
        top_k: int = 5,
    ) -> list[ProductSearchResult]:
        # Step 1: 向量检索
        query_embedding = await self.embedder.embed(query)
        results = self.vector_store.query(
            embedding=query_embedding,
            n_results=top_k * 3,
            where=self._build_where_clause(category, brand),
        )

        # Step 2: 结构化过滤
        filtered = self._apply_structured_filters(
            results, price_min, price_max, exclude_keywords
        )

        # Step 3: 去重（按 product_id）
        seen = set()
        unique = []
        for item in filtered:
            if item.product_id not in seen:
                seen.add(item.product_id)
                unique.append(item)

        # Step 4: 重排
        reranked = self._rerank(unique, query, top_k)

        # Step 5: 组装结果
        products = []
        for item in reranked:
            product_data = self.product_service.get_product(item.product_id)
            products.append(ProductSearchResult(
                product_id=product_data.product_id,
                title=product_data.title,
                brand=product_data.brand,
                category=product_data.category,
                base_price=product_data.base_price,
                image_path=product_data.image_path,
                skus=product_data.skus,
                relevance_score=item.score,
            ))

        return products

    def _build_where_clause(self, category: str | None, brand: str | None) -> dict | None:
        conditions = []
        if category:
            conditions.append({"category": category})
        if brand:
            conditions.append({"brand": brand})
        if not conditions:
            return None
        return {"$and": conditions} if len(conditions) > 1 else conditions[0]
```

---

## 9. 上下文管理与会话状态

### 9.1 会话上下文结构

```python
class ConversationContext:
    user_id: str
    session_id: str
    messages: list[Message]              # 完整对话历史
    recent_history: str                  # 最近 N 轮对话摘要文本
    recent_product_cards: list[Product]  # 最近一次展示的商品卡片
    cart_summary: str                    # 当前购物车摘要
    conversation_state: ConversationState  # 对话状态标签
    summary_text: str | None             # 历史摘要（窗口外的消息压缩结果）
    metadata: dict                       # 扩展信息


class ConversationState(str, Enum):
    IDLE = "idle"                        # 初始状态 / 闲聊
    RECOMMENDING = "recommending"        # 正在推荐商品
    COMPARING = "comparing"              # 正在对比商品
    CART_MANAGING = "cart_managing"      # 正在操作购物车
    ORDERING = "ordering"                # 正在下单流程
```

### 9.2 上下文构建策略

```python
class ContextBuilder:
    def __init__(self, session_service: SessionService, cart_service: CartService):
        self.session_service = session_service
        self.cart_service = cart_service

    async def build(self, session: Session, cart: Cart) -> ConversationContext:
        recent_messages = session.messages[-10:]
        recent_history = self._format_history(recent_messages)
        recent_products = self._extract_recent_products(recent_messages)
        cart_summary = self._format_cart_summary(cart)

        state = self._infer_state(recent_messages, session.state)
        summary_text = session.summary_text

        return ConversationContext(
            user_id=session.user_id,
            session_id=session.id,
            messages=session.messages,
            recent_history=recent_history,
            recent_product_cards=recent_products,
            cart_summary=cart_summary,
            conversation_state=state,
            summary_text=summary_text,
            metadata={},
        )

    def _format_cart_summary(self, cart: Cart) -> str:
        if not cart.items:
            return "购物车为空"
        lines = [f"- {item.title} ({item.sku_label}) x{item.quantity} = ¥{item.price * item.quantity}" for item in cart.items]
        total = sum(item.price * item.quantity for item in cart.items)
        return f"购物车共{len(cart.items)}件商品，合计¥{total}：\n" + "\n".join(lines)

    def _extract_recent_products(self, messages: list[Message]) -> list[Product]:
        for msg in reversed(messages):
            if msg.products:
                return msg.products
        return []

    def _infer_state(
        self,
        recent_messages: list[Message],
        persisted_state: ConversationState | None,
    ) -> ConversationState:
        if not recent_messages:
            return ConversationState.IDLE

        last_user_msg = None
        last_assistant_msg = None
        for msg in reversed(recent_messages):
            if msg.role == MessageRole.USER and last_user_msg is None:
                last_user_msg = msg.content
            elif msg.role == MessageRole.ASSISTANT and last_assistant_msg is None:
                last_assistant_msg = msg.content
            if last_user_msg and last_assistant_msg:
                break

        if not last_user_msg:
            return persisted_state or ConversationState.IDLE

        state = self._classify_state(last_user_msg, last_assistant_msg)

        if state is None:
            return persisted_state or ConversationState.IDLE

        return state

    def _classify_state(
        self,
        last_user_msg: str,
        last_assistant_msg: str | None,
    ) -> ConversationState | None:
        user_lower = last_user_msg.lower()

        cart_keywords = ["购物车", "加购", "加入", "买这个", "要这个", "删掉", "不要了", "移除", "数量", "再加", "少买"]
        order_keywords = ["结算", "下单", "结账", "付款", "确认购买", "订单", "总价"]
        compare_keywords = ["对比", "比较", "哪个好", "区别", "vs", "和.*哪个"]
        recommend_keywords = ["推荐", "有什么", "想买", "找", "适合", "好用", "求推荐"]

        if any(kw in user_lower for kw in order_keywords):
            return ConversationState.ORDERING
        if any(kw in user_lower for kw in cart_keywords):
            return ConversationState.CART_MANAGING
        if any(kw in user_lower for kw in compare_keywords):
            return ConversationState.COMPARING
        if any(kw in user_lower for kw in recommend_keywords):
            return ConversationState.RECOMMENDING

        if last_assistant_msg:
            assistant_lower = last_assistant_msg.lower()
            if any(kw in assistant_lower for kw in ["购物车", "已加入", "已移除"]):
                return ConversationState.CART_MANAGING
            if any(kw in assistant_lower for kw in ["订单", "结算", "下单"]):
                return ConversationState.ORDERING
            if any(kw in assistant_lower for kw in ["对比", "区别"]):
                return ConversationState.COMPARING
            if any(kw in assistant_lower for kw in ["推荐", "为你找到", "商品"]):
                return ConversationState.RECOMMENDING

        return None
```

### 9.3 状态持久化

对话状态持久化到 SQLite `sessions` 表的 `state` 列，每次编排器执行完 Agent 后更新：

```python
class SessionService:
    async def update_state(self, session_id: str, state: ConversationState) -> None:
        await self.db.execute(
            "UPDATE sessions SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (state.value, session_id),
        )

    async def update_summary(self, session_id: str, summary_text: str) -> None:
        await self.db.execute(
            "UPDATE sessions SET summary_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (summary_text, session_id),
        )
```

### 9.4 状态转换表

```
┌──────────────────────────────────────────────────────────────────────┐
│                        状态转换规则                                   │
├─────────────────┬───────────────────────────────────────────────────┤
│  当前状态        │  触发条件                         │  新状态       │
├─────────────────┼───────────────────────────────────┼───────────────┤
│  IDLE           │  用户请求推荐/筛选商品             │  RECOMMENDING │
│  IDLE           │  用户请求对比商品                  │  COMPARING    │
│  IDLE           │  用户操作购物车                    │  CART_MANAGING│
│  IDLE           │  用户请求下单                      │  ORDERING     │
│  RECOMMENDING   │  用户继续追问/细化推荐             │  RECOMMENDING │
│  RECOMMENDING   │  用户请求对比                      │  COMPARING    │
│  RECOMMENDING   │  用户加购/操作购物车               │  CART_MANAGING│
│  RECOMMENDING   │  用户闲聊/无明确意图               │  IDLE         │
│  COMPARING      │  用户继续对比/追问差异             │  COMPARING    │
│  COMPARING      │  用户加购                          │  CART_MANAGING│
│  COMPARING      │  用户请求新推荐                    │  RECOMMENDING │
│  COMPARING      │  用户闲聊/无明确意图               │  IDLE         │
│  CART_MANAGING  │  用户继续操作购物车                │  CART_MANAGING│
│  CART_MANAGING  │  用户请求下单                      │  ORDERING     │
│  CART_MANAGING  │  用户请求推荐                      │  RECOMMENDING │
│  CART_MANAGING  │  用户闲聊/无明确意图               │  IDLE         │
│  ORDERING       │  用户继续下单流程                  │  ORDERING     │
│  ORDERING       │  用户请求推荐                      │  RECOMMENDING │
│  ORDERING       │  订单创建完成                      │  IDLE         │
└─────────────────┴───────────────────────────────────┴───────────────┘
```

状态转换由编排器在 Agent 执行完成后调用 `_update_conversation_state` 完成（见 §11.1）。

### 9.5 对话历史管理

| 策略 | 说明 |
|------|------|
| 完整历史 | 存储在 SQLite 中，用于持久化和历史会话查看 |
| 滑动窗口 | 发送给 LLM 时只取最近 N 轮（默认 10 条），避免 Token 超限 |
| 摘要压缩 | 当历史超过窗口时，对窗口外的消息生成摘要，作为 System Prompt 的一部分 |

### 9.6 摘要压缩机制

#### 触发条件

当会话消息总数超过滑动窗口大小（默认 10 条）时，对窗口外的消息生成摘要。具体规则：

- 窗口大小：`SESSION_CONTEXT_WINDOW = 10`（最近 10 条消息直接发送给 LLM）
- 摘要触发：`len(messages) > SESSION_CONTEXT_WINDOW`
- 摘要范围：`messages[:-SESSION_CONTEXT_WINDOW]`（窗口外的所有消息）
- 摘要更新时机：每次窗口外消息有新增时重新生成（即每次新消息导致窗口外消息增加时）

#### 摘要生成 Prompt

```markdown
你是一个对话摘要生成器。请将以下用户与AI导购助手的对话历史压缩为一段简洁的摘要。

## 要求

1. 保留用户的核心需求（想买什么、预算、偏好、排除条件）
2. 保留已推荐的商品名称和ID（如果用户表达了偏好，也保留）
3. 保留购物车操作结果（加了什么、删了什么）
4. 保留订单状态（是否已下单）
5. 丢弃闲聊、重复提问、无效信息
6. 摘要不超过 200 字
7. 使用第三人称客观描述

## 输出格式

直接输出摘要文本，不要输出任何前缀或标签。

## 对话历史

{conversation_text}
```

#### 摘要存储位置

摘要存储在 SQLite `sessions` 表的 `summary_text` 列中：

```sql
ALTER TABLE sessions ADD COLUMN summary_text TEXT;
```

每次摘要更新后，通过 `SessionService.update_summary()` 持久化。

#### 摘要注入方式

摘要作为 System Prompt 的一部分注入到发送给 LLM 的 messages 中，位于 Agent System Prompt 之后、对话历史之前：

```python
def _build_messages(self, user_message: str, context: ConversationContext) -> list[dict]:
    messages = [
        {"role": "system", "content": self.system_prompt},
    ]

    if context.conversation_state != ConversationState.IDLE:
        messages.append({
            "role": "system",
            "content": f"当前对话状态：{context.conversation_state.value}。购物车摘要：{context.cart_summary}",
        })

    if context.summary_text:
        messages.append({
            "role": "system",
            "content": f"【历史对话摘要】\n{context.summary_text}",
        })

    if context.recent_product_cards:
        product_summary = "最近展示的商品：" + "、".join(
            [f"{p.title}(ID:{p.product_id},¥{p.base_price})" for p in context.recent_product_cards]
        )
        messages.append({"role": "system", "content": product_summary})

    window = context.messages[-10:]
    for msg in window:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

    return messages
```

#### 摘要生成实现

```python
class SummaryService:
    SUMMARY_PROMPT = """你是一个对话摘要生成器。请将以下用户与AI导购助手的对话历史压缩为一段简洁的摘要。

## 要求

1. 保留用户的核心需求（想买什么、预算、偏好、排除条件）
2. 保留已推荐的商品名称和ID（如果用户表达了偏好，也保留）
3. 保留购物车操作结果（加了什么、删了什么）
4. 保留订单状态（是否已下单）
5. 丢弃闲聊、重复提问、无效信息
6. 摘要不超过 200 字
7. 使用第三人称客观描述

## 输出格式

直接输出摘要文本，不要输出任何前缀或标签。

## 对话历史

{conversation_text}"""

    def __init__(self, llm_client: ZhipuClient, context_window: int = 10):
        self.llm_client = llm_client
        self.context_window = context_window

    async def generate_if_needed(
        self,
        session: Session,
    ) -> str | None:
        if len(session.messages) <= self.context_window:
            return session.summary_text

        old_messages = session.messages[:-self.context_window]

        if session.summary_text and not self._has_new_messages_since_last_summary(session):
            return session.summary_text

        conversation_text = self._format_messages(old_messages)

        summary = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": self.SUMMARY_PROMPT.format(conversation_text=conversation_text)},
                {"role": "user", "content": "请生成摘要"},
            ],
            model="glm-4-flash",
            temperature=0.1,
            max_tokens=300,
        )

        return summary.choices[0].message.content

    def _has_new_messages_since_last_summary(self, session: Session) -> bool:
        return len(session.messages) > self.context_window + 2

    def _format_messages(self, messages: list[Message]) -> str:
        lines = []
        for msg in messages:
            role_label = "用户" if msg.role == MessageRole.USER else "助手"
            content = msg.content[:200] if len(msg.content) > 200 else msg.content
            lines.append(f"{role_label}：{content}")
        return "\n".join(lines)
```

---

## 10. SSE 流式返回设计

### 10.0 Chat 请求模型

```python
class ChatStreamRequest(BaseModel):
    message: str                       # 用户消息文本
    session_id: str | None = None      # 会话ID，为空则创建新会话
    image_url: str | None = None       # 图片URL（图片找货时传入）
```

请求示例：

```json
{
  "message": "推荐一个面霜",
  "session_id": "sess_abc123",
  "image_url": null
}
```

图片找货请求示例：

```json
{
  "message": "帮我找类似的商品",
  "session_id": "sess_abc123",
  "image_url": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

### 10.1 SSE 事件格式

与前端 API 规范对齐，定义以下事件类型：

```python
class SSEEventType(str, Enum):
    TEXT_DELTA = "text_delta"           # 文本增量
    PRODUCT_CARDS = "product_cards"     # 商品卡片列表
    TOOL_RESULT = "tool_result"         # 工具执行结果
    DONE = "done"                       # 完成
    ERROR = "error"                     # 错误


class SSEEvent(BaseModel):
    type: SSEEventType
    data: dict


def format_sse_event(event: SSEEvent) -> str:
    return f"event: {event.type.value}\ndata: {event.data.json()}\n\n"
```

### 10.2 各事件数据格式

#### text_delta

```json
{
  "content": "为你找到以下",
  "message_id": "msg_abc123"
}
```

#### product_cards

```json
{
  "products": [
    {
      "id": "p_beauty_001",
      "title": "雅诗兰黛特润修护肌活精华露淡纹紧致保湿夜间修护抗初老精华30ml",
      "brand": "雅诗兰黛",
      "category": "美妆护肤",
      "sub_category": "精华",
      "price": 720.0,
      "rating": 2.2,
      "image": "/data/1_美妆护肤/images/p_beauty_001_live.jpg",
      "skus": [
        {"sku_id": "s_p_beauty_001_1", "label": "30ml 经典装", "price": 720.0},
        {"sku_id": "s_p_beauty_001_2", "label": "50ml 加大装", "price": 980.0},
        {"sku_id": "s_p_beauty_001_3", "label": "75ml 家用装", "price": 1260.0}
      ]
    }
  ]
}
```

#### tool_result

```json
{
  "tool": "cart_add",
  "success": true,
  "message": "已将雅诗兰黛小棕瓶加入购物车",
  "cart_item": {
    "id": "cart_item_001",
    "title": "雅诗兰黛特润修护肌活精华露",
    "sku": "30ml 经典装",
    "price": 720.0,
    "quantity": 1
  }
}
```

#### done

```json
{
  "message_id": "msg_abc123"
}
```

#### error

```json
{
  "code": "TOOL_EXECUTION_ERROR",
  "message": "商品不存在",
  "details": {}
}
```

### 10.3 SSE 端点实现

```python
@router.post("/api/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
):
    async def event_generator():
        try:
            context = await context_builder.build(
                session_id=request.session_id,
                user_id=current_user.id,
            )

            async for event in orchestrator.run(
                user_message=request.message,
                context=context,
            ):
                yield format_sse_event(event)

                if event.type == SSEEventType.TOOL_RESULT:
                    await session_service.save_tool_result(
                        session_id=request.session_id,
                        event=event,
                    )

        except Exception as e:
            yield format_sse_event(SSEEvent(
                type=SSEEventType.ERROR,
                data={"code": "INTERNAL_ERROR", "message": str(e), "details": {}},
            ))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

---

## 11. Agent 编排器设计

### 11.1 编排器核心逻辑

```python
class AgentOrchestrator:
    def __init__(
        self,
        router_agent: RouterAgent,
        agents: dict[str, BaseAgent],
        session_service: SessionService,
        summary_service: SummaryService,
    ):
        self.router = router_agent
        self.agents = agents
        self.session_service = session_service
        self.summary_service = summary_service

    async def run(
        self,
        user_message: str,
        context: ConversationContext,
    ) -> AsyncGenerator[SSEEvent, None]:
        # Step 1: Router 分类意图（支持混合意图）
        route_output = await self.router.route(user_message, context)

        # Step 2: 按顺序执行每个路由结果
        for i, route_result in enumerate(route_output.routes):
            target_agent = self.agents.get(route_result.target_agent)
            if not target_agent:
                yield SSEEvent(type=SSEEventType.ERROR, data={
                    "code": "AGENT_NOT_FOUND",
                    "message": f"Agent {route_result.target_agent} 不存在",
                })
                continue

            # Step 3: 注入路由参数到上下文
            context.metadata["route_params"] = route_result.extracted_params
            context.metadata["intent"] = route_result.intent

            # Step 4: 执行目标 Agent
            async for event in target_agent.run(user_message, context):
                yield event

            # Step 5: 混合意图时，在多个 Agent 之间插入分隔提示
            if route_output.is_multi_intent and i < len(route_output.routes) - 1:
                yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={
                    "content": "\n\n---\n\n",
                })

        # Step 6: 更新对话状态
        if route_output.routes:
            last_intent = route_output.routes[-1].intent
            await self._update_conversation_state(context, last_intent)

        # Step 7: 摘要压缩（如果需要）
        session = await self.session_service.get_session(context.session_id)
        summary = await self.summary_service.generate_if_needed(session)
        if summary is not None and summary != session.summary_text:
            await self.session_service.update_summary(context.session_id, summary)

    async def _update_conversation_state(
        self,
        context: ConversationContext,
        intent: IntentType,
    ) -> None:
        state_map = {
            IntentType.PRODUCT_RECOMMEND: ConversationState.RECOMMENDING,
            IntentType.PRODUCT_FILTER: ConversationState.RECOMMENDING,
            IntentType.PRODUCT_COMPARE: ConversationState.COMPARING,
            IntentType.PRODUCT_DETAIL: ConversationState.RECOMMENDING,
            IntentType.CART_ADD: ConversationState.CART_MANAGING,
            IntentType.CART_REMOVE: ConversationState.CART_MANAGING,
            IntentType.CART_UPDATE: ConversationState.CART_MANAGING,
            IntentType.CART_VIEW: ConversationState.CART_MANAGING,
            IntentType.ORDER_PREVIEW: ConversationState.ORDERING,
            IntentType.ORDER_CREATE: ConversationState.ORDERING,
            IntentType.GENERAL_CHAT: ConversationState.IDLE,
        }
        new_state = state_map.get(intent, ConversationState.IDLE)
        await self.session_service.update_state(context.session_id, new_state)
```

### 11.2 Fallback 机制

```python
async def run(self, user_message: str, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
    try:
        route_output = await self.router.route(user_message, context)
    except Exception:
        # Router 失败时 fallback 到导购 Agent
        route_output = RouteOutput(
            routes=[RouteResult(
                intent=IntentType.GENERAL_CHAT,
                target_agent="guide_agent",
                extracted_params={"query": user_message},
                confidence=0.0,
            )],
            is_multi_intent=False,
        )

    for i, route_result in enumerate(route_output.routes):
        target_agent = self.agents.get(route_result.target_agent, self.agents["guide_agent"])

        try:
            async for event in target_agent.run(user_message, context):
                yield event
        except Exception as e:
            yield SSEEvent(type=SSEEventType.ERROR, data={
                "code": "AGENT_EXECUTION_ERROR",
                "message": str(e),
            })
            yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={
                "content": "抱歉，处理您的请求时遇到了问题，请稍后再试。",
            })
            yield SSEEvent(type=SSEEventType.DONE, data={})
            return

        if route_output.is_multi_intent and i < len(route_output.routes) - 1:
            yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={
                "content": "\n\n---\n\n",
            })
```

---

## 12. 数据模型设计

### 12.1 商品模型

```python
class ProductSKU(BaseModel):
    sku_id: str
    properties: dict[str, str]      # {"容量": "30ml 经典装"}
    price: float

class ProductFAQ(BaseModel):
    question: str
    answer: str

class ProductReview(BaseModel):
    nickname: str
    rating: int                      # 1-5
    content: str

class ProductRAGKnowledge(BaseModel):
    marketing_description: str
    official_faq: list[ProductFAQ]
    user_reviews: list[ProductReview]

class Product(BaseModel):
    product_id: str                  # "p_beauty_001"
    title: str                       # "雅诗兰黛特润修护肌活精华露淡纹紧致保湿夜间修护抗初老精华30ml"
    brand: str                       # "雅诗兰黛"
    category: str                    # "美妆护肤"
    sub_category: str                # "精华"
    base_price: float                # 720.0
    image_path: str                  # "1_美妆护肤/images/p_beauty_001_live.jpg"（相对于 data/ 目录）
    skus: list[ProductSKU]
    rag_knowledge: ProductRAGKnowledge
    rating_avg: float | None = None  # 从 user_reviews 动态计算

    def compute_rating_avg(self) -> float:
        reviews = self.rag_knowledge.user_reviews
        if not reviews:
            return 0.0
        return sum(r.rating for r in reviews) / len(reviews)

    def get_image_url(self) -> str:
        return f"/data/{self.image_path}"

    def get_sku_label(self, sku_id: str) -> str:
        for sku in self.skus:
            if sku.sku_id == sku_id:
                return " ".join(sku.properties.values())
        return "默认规格"

    def get_default_sku(self) -> ProductSKU:
        return self.skus[0] if self.skus else None
```

### 12.2 会话模型

```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    products: list[Product] | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None

class Session(BaseModel):
    id: str
    user_id: str
    title: str
    state: ConversationState = ConversationState.IDLE
    summary_text: str | None = None
    messages: list[Message]
    created_at: datetime
    updated_at: datetime
```

### 12.3 购物车模型

```python
class CartItem(BaseModel):
    id: str
    user_id: str
    product_id: str
    sku_id: str
    title: str
    sku_label: str
    price: float
    quantity: int
    image_path: str
    created_at: datetime

class Cart(BaseModel):
    user_id: str
    items: list[CartItem]

    @property
    def total_price(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    @property
    def total_count(self) -> int:
        return sum(item.quantity for item in self.items)
```

### 12.4 订单模型

```python
class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    product_id: str
    sku_id: str
    title: str
    sku_label: str
    price: float
    quantity: int
    image_path: str

class Order(BaseModel):
    id: str
    order_no: str
    user_id: str
    items: list[OrderItem]
    total_price: float
    address: str
    status: OrderStatus
    created_at: datetime
```

### 12.5 用户模型

```python
class User(BaseModel):
    id: str
    phone: str | None = None
    email: str | None = None
    nickname: str
    avatar: str | None = None
    created_at: datetime
```

---

## 13. 智谱模型网关设计

### 13.1 客户端封装

```python
class APICallRecord(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    call_type: str                    # "chat" | "embedding" | "image_understand"
    timestamp: datetime

class ZhipuClient:
    def __init__(self, api_key: str, llm_model: str, embedding_model: str):
        self.api_key = api_key
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self._call_records: list[APICallRecord] = []

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[ChatChunk, None] | ChatResponse:
        """调用智谱 LLM，支持流式和工具调用"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """调用智谱 Embedding 模型"""
        ...

    async def image_understand(self, image_url: str, prompt: str) -> str:
        """调用智谱多模态模型，理解图片内容"""
        ...

    def _record_call(self, record: APICallRecord) -> None:
        self._call_records.append(record)

    def get_call_stats(self) -> dict:
        total_calls = len(self._call_records)
        total_tokens = sum(r.total_tokens for r in self._call_records)
        by_model = {}
        for r in self._call_records:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "tokens": 0}
            by_model[r.model]["calls"] += 1
            by_model[r.model]["tokens"] += r.total_tokens
        by_type = {}
        for r in self._call_records:
            if r.call_type not in by_type:
                by_type[r.call_type] = {"calls": 0, "tokens": 0}
            by_type[r.call_type]["calls"] += 1
            by_type[r.call_type]["tokens"] += r.total_tokens
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "by_model": by_model,
            "by_type": by_type,
        }

    def reset_stats(self) -> None:
        self._call_records.clear()
```

调用统计可通过管理端点查看：

```python
@router.get("/api/admin/call-stats")
async def get_call_stats(
    current_user: User = Depends(get_current_user),
):
    return zhipu_client.get_call_stats()
```

### 13.2 模型选择

| 用途 | 模型 | 说明 |
|------|------|------|
| Router 意图识别 | glm-4-flash | 速度快、成本低，分类任务不需要强推理 |
| 导购 Agent | glm-4-plus | 需要理解需求、生成推荐话术 |
| 购物车 Agent | glm-4-flash | 确定性操作，不需要强推理 |
| 订单 Agent | glm-4-flash | 流程化操作，不需要强推理 |
| Embedding | embedding-3 | 向量化商品知识 |

---

## 14. 幻觉防控体系

### 14.1 多层防线

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Prompt 约束                            │
│  System Prompt 明确禁止编造商品/价格/库存/SKU     │
├─────────────────────────────────────────────────┤
│  Layer 2: Tool-First 原则                        │
│  所有商品信息必须通过工具获取，LLM 不自由生成      │
├─────────────────────────────────────────────────┤
│  Layer 3: 结构化数据源                           │
│  商品卡片数据只来自工具返回的结构化结果            │
│  价格/SKU 从商品 JSON 读取，不来自 RAG 文本块     │
├─────────────────────────────────────────────────┤
│  Layer 4: Agent 隔离                             │
│  购物车/订单 Agent 只做确定性操作                 │
│  导购 Agent 的创造性输出受工具结果约束            │
├─────────────────────────────────────────────────┤
│  Layer 5: 输出校验（必须）                        │
│  对 LLM 输出中提到的商品进行后验校验              │
│  确保提到的商品 ID 存在于检索结果中               │
└─────────────────────────────────────────────────┘
```

### 14.2 输出校验实现

```python
class OutputValidator:
    def validate_product_references(
        self,
        llm_output: str,
        search_results: list[ProductSearchResult],
    ) -> ValidationResult:
        mentioned_ids = set()
        for product in search_results:
            if product.product_id in llm_output or product.title in llm_output:
                mentioned_ids.add(product.product_id)

        for product_id in mentioned_ids:
            if product_id not in {p.product_id for p in search_results}:
                return ValidationResult(
                    valid=False,
                    reason=f"LLM 输出中提到了检索结果之外的商品 {product_id}",
                )

        return ValidationResult(valid=True)
```

---

## 15. 错误处理设计

### 15.1 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| Router 分类失败 | `ROUTE_ERROR` | Fallback 到 guide_agent |
| LLM 调用失败 | `LLM_ERROR` | 重试 1 次，仍失败则返回错误 |
| 工具执行失败 | `TOOL_ERROR` | 返回错误信息，Agent 决定是否重试 |
| 商品不存在 | `PRODUCT_NOT_FOUND` | Agent 告知用户 |
| 购物车为空 | `CART_EMPTY` | Agent 引导用户先添加商品 |
| 会话不存在 | `SESSION_NOT_FOUND` | 自动创建新会话 |
| Token 无效 | `AUTH_ERROR` | 返回 401 |

### 15.2 统一错误响应

```python
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict = {}
```

---

## 16. 数据库设计

### 16.1 存储方案

首版使用 **SQLite**，通过 aiosqlite 提供异步访问。商品数据使用 JSON 文件存储，Chroma 存储向量。

| 数据 | 存储位置 | 说明 |
|------|---------|------|
| 用户 | SQLite | 简单账号信息 |
| 会话与消息 | SQLite | 对话历史持久化 |
| 购物车 | SQLite | 购物车状态 |
| 订单 | SQLite | 模拟订单 |
| 商品数据 | JSON 文件 | data/{类目}/data/ 按类目分目录 |
| 商品图片 | 本地文件 | data/{类目}/images/ 按类目分目录，通过 /data/ 路径访问 |
| 商品向量 | Chroma | 向量检索 |

实际数据目录结构（以 p_beauty_001 为例）：

```text
data/
├── 1_美妆护肤/
│   ├── data/
│   │   ├── p_beauty_001.json
│   │   └── ...
│   └── images/
│       ├── p_beauty_001_live.jpg
│       └── ...
├── 2_数码电子/
│   ├── data/
│   │   ├── p_digital_001.json
│   │   └── ...
│   └── images/
│       └── ...
├── 3_服饰运动/
│   └── ...
└── 4_食品饮料/
    └── ...
```

商品 JSON 中的 `image_path` 格式为 `1_美妆护肤/images/p_beauty_001_live.jpg`，相对于 `data/` 目录。
后端提供静态文件服务时，将 `data/` 目录挂载到 `/data` 路径，前端通过 `/data/{image_path}` 访问图片。
Product 模型的 `get_image_url()` 方法返回 `/data/{self.image_path}`，与前端 URL 一致。

```python
# main.py 中静态文件服务配置
app.mount("/data", StaticFiles(directory="data"), name="static-data")
```

### 16.2 SQLite 表结构

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    nickname TEXT NOT NULL,
    avatar TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL DEFAULT '新对话',
    state TEXT NOT NULL DEFAULT 'idle' CHECK(state IN ('idle', 'recommending', 'comparing', 'cart_managing', 'ordering')),
    summary_text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    products_json TEXT,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cart_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    product_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    title TEXT NOT NULL,
    sku_label TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    image_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    order_no TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    items_json TEXT NOT NULL,
    total_price REAL NOT NULL,
    address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('pending', 'confirmed', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 17. 配置管理

### 17.1 环境变量

```env
# 智谱模型
ZHIPU_API_KEY=your_api_key
ZHIPU_LLM_MODEL=glm-4-plus
ZHIPU_LLM_MODEL_FAST=glm-4-flash
ZHIPU_EMBEDDING_MODEL=embedding-3

# 服务端口
SERVER_PORT=8000
CLIENT_PORT=3000

# 数据路径
CHROMA_PATH=./data/chroma
PRODUCT_DATA_PATH=./data/products
IMAGE_DATA_PATH=./data/images

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/app.db

# 会话配置
SESSION_MAX_HISTORY=50
SESSION_CONTEXT_WINDOW=10
SUMMARY_MAX_TOKENS=300

# RAG 配置
RAG_TOP_K=5
RAG_CANDIDATE_MULTIPLIER=3
RAG_VECTOR_WEIGHT=0.6
RAG_STRUCTURED_WEIGHT=0.4
```

### 17.2 配置类

```python
class Settings(BaseSettings):
    zhipu_api_key: str
    zhipu_llm_model: str = "glm-4-plus"
    zhipu_llm_model_fast: str = "glm-4-flash"
    zhipu_embedding_model: str = "embedding-3"

    server_port: int = 8000
    client_port: int = 3000

    chroma_path: str = "./data/chroma"
    product_data_path: str = "./data/products"
    image_data_path: str = "./data/images"

    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    session_max_history: int = 50
    session_context_window: int = 10
    summary_max_tokens: int = 300

    rag_top_k: int = 5
    rag_candidate_multiplier: int = 3
    rag_vector_weight: float = 0.6
    rag_structured_weight: float = 0.4

    class Config:
        env_file = ".env"
```

---

## 18. 多模态扩展设计

### 18.1 图片找货流程

```
用户上传图片
  │
  ▼
POST /api/chat/stream (image_url 参数)
  │
  ▼
智谱多模态模型 → 提取图片中的商品特征
  │  输出：{category, color, style, keywords}
  │
  ▼
将提取结果作为 query → 进入正常 RAG 检索流程
  │
  ▼
导购 Agent 基于检索结果生成推荐
```

### 18.2 语音输入流程

```
用户点击语音按钮 → 前端录音
  │
  ▼
前端使用 Web Speech API / 后端 ASR → 转文字
  │
  ▼
文字作为普通消息 → 进入正常导购流程
```

---

## 19. 依赖清单

```
# requirements.txt
fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
httpx>=0.27.0
aiosqlite>=0.20.0
chromadb>=0.5.0
zhipuai>=2.1.0
python-jose>=3.3.0
passlib>=1.7.4
python-multipart>=0.0.9
sse-starlette>=2.0.0
```

---

## 20. 开发优先级与里程碑对齐

与调整后的项目开发计划对齐，后端开发按以下顺序推进：

### M4a：后端骨架 + 数据服务 + 认证（3天）

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | 项目初始化：FastAPI 骨架 + config + 目录结构 + requirements.txt | 无 |
| P0 | 数据模型定义（Product/Cart/Order/Session/User）+ SQLite 初始化 | 无 |
| P0 | 认证服务：简单登录 + JWT + 依赖注入 | 数据模型 |
| P0 | 商品数据服务：加载 JSON + 商品列表/详情 API | 数据模型 |
| P0 | 购物车服务 + 订单服务：CRUD API | 数据模型 + 认证 |

**验证点**：`uvicorn server.main:app` 启动，Swagger UI 可调用所有 REST API

### M4b：RAG Pipeline（3天）

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | 智谱客户端封装：LLM chat/stream + Embedding | 无 |
| P0 | 商品知识分块：marketing/faq/review_positive/review_negative | 商品数据 |
| P0 | Chroma 向量库：导入 + 检索 + 结构化过滤 | Embedding + 分块 |
| P0 | RAG Service：检索 + 过滤 + 重排 + 结果组装 | Chroma + 商品数据 |
| P1 | seed_products.py 数据导入脚本 | 全部 RAG 组件 |

**验证点**：`rag_service.search("适合油皮的护肤品")` 返回正确商品

### M5：Agent 层 + Chat API（5天）

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | Agent 基类 + 工具注册表 + 核心循环 | 无 |
| P0 | Router Agent：意图识别 + 混合意图分发 | 智谱客户端 |
| P0 | 导购 Agent + search_products/get_product_detail/compare_products | RAG Pipeline |
| P0 | 购物车 Agent + cart_add（sku_id 非必填）/cart_remove/cart_update/cart_view | 购物车服务 |
| P0 | 订单 Agent + order_preview/order_create | 订单服务 |
| P0 | Agent 编排器：混合意图顺序执行 + 状态转换 + Fallback | Router + 所有 Agent |
| P0 | SSE 流式返回 + Chat API（含 image_url 参数） | 编排器 + SSE |
| P0 | Prompt 模板创建与调优（Router/Guide/Cart/Order 四个 .md） | Agent 基类 |
| P1 | 上下文管理 + 状态推断 + 状态持久化 + 指代消解 | 编排器 |
| P1 | 输出校验（幻觉防控第 5 层） | 幻觉防控 |
| P1 | 摘要压缩机制（SummaryService） | 智谱客户端 |
| P2 | 多轮对话优化 | 上下文管理 |

**验证点**：通过 API 发送聊天消息，收到 SSE 流式回复 + 商品卡片

### M6：前后端联调 + 多模态（4天）

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | 前端对接后端 Chat API + SSE 事件处理 | Chat API |
| P0 | 前端对接购物车/订单 REST API | REST API |
| P1 | 图片上传 + 智谱视觉理解 + 图片找货 | 智谱多模态 |
| P2 | 语音输入支持 | 前端 ASR |
| P2 | TTS 播报 | 智谱 TTS |

**验证点**：前端完整跑通"聊天→推荐→加购→下单"闭环

### M7：部署 + 答辩（3天）

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | Docker 部署配置 | 全部 |
| P0 | 演示脚本 + 测试用例 | 全部 |
| P0 | 答辩材料 + 最终修复 | 全部 |

**验证点**：本地一键启动，云端可部署演示

---

## 21. 关键设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 编排框架 | 手写 Agent 循环 + zhipuai SDK 直调 | 零格式转换摩擦、流式输出自然顺畅、调试 100% 透明、12 个依赖 vs 45 个 |
| 不选 LangGraph | 混合方案（LangGraph + zhipuai 直调）性价比最低 | 承担依赖开销和格式转换摩擦，却没得到流式+Tool Calling 自动化的核心好处 |
| 不选全 LangGraph | langchain-zhipu 社区维护，兼容性风险 | astream_events 流式可能丢 chunk，状态管理黑盒，答辩时不好讲 |
| Agent 架构 | Router + 专项 Agent | 模块化、幻觉控制好、可扩展 |
| Router 实现 | 单次 LLM + Function Calling | 确定性输出、快速、格式一致 |
| 混合意图 | Router 输出 list[RouteResult]，编排器顺序执行 | 支持用户一条消息包含多个意图，提升交互自然度 |
| 购物车操作 | Tool Calling 而非 LLM 自由生成 | 确定性要求高，不能出错 |
| cart_add sku_id | 非必填，工具实现自动选择默认 SKU | 用户通常不知道 SKU ID，自动选择更健壮 |
| 商品数据存储 | JSON 文件（按类目分目录） | 商品数量有限，无需数据库；类目分目录便于管理 |
| 图片路径格式 | `image_path` 相对于 `data/` 目录，URL 为 `/data/{image_path}` | 与实际 JSON 数据一致，FastAPI 挂载 StaticFiles 即可 |
| 商品模型 | 以商品 JSON 为准，不含 tags/attributes/sales_count/stock_status | 数据源中无这些字段，避免模型与数据不一致 |
| 排除过滤 | exclude_keywords 替代 exclude_tags | 商品数据无 tags 字段，关键词匹配更灵活 |
| 评价分块策略 | 按情感分桶（好评/差评分别聚合） | 差评单独成块，支持"有什么缺点"类查询 |
| 会话/购物车/订单存储 | SQLite | 轻量、本地运行、无需额外服务 |
| 向量存储 | Chroma 本地持久化 | 与需求文档一致，轻量 |
| 对话历史 | 滑动窗口 + 摘要压缩 | 控制 Token 消耗，保留关键上下文 |
| 摘要触发 | 消息数 > 10 条时对窗口外消息生成摘要 | 平衡上下文完整性和 Token 消耗 |
| 摘要模型 | glm-4-flash | 摘要生成不需要强推理，成本低速度快 |
| 状态持久化 | sessions 表增加 state/summary_text 列 | 跨轮对话可利用状态信息优化 Router 判断 |
| 输出校验 | P1 必须 | 唯一能捕获 LLM 绕过工具编造商品信息的防线 |
| Router 模型 | glm-4-flash | 分类任务不需要强推理，速度快成本低 |
| 导购模型 | glm-4-plus | 需要理解需求、生成推荐话术 |
| SSE 事件格式 | 与前端 API 规范对齐 | 前后端一致，减少对接成本 |
| rating_avg | 从 user_reviews 动态计算 | 数据源中无此字段，需后端计算 |
| 认证提前到 M4a | 所有 API 依赖 user_id | 避免后期 mock user_id 再大改 |
| Agent 层集中做 | M5 整周专注 Agent | Router + 3 个 Agent + 工具是一个整体，拆开做增加集成成本 |
| API 成本追踪 | ZhipuClient 内置调用记录 | 监控智谱 API 用量，防止超支 |

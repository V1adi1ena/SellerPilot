# 跨境电商卖家智能运营 Agent 平台技术方案

面向大三学生的六周开发与学习指南

版本 1.0　｜　编制日期 2026 年 10 月 8 日　｜　项目建议名 SellerPilot

## 阅读说明

这份方案帮助具有 Python 和 C++ 基础、尚未做过后端或 Agent 项目的学生，在 1 至 2 个月内完成一个可部署、可测试、可讲解的实习作品。推荐采用 Python 单体后端，围绕卖家运营完成四个闭环：导入业务数据、用自然语言查询订单与库存、引用政策资料回答问题、生成并确认运营动作。

参考项目 VIVPM/ecommerce-agent 是面向买家的鞋类购物助手。SellerPilot 是本方案提出的卖家平台，两者的用户、数据和动作不同。第 1 章描述已核实的参考代码；第 2 章起均为建议设计，不代表原仓库已具备这些能力。所有性能阈值、质量目标和工时均为规划值，只有按第 11 章实测后才能用于成果表述。

计划按每周 20 至 25 小时、六周约 130 小时安排，其中已包含学习、联调和缓冲。每天只能投入 1 至 2 小时时，应采用第 14 章缩减版并调整周期；标准版约需 10 至 19 周。第 4 周形成可展示版本即可开始投递，第 5 至 6 周继续补齐质量与部署。

建议阅读顺序：先读第 2、3、12、14 章确定范围，再按周学习与实现；设计接口时查第 5 至 10 章；投递前用第 11、15 章验收和准备讲解。

## 目录

1. 参考仓库核查与复用边界
2. 产品定位与 MVP 范围
3. 技术栈与选型理由
4. 系统架构与工程组织
5. 数据来源与业务计算口径
6. 数据模型与数据库约束
7. API 与流式协议
8. Agent 编排与工具实现
9. RAG 知识库设计
10. 安全与可靠性设计
11. 测试评测与最终验收
12. 六周开发计划与阶段验收
13. 从零学习路线与资料
14. MVP 裁剪与延期处理
15. 部署交付与简历表达
16. 参考来源与启动清单

## 1 参考仓库核查与复用边界

### 1.1 核查基线

仓库地址：https://github.com/VIVPM/ecommerce-agent

本次读取的提交为 8b37e2899ccc6ea74e79a8280b6184fe14114018。可用该 SHA 固定代码版本，避免之后 README 或默认分支变动造成对照失效。核查依据包括依赖清单、后端入口、数据库模块、工具模块、前端代码、Docker 配置和 CI 工作流，而非仅依据项目介绍。[R1 至 R10]

本次实际执行了无需网络和业务服务的 tests/test_logging.py，结果通过。未运行需要模型密钥、Neon 数据库和 Pinecone 的完整应用、线上评测或负载测试，因此不将仓库报告的性能、云服务状态视作本次复现结果。

### 1.2 实际技术栈

| 层次 | 已核实实现 | 代码依据 |
| --- | --- | --- |
| 前端 | React 19.2、Vite 7.3 系列，JavaScript JSX，Axios、react-markdown、lucide-react | frontend/package.json |
| HTTP 服务 | FastAPI、Uvicorn，Pydantic 模型和校验器，SlowAPI 限流 | backend/requirements.txt；backend/main.py |
| 数据库 | SQLAlchemy 同步引擎和 Session，psycopg2 驱动，PostgreSQL；配置指向 Neon 的方式在 README 说明 | app/db/database.py；README.md |
| 生成模型 | google-genai，代码默认生成模型 gemini-2.5-flash，SQL 配置 Pro 回退；可切换 Cloudflare gpt-oss | app/llm_provider.py；app/sql.py |
| 知识检索 | Pinecone，gemini-embedding-001，输出 1024 维，FAQ 检索 top_k=4 | app/faq.py |
| Agent | Gemini 工具调用选择路由，应用显式执行工具；支持会话、复合意图拆分和领域过滤 | app/agent.py；main.py |
| 身份认证 | python-jose JWT、bcrypt；前端 sessionStorage 保存令牌 | main.py；frontend/src/api.js |
| 记忆与缓存 | 短期查询改写、PostgreSQL 偏好和缓存；Supermemory 为可选长期记忆 | memory.py；memory_store.py；cache.py |
| 监控与交付 | JSON 日志、可选 OpenTelemetry、Langfuse／Grafana；Docker、GitHub Actions、Render 部署钩子 | observability.py；Dockerfile；ci.yml |

版本说明：后端很多依赖没有固定版本，依赖表不能视为可精确复现的完整锁文件。LangChain 相关包被列入 requirements.txt，但主 Agent 路由是手写代码；faq.py 使用了 LangChain Document，并不等于项目采用 LangGraph、多 Agent 框架或完整 LangChain Agent Executor。[R2 至 R5]

### 1.3 请求链路与真实功能

POST /api/chats/{chat_id}/message 校验登录和消息额度后，进入 SSE 流。请求路径可包含图像转查询、领域判断、历史查询改写、长期记忆召回、复合意图拆分、模型工具路由，再调用商品 SQL 检索、FAQ、收藏比较、购物车／模拟订单或偏好工具。同步工作通过 asyncio.to_thread 转移；最终保存用户与助手消息。[R3、R4]

商品数据来自 Flipkart 鞋类目录。sql.py 让模型生成查询，run_query 对开头 SELECT 做初步判断，再经只读连接执行。faq.py 将 FAQ 问题向量化，检索固定 namespace 的候选答案，再由模型生成回复。购物车和下单／取消是确定性数据库操作，订单明确标注模拟，不包含真实支付与履约。[R4 至 R7]

项目还有图片找鞋、商品发现与刷新脚本、用户自带 Gemini 密钥、商品收藏价格变化、会话管理等实现。这些是参考项目的能力，不是六周卖家 MVP 必须复刻的清单。

### 1.4 README 与代码需要区别对待

| 项目说法或容易产生的误解 | 源码核查结果 | 仿作决策 |
| --- | --- | --- |
| 配好 Docker 就完全离线运行 | compose 只启动 API 与前端，数据库和向量库仍远程依赖 | 新项目本地 Compose 自带 PostgreSQL 与 pgvector |
| SQL 只读即充分安全 | 只读引擎使用相同 DATABASE_URL；SELECT 前缀检查不是完整 SQL 解析或租户授权 | MVP 使用白名单业务工具和参数化查询 |
| 聊天写入有行锁 | 当前 _save 写独立消息行；没有发现对应的 with_for_update，README 描述不能直接当证据 | 显式设计会话单运行约束及事务 |
| LLM_MODEL 默认可省略 | llm_provider.py 当前在变量缺失时直接报错，注释／README 默认值不能代替代码 | 启动前做配置校验，提供 .env.example |
| 测得路由准确率 100% | 仓库保存了 200 题结果；评测脚本由 LLM 根据回答判路由，没有直接比对执行轨迹 | 新评测记录实际 tool_name，另评答案质量 |
| CI 覆盖完整后端行为 | 后端 CI 执行 Ruff、语法检查、日志测试；前端构建、镜像构建另有任务 | 新增数据库、鉴权、幂等与 Agent 回归测试 |
| 已有跨境卖家平台 | 当前核心是鞋类买家助手，没有本方案的卖家库存分析与审批动作链 | 重新建立领域模型，复用工程思路 |

评测数字可在学习笔记中标为“作者报告”，不要放进自己的简历。README 也提示部分评分早于当前路由与工具结构。本次不对参考项目作生产安全认证；上述发现主要用于选取学习重点。[R3、R5、R8、R9]

### 1.5 推荐阅读顺序

第一遍读 frontend/src/api.js 与 main.py 的认证和聊天入口，画出一次请求的路径；第二遍读 agent.py 与 llm_provider.py，确认“模型返回工具选择”和“应用执行工具”之间的区别；第三遍读 sql.py 与 faq.py，分别理解结构化数据查询和文档检索；最后读模型、缓存、日志、CI 与 Docker。

不要从复制整个 main.py 开始。先用自己的表实现一个普通订单接口，再把接口背后的业务函数注册为 Agent 工具。参考项目采用 MIT 许可证；若复制代码，需要保留原版权与许可声明，并在 README 标明借鉴来源。独立实现的部分也应明确列出。[R10]

## 2 产品定位与 MVP 范围

### 2.1 用户与问题

目标用户是经营一个海外站点的小型跨境电商卖家。其常见工作是检查销量和库存、定位异常订单、查店铺运营政策、整理英文商品文案。项目用演示数据模拟这些工作，不接真实平台账号即可验证后端与 Agent 能力。

MVP 支持两名演示卖家，每名卖家一个独立店铺，模拟美国站点与 USD 结算。服务端仍将 store_id 作为权限边界；另设一个不同站点／币种的测试店铺，用于验证数据不会混算。用户界面以中文为主，商品内容允许英文。

建议承诺：卖家可以上传数据，通过对话获得可复核的经营事实和有来源的政策答案，并将运营建议保存为可审批的模拟任务。不要承诺真实销售提升、自动完成报关或全渠道自动运营。

### 2.2 四个必须完成的用户故事

| 用户故事 | 输入与操作 | 可观察产出 |
| --- | --- | --- |
| 导入数据 | 登录后上传商品、订单与库存 CSV | 显示校验结果、成功行数、失败行和数据版本 |
| 查询运营事实 | “过去 7 个自然日销量最高的 5 个 SKU 是什么” | 参数化工具返回数字、币种、时间范围与数据更新时间 |
| 查询政策 | “这份店铺规则怎样处理未发货订单” | 回答包含文档名、版本、章节和原文片段链接 |
| 形成运营动作 | “给 SKU A 生成英文标题并保存草稿” | 展示修改前后；卖家点击确认后更新模拟 listing 并记审计 |

库存风险分析是运营查询的一部分：返回可售天数和补货建议量。英文 listing 草稿是第 5 周的动作载体；只修改本地模拟记录，不向任何电商平台发布。

### 2.3 优先级与页面

P0 为登录、店铺权限、CSV 导入、业务查询工具、政策 RAG、聊天记录、SSE、审批与审计、离线测试、可复现部署。P1 为英文 listing、库存预警列表与简易报表。P2 为自动日报、更多站点、真实平台连接、混合检索、LangGraph、分布式任务和更完整的监控。

前端保持四页：登录页；数据页展示导入和最近版本；运营对话页展示答案、引用和工具状态；任务页展示待确认、成功与失败动作。库存表可放进数据页，不单独建设复杂 BI 大屏。第 1 至 3 周用 Swagger UI 和最小页面即可联调。

### 2.4 完整演示案例

卖家上传 60 天演示数据，问“美国店铺过去 7 天哪些 SKU 可能断货”。服务端固定店铺和日期口径，模型选择库存风险工具，数据库计算结果。用户再问“给风险最高的 SKU 起一个英文标题”，系统读取已验证商品属性生成草稿。确认页面展示商品、原标题、新标题、数据版本、影响范围和“本地模拟”标识。用户点击确认后数据库更新一次并留审计；第二次点击返回同一结果。任何一步缺少店铺、SKU 或资料时，系统应追问或报明确信息不足。

## 3 技术栈与选型理由

### 3.1 六周内的建议组合

| 组件 | 建议技术 | 学到的能力与取舍 |
| --- | --- | --- |
| 语言与依赖 | Python 3.12，uv 或 venv 加锁定依赖 | 使用已有 Python 基础，避免同时学习新的后端语言 |
| API 与校验 | FastAPI、Uvicorn、Pydantic v2、pydantic-settings | HTTP、依赖注入、类型校验、OpenAPI、配置管理 |
| 关系数据库 | PostgreSQL 17、SQLAlchemy 2、psycopg 3、Alembic | 表结构、事务、索引、迁移和参数化查询 |
| 向量检索 | 同一 PostgreSQL 的 pgvector 扩展 | 减少一个远程服务；小语料先精确检索 |
| 模型层 | 可替换 Provider，首个只接一种可访问的工具调用模型 | 先做密钥／网络／工具调用试验，型号通过配置指定 |
| Embedding | 一种支持中英文且可稳定调用的模型 | 明确维度与版本，重建索引流程；不随生成模型一起切换 |
| 编排 | 手写有界工具循环、Pydantic 工具参数模型 | 理解 Agent 的执行机制；LangGraph 留作增强 |
| 前端 | React、Vite、TypeScript、fetch 流读取；组件库按需 | 只实现业务必需页面，控制前端学习成本 |
| 测试与规范 | pytest、HTTPX、Ruff；Playwright 可选 | 普通后端测试和 Agent 行为评测分开 |
| 交付 | Docker Compose、Nginx、GitHub Actions | 一键启动、反向代理、持续集成、配置与持久化 |
| 可观测性 | JSON 日志、request_id、agent_run 记录 | 先定位错误与统计耗时；云监控按需要再接 |

推荐组合是设计选择，不是原仓库技术清单。FastAPI、SQLAlchemy、Alembic 与 pgvector 的官方材料见 [D1 至 D4]。开工时固定经验证的一组具体版本和容器镜像；这里的版本线是起点，不等于声称它们都是最新版本。

### 3.2 同步与异步的明确边界

数据库先用同步 SQLAlchemy Session，普通接口用 def 路由。聊天流用 async def，模型与 HTTP 请求尽量使用异步客户端；同步检索或数据库函数用 asyncio.to_thread 包装，并在该函数内部创建和关闭 Session。不要跨线程共享 Session，也不要在 async 路由内直接执行长时间同步调用。

不要一开始同时学习 async SQLAlchemy、复杂任务队列和微服务。若后续改成异步数据库，应完整替换会话生命周期与驱动，并补并发测试，不只改函数名。

### 3.3 可替换 Provider 与服务降级

Provider 接口至少支持 generate_structured、stream_answer、embed；返回统一的 text、tool_calls、usage、finish_reason。默认 Provider 在启动阶段做一次小型能力验证，确认 schema、工具选择、中文、流式和超时可用。可以学习参考仓库的 Gemini 接入，也可使用自己已拥有额度的其他服务。具体模型可用性、价格和地区条件在开工时验证，不将仓库中的旧型号直接当作当前推荐。

保留 MockProvider：固定输入返回固定工具选择和答案，供测试与断网演示使用，界面注明“模拟模型模式”。真实模型不可用时，数据页、查询 API 和历史记录仍可用；禁止悄悄把假答案伪装成真实模型结果。Embedding 故障时返回知识库暂不可检索，不能用生成模型补造政策。

### 3.4 预算与资源假设

先设个人可承受的开发预算，例如整个项目模型费用上限人民币 100 元、总费用上限 200 元；这些是个人预算示例，不是服务商报价。单次调用成本按输入 tokens × 输入单价 + 输出 tokens × 输出单价 + embedding 成本计算，再换算币种。采购前查当前官方计价，免费额度不作为项目可运行的前提。

每天设置请求数和 token 额度、单次最大输出、最大工具次数；记录 usage 和实际账单。个人电脑优先运行 Docker 与远程模型，不训练大模型。部署资源从一台 2 核 4GB 的测试服务器起步，容量须压测验证；不要承诺生产高并发。

## 4 系统架构与工程组织

### 4.1 模块化单体

建议架构是一个 API 服务加一个数据库，所有业务规则均在后端执行。RAG 索引任务由独立 CLI 命令触发，避免为了少量文档引入任务集群。架构图中的箭头表示主要调用或数据访问方向。

```text
浏览器 React
    | HTTPS  REST 与 SSE
    v
Nginx  静态页面与反向代理
    |
    v
FastAPI
    |-- 认证与店铺权限 -- 数据导入 -- 查询 API
    |-- Agent 编排 -- 参数校验 -- 工具注册表
    |       |-- 订单分析与库存计算
    |       |-- RAG 检索与引用校验
    |       |-- 草稿与动作审批
    |-- 日志与审计
    |              |
    v              v
PostgreSQL     模型 Provider
业务表         文本生成与 embedding
pgvector

独立索引 CLI -- 解析与切分 -- embedding -- 知识表
```

### 4.2 一次经营查询的数据流

1. 前端提交 chat_id、store_id、message 和 client_request_id。
2. 后端从令牌确认用户，再从 membership 判断店铺权限；不信任模型或请求中的 user_id。
3. 新建 agent_run 与用户消息，短事务提交。通过唯一约束阻止同会话同时运行两条请求。
4. 加载有限历史与店铺配置，模型给出工具名和参数。
5. 服务端白名单校验参数，把已授权 store_id 注入执行上下文，调用业务函数。
6. 工具返回数值、时间区间、币种、数据版本和证据；模型生成说明，确定性结果组件展示原始数值。
7. SSE 推送状态、答案和引用；先保存最终消息与运行结果，再发 done。

外部模型调用时不持有数据库行锁或长事务。执行异常要将 run 标记为 failed 或 cancelled，并释放会话运行限制。

### 4.3 建议目录

```text
sellerpilot/
  backend/
    app/
      main.py        配置与路由挂载
      api/           auth stores imports chats actions
      schemas/       HTTP 与工具参数模型
      models/        SQLAlchemy 表
      services/      imports analytics inventory actions
      repositories/  带店铺条件的数据库访问
      agent/         runner registry prompts providers
      rag/           ingest split retrieve citations
      core/          auth settings errors logging
    migrations/      Alembic 版本记录
    tests/           unit integration agent security
  frontend/src/      pages components api
  data/demo/         两租户演示数据与标准答案
  evals/             cases.jsonl 与评测输出
  scripts/           seed ingest backup smoke
  docs/              架构 API 评测与演示说明
  compose.yaml
  .env.example
  README.md
```

路由只处理协议和依赖，service 执行业务规则，repository 负责数据库查询，Agent 通过工具调用 service。一个工具应能被普通 HTTP 接口和测试直接调用；业务能力不应只能通过聊天使用。

## 5 数据来源与业务计算口径

### 5.1 演示数据优先

用固定随机种子生成两个卖家、各一个店铺、每店 100 个 SKU、60 天约 3000 笔订单及明细、当前库存快照。安排可验证的边界：零销量 SKU、取消订单、退款、缺失成本、负库存非法行、同名 SKU 分属不同店铺。另备少量人工构造的精确答案，不能只依赖随机数据。

政策知识库采用自己编写的演示店铺 SOP，明确标为“演示店铺政策”，覆盖发货、取消、退货和 listing 内容规范。若引用真实平台文档，保存原始链接、获取日期、站点、适用范围和文档版本；问答只反映已收录资料，不保证实时规则。不要编造 Amazon／Shopify 的政策或宣称已接其真实 API。

MVP 不需要爬虫。CSV 可以代表平台导出的数据，不需要真买家姓名、地址、邮箱或支付信息。对外演示仅使用合成数据。

### 5.2 CSV 合同

| 文件 | 必需列 | 校验与幂等方式 |
| --- | --- | --- |
| products.csv | sku,title,currency,price,cost,lead_time_days | sku 店内唯一；price 非负；cost 可空；币种须匹配店铺 |
| orders.csv | external_order_id,ordered_at,status,currency | 订单号店内唯一；时间必须含偏移；状态采用枚举 |
| order_items.csv | external_order_id,line_no,sku,quantity,unit_price,refund_amount | 订单和商品须存在；数量正数；退款不超过该行成交额 |
| inventory.csv | sku,on_hand,reserved,as_of | 数量非负；reserved 不大于 on_hand；同店同 SKU 同时间唯一 |

单文件默认上限 5MB、10000 行、UTF-8；错误返回行号、字段和原因。导入顺序是商品、订单、明细、库存。小文件采用整文件原子提交，任何行错误都不写入，修复后重试；不实现容易造成部分数据混乱的静默跳过。

导入先校验，再事务 upsert，成功后增加 stores.data_version。文件 SHA-256 与 store_id、kind 构成去重键；相同文件重传返回原结果。不同文件中重复业务主键按版本规则更新，过时库存快照不覆盖较新快照。金额和数量不可由模型直接清洗或猜测。

### 5.3 指标定义

“过去 7 天”默认指店铺时区最近 7 个完整自然日，不含尚未结束的今天。服务端先按店铺时区得到边界，再转 UTC 查询，区间采用 [start,end)。答案显示本地日期、时区、状态过滤和最新数据时间。若用户要包含今天，应明确展示未完整日的口径。

商品销量是区间内状态为 paid 或 shipped 的订单明细数量之和；cancelled 和 pending 不计入。销售额是这些行 quantity × unit_price 之和，净销售额再减已记录退款。MVP 退款为金额，不推断退货数量或回补库存。多订单 join 应防止重复聚合。

可售库存 = on_hand - reserved。日均销量 = 同 SKU 最近 14 个完整自然日的有效销量 ÷ 14。可售天数 = 可售库存 ÷ 日均销量；日均为 0 时显示“无近期销量，无法估算”，不输出无穷大。缺少库存或数据不足 14 天时显示缺失或按实际天数计算并标注观察窗口。

缺货风险判定为可售天数 < lead_time_days + safety_days。建议补货量 = max(0, ceil(日均销量 × (lead_time_days + safety_days) - 可售库存))。例如 14 天销量 140、库存 35、在途暂不计、提前期 5 天、安全天数 2，则日均 10、可售天数 3.5、建议补货 35。这是可解释规则，不能包装成机器学习预测。

MVP 只计算已知商品成本对应的商品毛利，不计算真实净利润。缺成本时返回未知；运费、广告费、税费未建模必须在页面标出。不同币种分别聚合，不把 USD 与 EUR 直接相加；汇率与税务规则留待后续模块。

## 6 数据模型与数据库约束

### 6.1 关系与类型约定

user 通过 membership 访问 store。store 拥有商品、订单、库存、文档、会话与动作。order 包含多条 order_item；document 包含多个 chunk；chat 包含 message 与 agent_run；action 引用生成它的 agent_run，audit_event 记录确认和执行行为。

主键统一 UUID；金额为 NUMERIC(18,2)，Python 端用 Decimal，JSON 中用十进制字符串；时间为 TIMESTAMPTZ，统一 UTC 保存。币种存 ISO 三字母代码。SKU 与平台订单号是业务标识，不能替代全局主键。所有含业务内容的表必须带 store_id，导入、检索、缓存和历史访问均应用同一权限边界。

### 6.2 核心表字段

| 表 | 关键字段 | 关键约束或索引 |
| --- | --- | --- |
| users | id,email,password_hash,created_at | email 唯一；禁止保存明文密码 |
| stores | id,name,marketplace,region,currency,timezone,data_version | timezone 保存 IANA 名称；MVP marketplace=demo |
| memberships | user_id,store_id,role | 联合主键；role=owner 或 viewer |
| products | id,store_id,sku,title,currency,price,cost,lead_time_days,version | UNIQUE(store_id,sku)；price 与 cost 非负 |
| orders | id,store_id,external_order_id,status,currency,ordered_at | UNIQUE(store_id,external_order_id)；索引(store_id,ordered_at) |
| order_items | id,store_id,order_id,line_no,product_id,quantity,unit_price,refund_amount | UNIQUE(order_id,line_no)；数量正数；金额非负 |
| inventory_snapshots | id,store_id,product_id,on_hand,reserved,as_of | UNIQUE(store_id,product_id,as_of)；库存合法性 CHECK |
| import_jobs | id,store_id,kind,file_hash,status,row_count,error_summary,created_by | UNIQUE(store_id,kind,file_hash) |
| documents | id,store_id,title,version,region,source_url,content_hash,status,effective_at | UNIQUE(store_id,content_hash,version)；status=staging/active/retired |
| chunks | id,store_id,document_id,chunk_no,text,section,embedding,embedding_version | UNIQUE(document_id,chunk_no)；固定向量维度 |
| chats | id,store_id,user_id,title,created_at | 访问时同时核验店铺和用户 |
| messages | id,store_id,chat_id,run_id,role,content,created_at | 索引(chat_id,created_at,id)；用户消息引用 request 去重 |
| agent_runs | id,store_id,chat_id,client_request_id,status,tool_trace,usage,error_code | UNIQUE(chat_id,client_request_id)；运行状态部分唯一索引 |
| actions | id,store_id,run_id,type,payload,payload_hash,status,base_version,expires_at,created_by | 持久化审批状态；确认时比对版本和内容哈希 |
| action_executions | id,store_id,action_id,idempotency_key,result,created_at | UNIQUE(action_id)；UNIQUE(store_id,idempotency_key) |
| audit_events | id,store_id,actor_id,event_type,target_id,before_after,request_id,created_at | 仅服务端写；敏感值脱敏；按店铺和时间检索 |

tool_trace 记录工具名、脱敏参数、结果状态和耗时，可用 JSONB，不保存模型隐藏推理。MVP 不单独建立 tool_call 表；查询需求增长后再拆分。messages 的最终助手记录还应满足同 run 唯一，防止重试造成重复答案。

### 6.3 防止跨店铺外键错误

只加 store_id 字段不等于完成隔离。给父表建立 UNIQUE(store_id,id)，在 order_items、inventory_snapshots、chunks 等表使用 (store_id,父对象 id) 的复合外键，确保一个店铺的明细不能引用另一个店铺的商品或订单。repository 查询也必须显式加 store_id 条件。

权限校验在 API 与工具 service 共用的授权函数完成，不能只在前端隐藏按钮。后续可研究 PostgreSQL RLS，但 MVP 的主保障是统一权限入口、复合约束和跨租户测试。

### 6.4 事务与迁移

用 Alembic 管理建表、CHECK、复合外键、索引和 pgvector 扩展，初始迁移与种子数据分离。生产启动不调用 create_all 代替迁移。每次变更测试空库升级和已有数据升级，迁移前备份。

索引优先覆盖 orders(store_id,ordered_at)、products(store_id,sku)、inventory_snapshots(store_id,product_id,as_of DESC)、messages(chat_id,created_at)。小型知识库先执行带 store_id 过滤的精确向量搜索；达到明显延迟瓶颈后才加 HNSW，并验证过滤后召回率，不能仅展示创建了向量索引。[D4]

## 7 API 与流式协议

### 7.1 通用约定

前缀统一 /api/v1。除登录与存活检查外均需认证；store_id 放路径，后端查询 membership。列表默认 page_size=20，最多 100，采用 created_at 加 id 的游标；报表必须限制最大 90 天，参数排序字段只允许白名单。

普通成功响应为 {"data": ..., "request_id": "..."}。错误响应为 {"error":{"code":"...","message":"...","details":...},"request_id":"..."}。采用 401 未登录、403 无操作权限、404 对象不存在或不可见、409 状态／版本冲突、413 文件过大、422 参数错误、429 额度／限流、502 模型服务失败、504 超时。不要把服务商异常堆栈或 SQL 语句直接发给用户。

### 7.2 端点清单

| 方法与路径 | 用途 | 权限及关键行为 |
| --- | --- | --- |
| GET /health/live | 进程存活 | 不查外部模型 |
| GET /health/ready | 数据库与配置就绪 | 超时快速失败，不产生模型费用 |
| POST /auth/login | 获取登录状态 | 账户＋IP 限流；演示账号由 seed 创建 |
| POST /auth/logout | 清理登录状态 | MVP 无 refresh token，短期令牌到期失效 |
| GET /me/stores | 可访问店铺列表 | 仅当前用户 membership |
| POST /stores/{sid}/imports/{kind} | 上传业务 CSV | owner；multipart file；成功返回 201，重复返回 200 |
| GET /stores/{sid}/imports/{id} | 导入结果 | 当前店铺成员；错误明细限制条数 |
| GET /stores/{sid}/products | 商品列表 | sku 查询与游标分页 |
| GET /stores/{sid}/orders | 订单列表 | 状态、日期筛选 |
| GET /stores/{sid}/analytics/sales | 销量与销售额 | 固定口径；按币种返回 |
| GET /stores/{sid}/inventory/risks | 库存风险 | 日期窗口、安全天数与上限 |
| GET /stores/{sid}/documents | 文档与索引状态 | 成员；上传／索引由 CLI 完成 |
| GET /stores/{sid}/documents/{id}/chunks/{cid} | 展示引用原文 | 再核验店铺、版本与文档状态 |
| POST /stores/{sid}/chats | 创建会话 | 返回 chat_id |
| GET /stores/{sid}/chats/{cid}/messages | 会话历史 | 当前用户与店铺；游标分页 |
| POST /stores/{sid}/chats/{cid}/messages | 发送消息并接收 SSE | client_request_id 去重；同会话只允许一个运行 |
| GET /stores/{sid}/runs/{rid} | 断线后的运行状态 | 返回持久化状态与最终答案 |
| GET /stores/{sid}/actions | 待审批与历史动作 | 成员；按状态筛选 |
| POST /stores/{sid}/actions/{aid}/confirm | 确认并模拟执行 | owner；Idempotency-Key；版本与哈希校验 |
| POST /stores/{sid}/actions/{aid}/reject | 拒绝动作 | owner；只有 pending 可拒绝 |
| GET /stores/{sid}/audit-events | 动作审计 | owner；脱敏、分页 |

注册、团队邀请、密码找回、多角色管理和公开 SaaS 账号体系留待后续。MVP 至少提供两个互相隔离的账号，避免只有单用户而无法验证权限。

### 7.3 工具输入与结果示例

```json
{
  "message": "过去7个完整自然日销量最高的5个SKU",
  "client_request_id": "e7fae421-377c-4fc6-88e1-4d319b34e215"
}
```

模型可以提出日期和 top_k，但店铺 ID 从路径授权结果注入。工具结果建议统一为以下结构；示例数值为演示数据。

```json
{
  "ok": true,
  "tool": "get_sales_summary",
  "data": [{"sku": "SKU-A", "units": 140,
            "net_sales": "2800.00", "currency": "USD"}],
  "evidence": {"data_version": 8, "timezone": "America/Los_Angeles",
               "range_local": ["2026-10-01", "2026-10-08"],
               "included_statuses": ["paid", "shipped"]},
  "warnings": []
}
```

### 7.4 SSE 的可实现协议

采用 fetch POST 加 ReadableStream 读取 text/event-stream；浏览器原生 EventSource 通常用于 GET，无法直接满足此处 POST 请求体与自定义 Bearer 头需求。流解析必须处理一次读取中含多事件、单事件跨多个读取块、UTF-8 跨块、空行结束和 CRLF。[D10]

```text
event: run_started
data: {"run_id":"r1"}

event: tool_started
data: {"name":"get_inventory_risk"}

event: answer_delta
data: {"text":"SKU-A 的可售天数为 3.5 天。"}

event: citation
data: {"document_id":"d1","chunk_id":"c4","version":"v2"}

event: done
data: {"run_id":"r1","status":"completed","message_id":"m2"}
```

政策回答可以先生成并校验证据，再按段发送答案；无须为了“逐 token”牺牲引用正确性。异常发 event:error 并结束；HTTP 头已发出后不能再改 HTTP 状态。每 15 秒发注释心跳；Nginx 对流关闭缓冲与缓存，超时大于单次运行上限。

断线后前端先 GET run 状态，若已完成则加载消息；若被取消则展示重试按钮。相同 client_request_id 重发不触发新模型调用。MVP 不承诺按 Last-Event-ID 回放每个 token，只保证最终状态可查询。浏览器主动中止时取消后续模型调用，并记录 cancelled；极端进程中断由超时清理恢复。

## 8 Agent 编排与工具实现

### 8.1 先明确三个概念

LLM 负责理解意图和组织语言；工具是具有明确参数和返回值的业务函数；Agent 是在约束内选择并调用这些工具的执行流程。RAG 是从文档取证后回答的能力，可以成为 Agent 的一个工具。普通聊天页本身不足以证明完成了 Agent 工程。

MVP 采用“单 Agent 加多个业务工具”。流程是授权、补全上下文、选择工具、校验、执行、根据结果决定下一步、生成回答。有意限制最多 3 次工具调用和 4 次生成调用，避免无界循环；不要将多次调用包装成多个独立 Agent。

### 8.2 工具注册表

| 工具 | 参数核心 | 返回与约束 |
| --- | --- | --- |
| get_sales_summary | start,end,group_by,top_k | 确定性聚合；日期与维度白名单；top_k≤20 |
| get_order_status | external_order_id 或 status | 当前店铺订单；无结果明确返回，不猜物流 |
| get_inventory_risk | window_days,safety_days,sku | 计算口径、库存时间与建议量；只读 |
| search_policy | question,region | 带店铺／站点过滤的 chunk 与引用；无证据拒答 |
| propose_listing_update | sku,language,goal | 读取商品事实，生成草稿并创建 pending action |

确认与真正更新的 execute_listing_update 不向模型注册。模型可以创建提案，只有已登录用户通过 confirm API 才能触发执行。用于回答事实的工具不接受任意 SQL、文件路径、URL、shell 或 user_id。

### 8.3 编排伪代码

```python
async def run_agent(ctx, message):
    history = load_authorized_history(ctx, max_messages=8)
    messages = build_messages(message, history, ctx.store_config)
    for step in range(3):
        decision = await provider.decide(messages, tools=TOOL_SCHEMAS)
        if decision.needs_clarification:
            return clarification(decision.question)
        if not decision.tool_calls:
            return validate_answer(decision.answer, evidence=ctx.evidence)
        call = validate_single_call(decision.tool_calls)
        tool = registry.require_allowed(call.name)
        args = tool.schema.model_validate(call.arguments)
        result = await tool.execute(ctx, args)  # ctx 内含授权店铺
        record_trace(call.name, args, result)
        messages = append_result(messages, call.id, result)
    return bounded_summary_or_limit_message(messages)
```

这是控制流程示意，不是已经完成的可运行实现。采用何种 SDK 决定 tool_call_id 和模型消息结构的具体编码；必须保留调用与结果对应关系。每轮只执行一个工具，复合问题可顺序查两个工具后总结。第 3 周先只支持单工具，第二个工具和多轮能力在回归测试通过后加入。[D8]

### 8.4 上下文与模型输出

服务端加载最近 8 条已保存消息及最近一次选择的 SKU、日期范围；不让前端传入一份任意 history 作为可信历史。“这个商品”“再看上周”只在可唯一解析时补全，否则追问。对长工具结果最多传 20 行和汇总统计，避免 token 失控。

Prompt 约定回答包括事实、数据依据、建议及限制；数值来自工具，政策来自 chunk，缺失事实说未知。不要要求模型展示内部思考。tool_trace 展示工具选择、参数、耗时和结果摘要即可。

参数模型设置 extra='forbid'，数值使用边界校验，日期用确定格式。字段校验失败允许模型修正一次；第二次失败停止并给出可操作提示。领域过滤用于提升体验，不能承担权限或执行安全责任。凡授权失败、未知工具和审批无效均禁止执行。

### 8.5 为什么 MVP 不照搬 Text to SQL

经营指标只有少数固定维度，使用模型把自然语言映射为工具参数，后端再生成参数化 SQL，能明确限制店铺、时间、列名和资源。模型输出“删除所有商品”或恶意 WHERE 条件不会成为数据库语句。

若第 7 至 8 周研究 Text to SQL，应作为独立实验：仅开放只读报表视图，使用独立低权限数据库角色，采用 AST 解析允许单条 SELECT，拒绝不允许的函数／系统表，强制店铺范围、行数与 statement_timeout，并测试越权读取。只读事务能限制写入，但不能阻止敏感数据读取或昂贵查询；不能只检查 SQL 以 SELECT 开头。

## 9 RAG 知识库设计

### 9.1 摄取与版本

MVP 输入以 Markdown 和 UTF-8 文本为主，避免从扫描 PDF OCR 开始。每个文档元数据包含 store_id、title、region、version、effective_at、source_url、content_hash。先校验编码并去除无意义空白，再按标题／段落切分，每块初始 300 至 600 tokens，重叠 50 至 80 tokens。这些是实验起点，应按实际政策结构调整。

通过 CLI 创建 staging 文档，写入全部 chunk 和向量，核对数量与维度后事务切换为 active，同时退休旧版本。索引失败保留旧 active 版本，不让用户检索到半成品。同内容哈希与版本重复导入不重新计费；日志记录失败块便于重试。

Embedding 模型、维度、归一化方法和版本必须固定。切换模型后整库重建，新旧向量不能混用。对于支持 query／document task_type 的模型，应按官方要求区分，不能盲目复制参考仓库的同一 embedding 调用方式。[D9]

### 9.2 检索与回答

先校验店铺访问，按 store_id、region、active 版本过滤，再执行向量相似度检索。MVP 取 top_k=4 或 5；相似度阈值用开发集校准，没有跨模型通用的“0.8 必然相关”。小语料精确扫描更易验证，记录查询向量耗时和数据库检索耗时。[D4]

给模型的每段内容附 chunk_id、文档名、章节、版本和生效日期。回答要求用检索上下文作证据，并输出结构化 claim 与 citation_ids；服务端确认 citation_id 来自本次可访问候选集，去除无效引用。引用可访问且存在不等于完全支持结论，仍需在评测中人工核对“原文是否支持这句话”。

找不到相关政策、站点不匹配、资料冲突或用户询问未覆盖内容时，说明现有资料的覆盖范围并拒绝给出具体承诺。缺证据时的拒答是正确行为。对冲突版本优先使用当前 active 且适用的版本，不能随意选较有利的条款。

### 9.3 注入防护与缓存

文档原文可能包含“忽略指令”“发送密钥”等恶意内容。将检索片段标为数据，禁止其改变系统规则和调用权限；检索工具只读，模型不拥有执行入口。即使提示词失守，也应由服务端权限、工具白名单和人工确认限制影响。

优先不缓存完整业务答案。若缓存检索或政策答案，键至少包含 store_id、region、query、document_version、embedding_version、prompt_version；只缓存成功结果。业务统计缓存还需包含 data_version 和时间口径。不能沿用仅按问题文本生成的全局缓存去缓存租户私有答案。

### 9.4 最小 RAG 评测集

准备 40 道政策问题，其中 20 道开发集用于调参、20 道冻结验收集用于最终评测。覆盖准确表述、同义改写、多条件、站点差异、旧版本、无答案及注入。每道题由人工指定期望 chunk_id 和应答／拒答标签。分别统计 Recall@5、引用有效率、引用支持率和无答案拒答率，不能只用“回答看起来不错”作为验收。

## 10 安全与可靠性设计

### 10.1 鉴权与租户隔离

两账号默认由命令行生成。密码使用维护中的密码哈希库，优先 Argon2id；JWT 由服务端固定允许算法并校验 exp、sub、issuer 与 audience，签名密钥来自环境变量。演示访问令牌建议 30 分钟，无 refresh token，过期重新登录。

前端令牌先存内存，刷新重新登录，减少持久化复杂度；若日后换 HttpOnly Cookie，需要同时设计 Secure、SameSite 和 CSRF。登出清除前端令牌，MVP 已签发 JWT 到期前仍有效，这一限制必须记录。模型密钥不下发前端，日志不得记录 Authorization。

按 user_id、IP 和业务成本限流；单进程内存限流只作为演示版约束，多实例前需换共享存储。先部署单 API 进程，不把内存限流描述成分布式能力。

### 10.2 动作确认与幂等

动作状态为 pending → succeeded，或 pending → rejected／expired；执行失败后记 failed，是否允许重试由接口显式决定。创建时保存 payload_hash、商品 base_version、创建人和 24 小时有效期。确认页必须显示具体变更和模拟标识，聊天中的“好的”不直接触发执行。

confirm 先校验 owner 权限，再在短事务中锁定 action 行。优先检查已有 execution，合法重复请求直接返回原结果；新请求才校验 pending、有效期、payload_hash 与商品版本，更新 listing、递增版本、写 execution 和 audit 后提交。同 action 并发最多更新一次；相同 Idempotency-Key 绑定不同动作或内容返回 409；商品变化后要求重新生成提案。

此处“执行一次”仅指同一 PostgreSQL 事务内的模拟更新。未来真实平台 API 调用涉及外部副作用，应增加 outbox、重试与对账，不能凭一个数据库锁承诺跨系统 exactly once。

### 10.3 上传与输出安全

CSV 限制扩展名、字节数、行数、编码和字段长度，不将上传内容保存为可执行文件。导出表格时转义 =、+、-、@ 等可能触发公式的文本单元格。MVP 不支持任意 URL 抓取，避免新增 SSRF 面。

Markdown 渲染关闭原始 HTML，链接协议仅允许 http／https，并限制引用打开来源。上传文案视作不可信数据，不能让其覆盖系统提示词。用户的店铺权限、数据库凭据和审批结果都不得从模型输出读取。

### 10.4 超时与失败恢复

建议单次运行 60 秒、单次模型调用 20 秒、数据库查询 5 秒、最大结果 100 行，属于初始配置。对网络和 429 类可重试错误最多重试 2 次，指数退避加抖动；配合整体截止时间，不能每次重试都重新获得 60 秒。参数错误、权限错误和本地写入不自动重复执行。

同步函数在线程中运行时，取消 await 不一定立即终止底层线程，因此数据库 statement_timeout 和客户端超时仍然必要。每段数据库操作结束立即关闭 Session；客户端断开后停止新的工具调用。

服务启动时将超过截止时间仍 running 的记录标记 interrupted。用部分唯一索引防同 chat 多个 running；接收新请求时先清理该会话过期运行。数据库失败时不发 done 成功事件，模型失败时不写“执行成功”审计。

### 10.5 最小威胁与验证矩阵

| 风险 | 服务端控制 | 必测反例 |
| --- | --- | --- |
| 越权读店铺数据 | membership 与 repository 条件、复合外键 | A 账号访问 B 的订单、chunk、run 和 action |
| 提示注入 | 文档作为数据、工具白名单、执行不注册给模型 | 原文要求改价格或泄露密钥 |
| SQL 注入 | 固定查询、参数绑定、列名枚举 | sku 中带引号与 SQL 片段 |
| 重复执行 | 事务、行锁、执行唯一约束、版本校验 | 同 action 同时确认 10 次 |
| 伪造审批 | 确认 API 鉴权、状态与哈希核验 | viewer／其他店铺 owner 确认 |
| 无限调用与费用 | 调用步数、token／每日额度和超时 | 循环选择同工具、长输入、模型 429 |
| 敏感信息泄露 | 脱敏日志、无真实买家数据、密钥环境化 | 检查日志、错误体、前端构建文件 |

OWASP 的 LLM 应用风险材料用于建立测试思路；本方案的安全验收以实际用例和服务端行为为依据。[D11]

## 11 测试评测与最终验收

### 11.1 测试分层

单元测试验证计算函数、日期边界、CSV 规则、参数模型和状态机。集成测试连接临时 PostgreSQL 验证迁移、复合外键、租户隔离、事务回滚、唯一约束与向量检索，不能用 SQLite 代替这些数据库特性。API 测试通过 HTTPX 调用应用，模型替换为 MockProvider。

端到端至少走通登录、上传、提问、打开引用、确认动作和重复确认，可以手工录制验收过程；若时间允许再用 Playwright 自动化。真实模型评测单独运行，不让每次提交都付费，也不让外部网络波动导致普通 CI 无法完成。[D6]

### 11.2 固定数据与边界用例

至少准备以下可精确断言的情况：跨夏令时自然日查询；边界时间恰等于 start／end；取消订单不计销量；一订单多个明细不被重复加总；部分退款只影响净销售额；缺成本不算利润；零销量不除零；库存快照重复上传；CSV 错误整批回滚；租户 A 和 B SKU 同名；引用旧版本失效；审批前商品版本变化；SSE 半途断开与请求重放。

测试数量不是目标。关键是每个 P0 失败路径都有可重复验证。可把核心 service 与权限模块语句覆盖率 80% 作为检查目标，同时报告未覆盖分支，不以覆盖率代替业务断言。

### 11.3 Agent 冻结评测集

建议建立额外 100 道冻结验收题，不用来改提示词：经营查询 30、库存分析 20、政策 20、动作提案 10、越权／注入／缺参数／超时等边界 20。第 9 章的 20 道 RAG 冻结题可复用为其中政策题；开发题另存，最终报告避免重复计数。

每条记录含 id、输入、店铺、固定时间、预期工具及参数、数值标准答案、应引用 chunk、是否该拒答。运行保存 commit、数据版本、prompt 版本、模型标识、温度、token、工具轨迹、错误与耗时。权限类断言靠代码与数据库，不能交给 LLM 裁判。

| 指标 | 计算方式 | MVP 目标 |
| --- | --- | --- |
| 工具选择正确率 | 实际轨迹命中预期工具／需要工具的题数 | ≥90% |
| 经营事实正确率 | 工具结果数值与标准答案完全相符／可回答经营题数 | ≥95% |
| 参数正确率 | 日期、SKU、top_k 等关键参数正确／调用题数 | ≥90% |
| RAG Recall@5 | 前 5 个候选含人工标注证据的可回答题／可回答政策题数 | ≥85% |
| 引用有效率 | 引用属于本次授权候选且可打开／引用总数 | 100% |
| 引用支持率 | 原文实际支持对应主张／抽查主张数 | ≥90%，人工复核 |
| 无答案拒答率 | 正确拒答的无答案题／无答案题数 | ≥90% |
| 租户与确认安全 | 预定安全用例无越权／无未授权执行 | 全部通过 |

报告同时列出分子、分母、错误和无法评分数量，模型异常计失败或独立列明，不能从分母悄悄剔除。小样本指标仅证明该测试集表现；真实模型题至少选 20 道再跑一次观察稳定性。LLM 评分只作辅助，人工核对所有失败题和至少 20 道随机成功题。

### 11.4 性能与可靠性目标

先分开测普通 API 与真实模型。参考环境为本地或测试服务器 2 核 4GB、数据库同机、每店约 3000 笔订单；记录 CPU、内存、连接池、版本、热身、时长和实际硬件。MockProvider 下并发 10、持续 5 分钟，普通读 API p95 目标小于 500ms、非预期限流的错误率小于 1%。这不能用于宣称真实模型并发能力。

真实模型选 30 次代表请求并发 2，记录首次状态事件、首个答案内容、完整结束的 p50／p95。首个状态事件可在 1 秒内，首个有内容答案目标 p95 小于 10 秒、完整请求目标 p95 小于 30 秒；超出后优先减少模型调用、缩短上下文、优化查询，不虚构测量结果。RAG 校验后才发答案时，单独报告等待时间。

对 actions 做 10 个并发重复确认，期望一个 execution、一条商品更新和可解释的其余响应。对相同 client_request_id 重放，期望只有一个 run。连接池总容量按进程数计算，避免多进程把数据库连接用尽。

### 11.5 最终交付验收

1. 新环境按 README 可从空数据库完成构建、迁移、种子导入与启动，演示密钥和真实密钥分开。
2. 两账号店铺隔离测试全部通过，工具和引用接口不能绕过授权。
3. 四个用户故事可完整演示；每个数字附口径，每条政策主张可追溯来源。
4. 模拟动作经显式确认、版本校验与幂等处理，有可查询审计。
5. CI 检查通过，冻结评测有结果、失败分析、硬件与模型信息。
6. 项目提供可访问演示或录屏、架构图、API 文档、部署说明与限制清单。

## 12 六周开发计划与阶段验收

### 12.1 总体节奏

| 周 | 主要目标 | 学习与实现时间 | 核心交付 |
| --- | --- | --- | --- |
| 第 1 周 | 能独立写和解释普通后端 | 约 22 小时 | API 骨架、认证、数据库、迁移 |
| 第 2 周 | 经营数据可导入与计算 | 约 22 小时 | CSV、查询工具、确定性标准答案 |
| 第 3 周 | 自然语言可安全调用工具 | 约 22 小时 | Provider、Agent、会话、SSE |
| 第 4 周 | 政策可检索并附引用 | 约 22 小时 | RAG、引用页面、首个展示版本 |
| 第 5 周 | 动作闭环与可靠性 | 约 22 小时 | listing 草稿、确认、审计、并发测试 |
| 第 6 周 | 可交付与投递 | 约 20 小时 | 部署、评测报告、录屏、简历材料 |

每周约 5 天学习与实现、1 天联调验收、半天复盘缓冲。卡住超过半天先写最小复现、查官方资料和缩小问题；不能用未经理解的大段生成代码跨过验收。学习比例前两周约 40%，之后约 20%，剩余时间用于实现和验证。

### 12.2 第 1 周 后端基础与权限骨架

第 1 天学习 HTTP 方法、JSON、状态码、请求／响应和 Git 基本操作；建立仓库、Python 环境、最小 /health 与一个 Pydantic 请求模型。第 2 天练习 FastAPI 参数、路由、Depends 和错误处理，实现一个内存商品 CRUD。第 3 天学习 SQL 的 SELECT、JOIN、GROUP BY、主外键和事务，启动 PostgreSQL，写首个 SQLAlchemy 模型。第 4 天加入 Alembic，创建 users、stores、memberships 和 products，seed 两账号。第 5 天实现登录、短期令牌和统一店铺授权。第 6 天做 API 联调、跨店铺反例测试，写启动 README；余量用于修正环境问题。

验收 G1：空库可迁移；两账号能登录；未登录 401；A 无法访问 B 的店铺商品；能解释一次请求从路由到数据库的路径。产物为 tag v0.1、迁移文件、接口截图和不少于五个有意义的鉴权／输入测试。未通过 G1 不开始接模型。

### 12.3 第 2 周 数据导入与经营工具

第 1 至 2 天建订单、明细与库存表，生成固定演示数据并手写小样本标准答案。第 3 天实现 CSV 预校验、导入事务、哈希去重和错误行报告。第 4 天实现销售汇总和订单查询，验证取消、退款和日期边界。第 5 天完成库存风险计算，把每个 service 同时暴露成普通 API。第 6 天完善数据页和单元／数据库集成测试。

验收 G2：四类 CSV 可按顺序导入；相同文件不重复入库；非法文件整批不写；数据版本递增；关键指标与手算样本相符；金额与日期没有模糊口径。产物为 tag v0.2、数据说明、接口示例和核心业务测试。模型尚未接入也应能展示业务价值。

### 12.4 第 3 周 Agent 与流式聊天

第 1 天使用 Provider 完成一次结构化工具选择试验，建立 MockProvider。第 2 天实现工具参数 schema、注册表和服务端权限注入。第 3 天实现单工具循环，再加入最大步骤、超时和澄清。第 4 天接聊天表、run 状态与请求去重。第 5 天完成 SSE 与最小对话页面；第 6 天用 20 道开发题检查路由、参数和缺数据回答。

验收 G3：同一经营问题既能通过 API 查询，也能通过自然语言得到一致结果；缺 SKU 会追问；未知工具不执行；同会话并发请求和重放可控；断线能查询最终 run 状态。产物为 tag v0.3、工具 schema、调用轨迹示例和 20 题开发报告。此时冻结 100 题验收集框架，后续补齐题目但不用于调参。

### 12.5 第 4 周 RAG 与首个展示版本

第 1 天学习 embedding、chunk、相似度与 RAG，编写演示 SOP。第 2 天写文档摄取 CLI、元数据和向量表，完成 staging 到 active 切换。第 3 天实现带租户／站点过滤的 top_k 检索。第 4 天接入政策工具和引用校验；第 5 天完成引用原文页与拒答。第 6 天用开发集调参，测试无答案、旧文档和注入。

验收 G4：政策答案可打开原文；A 的问题不会检索 B 的文档；更新文档不会出现半索引；未知规则拒答；工具与 RAG 在同一聊天中可使用。产物为 tag v0.4、3 分钟演示、RAG 开发报告。可以开始投递，注明动作确认仍在开发。

### 12.6 第 5 周 动作审批与可靠性

第 1 天用已知商品属性生成英文标题草稿，保存 pending action；第 2 天完成确认页面与拒绝动作。第 3 天实现 confirm 事务、版本校验、幂等记录和审计。第 4 天补租户、并发、过期、失败与注入测试。第 5 天完善日志、额度、超时、启动恢复和错误文案；第 6 天完成端到端演示。

验收 G5：模型不能直接执行更新；并发确认只修改一次；过期或商品版本变化返回明确冲突；viewer 与外店铺用户无法确认；日志不泄密。产物为 tag v0.5、审计截图、动作状态说明和并发测试结果。时间不足时只支持一个 action 类型，不扩展退款或广告操作。

### 12.7 第 6 周 部署评测与面试材料

第 1 天完善 Compose、环境变量和迁移命令；第 2 天打通 CI、数据库服务测试、镜像构建和前端构建。第 3 天部署测试环境并验证 HTTPS、SSE、持久化和备份恢复。第 4 天冻结代码，跑 100 题验收与性能样本，记录失败而非只筛选成功。第 5 天修复 P0 缺陷并重跑受影响测试；第 6 天整理 README、评测报告、录屏和简历，打 tag v1.0。

验收 G6：通过第 11.5 节六项验收，且能在 5 分钟内独立讲清架构和两个工程难点。如果普通 API、权限或幂等不稳定，优先修复；暂停增加新工具。

### 12.8 八周扩展安排

有第 7 至 8 周时，从一项增强中选择：混合检索与召回对照；LangGraph 替换有界循环并保留同一评测；只读 Text to SQL 沙箱；持久化任务与 outbox；一个真实平台沙箱适配器。必须先选能解释明确问题的能力，不把五项同时启动。真实平台接入需另核实官方授权、账号、额度与数据条件，不能保证按原六周工时完成。

## 13 从零学习路线与资料

### 13.1 先修顺序与完成标准

| 阶段 | 只学本项目需要的内容 | 最小练习与掌握标准 |
| --- | --- | --- |
| Python 工程化 | typing、异常、包结构、venv、pytest、日志、基本 async | 拆一个小程序为模块并测试错误路径 |
| Web 基础 | HTTP、JSON、状态码、REST、浏览器请求与跨域 | 能解释登录请求和 401／403／422 的差别 |
| FastAPI | 路由、请求体、依赖、响应模型、配置 | 从零写商品 API，不依赖聊天生成完整工程 |
| 数据库 | SQL、JOIN、聚合、索引、事务、主外键 | 手写销量查询，解释重复 join 和回滚 |
| ORM 与迁移 | Session、模型映射、参数绑定、Alembic | 空库建表、添加字段并保留数据 |
| 认证与权限 | 哈希、JWT、权限检查、租户范围 | 两账号测试，能指出越权入口 |
| LLM 与工具 | tokens、schema、tool call、超时、usage | 同问题调用普通函数和模型选出的函数 |
| RAG | chunk、embedding、过滤、top_k、引用、评测 | 10 篇文档构建检索并分析一次漏召回 |
| 前端与交付 | React 基础、fetch、流式读取、Docker、CI | 展示数据、接 SSE、在新目录启动项目 |

HTTP 和数据库是前两周重点；Agent 经验不能替代后端基础。C++ 基础继续用于算法和操作系统学习，本项目后端先使用 Python；无需同时改成 C++ Web 框架。

### 13.2 官方资料与具体阅读任务

FastAPI Tutorial [D1]：只先完成请求体、错误处理、依赖、Security、Testing 和 Bigger Applications；每看一节就改项目里的一个接口。SQLAlchemy Unified Tutorial [D2]：重点看连接、事务、select 与 ORM Session；Alembic Tutorial [D3]：完成 init、revision、upgrade 与已有库升级练习。

Pydantic Models [D5]：练习 BaseModel、Field、model_validate、严格边界和额外字段拒绝。pytest 入门 [D6]：完成 fixture、参数化和异常断言。模型工具调用文档 [D8]：看工具声明、模型返回调用、应用执行与结果回传；不要跳过失败处理。Embedding 文档 [D9]：确认 query／document 任务类型、维度和批处理策略。

pgvector 官方仓库 [D4]：理解 cosine distance、精确检索与 HNSW 的取舍。MDN SSE [D10]：理解事件格式、空行、心跳与断线，注意本项目用 fetch POST。Docker Compose [D7] 和 GitHub Actions Python [D12]：分别用于本地服务编排与无密钥 CI。

前端只需按 React Learn [D13] 学组件、状态、事件、列表和表单，再按 TypeScript Handbook [D14] 补基本类型。两周内无需完整读完框架文档。Vite 版本所需 Node 版本按实际脚手架文档校验，CI 与本地保持一致，避免照搬原仓库 README 的旧最低要求。

### 13.3 每日学习方法

工作日用 30 至 45 分钟读对应章节，90 至 120 分钟完成一个能演示的功能，最后 15 分钟记录“今天写了什么、为什么这样设计、一个失败案例、下一步”。周末另留 5 至 6 小时联调及 2 小时复盘，使每周总投入接近 20 至 25 小时。笔记重点是自己能解释的因果关系，不追求复制百科。

可让 AI 帮你生成测试数据、解释报错、审查权限路径和给出小段代码。但合并前必须回答：输入来自哪里、谁授权、SQL 做什么、事务何时提交、失败怎么恢复、测试怎样证明正确。答不出来的代码先简化或拆开理解。

每周复盘用四个问题：是否能从空库启动；是否有一个真实失败路径；是否有可核对结果；是否能在没有 AI 帮助时修改一个接口。面试需要的是这些能力和项目证据。

## 14 MVP 裁剪与延期处理

### 14.1 三种时间预算

| 版本 | 可投入时间 | 保留能力 | 主要裁剪 |
| --- | --- | --- | --- |
| 四周展示版 | 约 80 小时 | 两账号隔离、订单／库存导入、2 个查询工具、政策 RAG、最小聊天与 Docker | listing 动作只生成草稿；确认链另补，不声称已实现 |
| 六周标准版 | 约 130 小时 | 本方案 P0、单一 listing 模拟动作、评测与部署 | 真实平台、复杂 BI、长期记忆、队列与多 Agent |
| 八周增强版 | 约 170 小时 | 标准版加一个可证明收益的增强 | 保持单体，不同时新增多个基础设施 |

四周版是投递时的中间产物，不能把尚未完成的审批、幂等与审计写成已有成果。若仍希望四周完成闭环，减少前端和工具数量，将一个简单草稿保存动作加入最后一周，并相应降低其他功能范围。

### 14.2 延期时的删除顺序

首先删除炫酷大屏、复杂图表、品牌样式和移动端适配；其次删除多语言界面、多站点汇率、长期记忆、自动日报与消息推送；再删除复杂多轮规划和第二种模型。仅保留一个经营工具、一个 RAG 工具和一个动作类型也能展示核心能力。

不裁掉权限、参数校验、金额／日期口径、失败处理和动作确认，也不以视频假演示替代缺失后端。若第 2 周 CSV 拖延，可仅接受规定模板并减少字段；若第 4 周 RAG 调参困难，缩小到 10 篇高质量 SOP，优先保证引用与拒答；若没有可用模型额度，先 MockProvider 完成工程，并明确模型评测尚未完成。

### 14.3 风险与应对

| 风险 | 触发信号 | 处理 |
| --- | --- | --- |
| 模型网络／额度不稳 | 第 1 次能力试验仍无法调用 | 提前验证另一个可用 Provider；工程测试保留 mock |
| 后端基础不足 | 第 1 周无法解释 CRUD 与事务 | 取消前端美化，延长基础练习至第 2 周前半 |
| 数据口径混乱 | 同问题 API 与 Agent 数字不同 | 固定 service 单一事实来源，先做手算数据集 |
| RAG 幻觉 | 无证据仍给具体条款 | 加无答案集、结构化引用、阈值校准与拒答 |
| 范围失控 | 第 3 周仍在接多个平台 | 回到 CSV 和单站点，冻结新增需求 |
| 项目不可复现 | 换目录就启动失败 | 锁依赖、空库迁移演练、.env.example 与 seed |

## 15 部署交付与简历表达

### 15.1 本地与测试部署

Compose 至少包含 postgres 和 api，前端构建后由 nginx 提供。数据库镜像须含 pgvector 扩展且版本固定。为数据库数据目录设置持久卷，只暴露 nginx 的公开端口；api 与 postgres 走内部网络。配置数据库 healthcheck，API readiness 再验证必要表与配置，不依赖启动顺序猜测数据库已就绪。[D7]

建议启动流程如下，命令名称是新项目待实现的合同：

```text
复制 .env.example 为 .env 并填写本地配置
docker compose up -d postgres
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m scripts.seed_demo
docker compose run --rm api python -m scripts.ingest_demo_docs
docker compose up -d --build
执行 smoke 检查并登录两账号
```

Mock 模式使用预计算演示向量或确定性 mock embedding，仅用于启动与协议测试，不能用来报告真实 RAG 检索质量。真实模式使用配置的模型／embedding 重新索引，记录版本。README 应分别给出两种模式的启动步骤与界面标识。

测试服务器部署配置 HTTPS，前端与 API 同域，Nginx 关闭 SSE 缓冲。进程非 root 运行、日志写标准输出、.env 不进入镜像或 Git。Vite 环境变量会进入前端构建，不能放模型密钥；公开 API 地址改变后需按构建配置重新打包。

### 15.2 备份回滚与监控

测试部署每天或每次迁移前执行 pg_dump，备份保存到项目之外且限制访问。至少做一次恢复到临时数据库的演练，验证商品、文档和审计数量。镜像打 commit 标签，回滚优先恢复上一个兼容镜像；数据库变更采用先加后迁移的兼容方式，避免把回滚等同于盲目 downgrade。

JSON 日志包含 request_id、store_id、run_id、tool_name、duration_ms、status 和 error_code，正文与密钥默认不记录。统计普通 API 延迟、模型延迟、token、工具失败率、RAG 无答案比例和动作冲突次数。单机项目先用日志与数据库报表就够，后续再接 OpenTelemetry 或 Langfuse。

### 15.3 CI 的完成定义

PR 执行后端 Ruff、pytest、带 pgvector 的 PostgreSQL 集成测试、迁移检查、前端类型检查与构建、镜像构建。全部不需要真实模型密钥。人工触发的 eval workflow 使用受控密钥运行真实模型题，设置预算和超时，不对外部 PR 暴露密钥。[D12]

至少保留一次 CI 成功记录和一次缺陷修复记录。自动部署可以在 main 检查通过后触发测试环境；无需为实习作品引入 Kubernetes、服务网格或多区域。

### 15.4 对外交付清单

README 包含项目定位、功能截图、三分钟演示、架构图、启动步骤、环境变量、演示账号获取方式、API 入口、数据口径、测试与评测方法、已知限制和参考项目。评测报告保留冻结题集、结果摘要、失败分类、实测环境与复现命令。仓库应清除密钥和真实个人数据。

建议视频顺序：15 秒讲问题；30 秒导入并查看数据；45 秒展示经营工具与口径；40 秒政策问答并打开引用；40 秒生成草稿、确认、再次点击验证幂等；10 秒展示审计和测试报告。录屏可控制在 3 至 4 分钟。

### 15.5 可直接改写的简历描述

以下是完成相应模块后使用的表达模板，不能在功能尚未实现时直接作为经历。没有真实用户和线上流量，就明确标为个人项目与演示数据。

项目名称：SellerPilot 跨境电商卖家智能运营 Agent 平台（个人项目）。技术栈：Python、FastAPI、PostgreSQL、SQLAlchemy、pgvector、React、Docker。

描述一：设计并实现面向卖家的模块化单体后端，支持商品、订单和库存 CSV 导入，统一销售额与库存风险计算口径，并通过店铺授权及数据库约束实现多租户数据隔离。

描述二：实现有界工具调用 Agent，将自然语言映射为参数化经营查询；构建带文档版本、站点过滤与引用校验的政策 RAG，提供 SSE 状态与答案输出及可追溯工具记录。

描述三：实现 listing 草稿的人工确认、版本校验、事务幂等和审计，在本地模拟环境验证并发确认不会重复更新；使用固定数据集、CI 与容器部署保障可复现。

只有得到结果后才补入数字：“在 N 道冻结题、模型 X、数据版本 Y 上，工具选择正确率 A%；在环境 Z、并发 C 下，普通查询 p95 为 T ms。”将实际 N、X、Y、A、Z、C、T 替换为报告中的真实值；否则删除整句。不要写“生产级”“支撑百万用户”“营收提升 30%”“自研大模型”或未经证实的 100% 准确率。

### 15.6 面试准备

准备回答六个问题：为什么选单体；工具调用与普通接口有什么关系；为什么经营查询不用任意 Text to SQL；店铺隔离在哪几层；引用存在为什么仍可能答错；重复确认如何防止两次执行。每个问题都拿一段实现、一条失败用例或一次评测结果作证据。

后端实习叙述侧重表设计、索引、事务、鉴权、幂等、部署；Agent 实习叙述侧重 schema、执行边界、RAG、评测、超时和成本。继续复习数据结构、网络、操作系统与 SQL；作品帮助面试官讨论能力，不能替代基础知识。

## 16 参考来源与启动清单

### 16.1 固定提交的仓库证据

以下链接均固定到本次读取的提交。目录与代码内容以该提交为准；网页上的运行展示和默认分支可能随后变化。

[R1] 仓库说明与功能边界：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/README.md

[R2] 后端依赖：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/requirements.txt

[R3] HTTP 入口与流式执行：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/main.py

[R4] Agent 路由与拆分：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/app/agent.py

[R5] 数据库与只读连接：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/app/db/database.py

[R6] FAQ 检索：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/app/faq.py

[R7] 商品 SQL 与模拟订单：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/app/sql.py

订单模块：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/app/orders.py

[R8] 评测实现与局限：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/backend/test/evaluate_agent_tuned.py

[R9] CI 与 Compose：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/.github/workflows/ci.yml

Compose：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/docker-compose.yml

[R10] MIT 许可：https://github.com/VIVPM/ecommerce-agent/blob/8b37e2899ccc6ea74e79a8280b6184fe14114018/LICENSE

补充证据路径：frontend/package.json、frontend/src/api.js、backend/app/db/models.py、backend/app/llm_provider.py、backend/app/cache.py、backend/app/memory_store.py、backend/app/observability.py、backend/migrations.sql、tests/test_logging.py、.github/workflows/refresh.yml。均可在上述固定提交的目录中定位。

### 16.2 官方技术学习资料

[D1] FastAPI Tutorial：https://fastapi.tiangolo.com/tutorial/

[D2] SQLAlchemy Unified Tutorial：https://docs.sqlalchemy.org/en/20/tutorial/

[D3] Alembic Tutorial：https://alembic.sqlalchemy.org/en/latest/tutorial.html

[D4] pgvector 官方仓库：https://github.com/pgvector/pgvector

[D5] Pydantic Models：https://docs.pydantic.dev/latest/concepts/models/

[D6] pytest 入门：https://docs.pytest.org/en/stable/getting-started.html

[D7] Docker Compose：https://docs.docker.com/compose/intro/compose-application-model/

[D8] Gemini Function Calling：https://ai.google.dev/gemini-api/docs/function-calling

[D9] Gemini Embeddings：https://ai.google.dev/gemini-api/docs/embeddings

[D10] MDN Server Sent Events：https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events

[D11] OWASP LLM 应用风险：https://owasp.org/www-project-top-10-for-large-language-model-applications/

[D12] GitHub Actions Python：https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python

[D13] React Learn：https://react.dev/learn

[D14] TypeScript Handbook：https://www.typescriptlang.org/docs/handbook/intro.html

资料核查日期为 2026 年 10 月 8 日。官方在线文档会更新；依赖、模型可用性和具体 SDK 调用，以项目实际锁定版本的测试为准。

### 16.3 明天就可以执行的启动清单

1. 建立自己的 sellerpilot 仓库，写下四个用户故事、每周可投入时长和六周交付日期。
2. 固定参考仓库 SHA，读认证与聊天入口，写一页请求链路笔记。
3. 跑通自己的 /health 和一个商品请求模型，写第一个无效输入测试。
4. 启动 PostgreSQL，手写一条按 SKU 汇总销量的查询，再引入 ORM。
5. 提前验证可用模型的工具调用与 embedding；同时保留 mock，不让云服务问题阻塞基础工程。

第一周的成果应是你能从空目录解释并搭起的后端，而不是截图中的复杂聊天界面。后续每周都保留一个可运行版本和一份可核验结果，六周后就有一个可以被面试官具体追问的作品。

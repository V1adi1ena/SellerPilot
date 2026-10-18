# SellerPilot——你的私人智能电商运营 Agent 平台

SellerPilot 是面向跨境电商卖家的智能运营 Agent 学习项目，使用演示数据逐步实现商品管理、经营分析、政策检索与经确认的运营动作。

截至 **2026-10-18**，本地演示版已贯通登录选店、商品与低库存、CSV订单及明细导入、经营分析、GLM问答与政策引用、标题草稿审核和确认。React前端已整合五个导航模块，开发地址为 **http://127.0.0.1:5188**。用户逐步确认页面功能跑通，真实GLM提问、追问与政策引用已由用户确认。本轮另通过实际前端构建、独立MySQL测试库业务闭环验收；这不代表生产部署或全部模型回答的语义正确性已验收。

## 当前进度与停点

| 模块 | 当前状态 | 说明 |
| --- | --- | --- |
| 用户、店铺、商品 | 已实现并验证 | 注册登录、JWT、商品 CRUD、价格校验、店铺归属及双账号隔离 |
| 低库存查询 | 已验收 | 指定店铺、库存阈值、排序、返回数量限制、业务函数权限校验 |
| 订单与订单明细 | 已迁移并验证 | 店内订单号唯一、明细行号唯一、复合外键、状态与金额约束 |
| 订单 CSV 导入 | 已验收 | 文件校验、UTC 转换、新增或更新、文件去重、版本递增、整批回滚 |
| 明细 CSV 导入 | 已验收 | 店内订单与 SKU 关联、数量与退款校验、新增或更新、并发去重 |
| 订单查询、销售汇总、商品销量 | 已验收 | 真实 HTTP、手算金额、日期边界、分页、多币种、缺明细与双账号隔离 |
| GLM 接入 | 已实现 | OpenAI兼容接口；后端从项目根目录.env读取密钥，不下发浏览器 |
| 只读 Agent 工具 | 已实现 | 低库存、订单、销售汇总、商品销量和政策检索；工具白名单、参数重验、服务端注入用户与店铺身份 |
| 对话会话 | 已实现 | 按用户和店铺隔离；保存有限问答历史，并用版本条件更新处理并发冲突 |
| 演示政策检索 | 已实现并通过当前阶段验收 | 四条共享自编政策，词面检索、当前轮引用来源校验与资料不足状态；不代表真实平台政策 |
| 标题草稿后端 | 已实现，用户报告完成 | 生成、预览、确认、旧标题冲突、幂等回执及单一动作记录 |
| 前端登录与店铺选择 | 用户已运行成功 | React/Vite/TypeScript，5188端口，当前标签页保存JWT |
| 前端运营问答 | 用户确认真实GLM跑通 | 提问、追问、政策引用；另有模拟浏览器错误与隔离检查 |
| 前端标题审核 | 用户确认成功 | 生成、预览、核对、确认与回执 |
| 前端CSV导入 | 用户使用测试文件确认成功 | 订单、明细、重复提示和行级错误 |
| 前端经营数据 | 用户报告完成 | 日期、分币种汇总、订单状态筛选与分页 |
| 前端商品与库存 | 用户确认完成 | 店铺商品、后端低库存筛选、阈值边界和100条限制 |
| 工作区导航 | 用户确认成功 | 五模块按需挂载；同店铺切模块保留状态，换店铺清理 |

**当前停点：** 功能接入已完成，进入演示验收与交付收尾。本轮新增 `backend/test_acceptance.py`，用于独立测试库中的业务闭环回归；完整演示步骤与验证范围见 [演示验收](演示验收.md)。标题确认仍通过独立API执行，没有注册为模型工具。

## 技术栈

Python、FastAPI、Pydantic、SQLAlchemy、PyMySQL、MySQL 8.4、Alembic、pytest、HTTPX、Docker Compose、pwdlib/Argon2、PyJWT、python-multipart、GLM（OpenAI 兼容 API）、React、TypeScript、Vite。

## 项目结构

```text
SellerPilot/
├── backend/
│   ├── main.py                 # 请求/响应模型、认证依赖、HTTP 接口
│   ├── database.py             # 数据库连接、Base、get_db
│   ├── models.py               # 用户、店铺、商品、订单、明细、导入记录、会话与标题草稿
│   ├── services.py             # 店铺授权与低库存业务函数
│   ├── imports.py              # 订单 CSV 解析与事务导入
│   ├── order_items_import.py   # 明细 CSV 解析、关联校验与事务导入
│   ├── analytics.py            # 订单查询、销售汇总、商品销量
│   ├── llm.py                  # GLM 配置读取、HTTP 请求与错误归一化
│   ├── agent.py                # 工具白名单、参数校验、调用循环与政策响应检查
│   ├── conversations.py        # 对话历史读取、并发版本控制与事务保存
│   ├── policy_search.py        # 共享演示政策的词面检索
│   ├── policy_service.py       # 政策检索前的店铺归属校验
│   ├── title_drafts.py         # 标题草稿生成、预览、确认与事务
│   ├── secuity.py              # 密码哈希与 JWT 工具（当前文件名）
│   ├── test_main.py            # 基础接口自动化测试
│   ├── test_acceptance.py      # 独立测试库的业务闭环，模拟模型响应
│   ├── requirements.txt
│   └── migrations/            # Alembic 配置入口与版本脚本
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # React挂载入口
│   │   ├── App.tsx            # 登录、账号与当前店铺
│   │   ├── StoreWorkspace.tsx # 五模块导航、按需挂载与状态保留
│   │   ├── AgentChat.tsx      # 当前店铺问答、引用与请求清理
│   │   ├── ProductTitles.tsx  # 标题草稿生成、审核与确认
│   │   ├── CsvImports.tsx     # 文件上传、去重回执和行级错误
│   │   ├── StoreOperations.tsx # 日期、销售汇总与订单分页
│   │   ├── ProductInventory.tsx # 商品与低库存查询
│   │   ├── api.ts             # fetch、JWT及API封装
│   │   └── style.css          # 布局和手机适配
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts         # 5188开发端口与/api代理
│   └── README.md              # 前端流程、函数与验收说明
├── alembic.ini
├── compose.yaml                # MySQL 容器与持久化卷
├── .env.example
├── .gitignore
├── README.md
└── 技术方案.md
```

## 请求流程与函数分工

普通查询路径为：HTTP 路由 → JWT 用户认证与数据库会话 → 业务函数 → 店铺归属校验与查询 → 响应。Agent 路径为：Agent HTTP 路由 → `run_conversation_agent` 读取用户与店铺对应的历史 → `run_store_agent` 检查店铺、请求 GLM 并执行白名单工具 → 保存问答。工具的用户 ID 来自已验证 JWT，店铺 ID 来自路由并再次由后端核验；模型只提供工具名和业务参数。

| 函数或方法 | 实现与作用 | 参与的流程 |
| --- | --- | --- |
| `get_db` | 为请求提供 Session，结束后关闭会话；不替业务函数自动提交写入 | 所有数据库接口 |
| `get_current_user` | 验证 Bearer JWT，读取当前用户 | 需要登录的接口；提供可信 user_id |
| `require_owned_store` | 同时按店铺 ID 和 owner_id 查询；查不到时抛业务异常 | 查询与导入共用的权限入口 |
| `list_low_stock_products` | 校验阈值和数量，筛选库存小于阈值的商品，按库存及 ID 排序 | 低库存 API 与 Agent 工具 |
| `OrderCsvRow.parse_timestamp` | 要求时间含时区偏移，转换为 UTC 后用于 MySQL DATETIME | 订单 CSV 字段校验 |
| `parse_orders_csv` | 解码 UTF-8、检查表头与记录数，用 Pydantic 验证每行并检查文件内重复订单号；不访问数据库 | 订单导入的预校验阶段 |
| `import_orders_csv` | 授权、校验文件、锁定店铺、查重、新增或更新订单，将订单、导入记录及版本一次性提交 | 订单导入的事务边界 |
| `OrderItemCsvRow.check_refund` | 基于已验证的数量和成交单价，拒绝超过行成交额的退款 | 明细 CSV 字段校验 |
| `parse_order_items_csv` | 检查六列表头、数量、Decimal 金额及重复的“订单号 + 行号”；不访问数据库 | 明细导入的预校验阶段 |
| `import_order_items_csv` | 在目标店铺内查询订单和商品，校验币种与已有行的商品归属，再统一提交明细、导入记录及版本 | 明细导入的事务边界 |
| `utc_range` | 校验两个带时区的时间，转 UTC，并要求开始早于结束 | 三种经营查询共用的时间边界 |
| `check_page` | 验证 limit 与 offset 的整数类型及范围 | 订单列表、商品销量分页 |
| `utc_text` | 将数据库中约定为 UTC 的无时区时间输出为带 Z 的字符串 | 查询响应时间格式化 |
| `money` | 将 Decimal 金额输出为两位小数字符串 | 销售汇总和商品销量响应 |
| `context` | 组装店铺、UTC 起止时间、区间规则和数据版本 | 经营查询的公共响应字段 |
| `list_store_orders` | 按店铺、时间、可选状态筛选，倒序排列，多取一条判断 has_more | 订单查询 API 与 Agent 工具 |
| `summarize_sales` | 外连接订单与明细，按币种分组，用 COUNT DISTINCT 计订单数、SUM 计数量和金额，并识别无明细订单 | 销售汇总 API 与 Agent 工具 |
| `list_product_sales` | 关联明细、订单和商品，按商品与订单币种分组，按销售件数排序 | 商品销量 API 与 Agent 工具 |
| `chat` | 从 `.env` 读取模型配置，通过 HTTP 请求 GLM；统一处理超时、网络和服务端错误，可启用 JSON 输出模式 | `run_store_agent` 的模型请求 |
| `execute_tool` | 只允许注册表中的工具；按工具对应的 Pydantic 模型重新校验参数，并传入服务端身份 | Agent 收到模型工具调用后 |
| `run_store_agent` | 检查店铺归属，组织当前时间、店铺上下文与有限历史；循环请求模型和执行工具，整个请求最多执行 3 次工具调用 | Agent 业务流程；返回答案、工具轨迹和引用 |
| `build_policy_response` | 校验政策回答 JSON、回答状态和引用 ID；引用必须来自本次检索，资料不足时以服务器固定文本替代模型内容 | Agent 政策回答收尾 |
| `retrieve_policy_chunks` | 对项目自编政策做词面相关度排序，返回候选原文；不是语义蕴含判断 | 政策检索服务 |
| `search_store_policy` | 先检查用户拥有目标店铺，再调用共享政策检索，返回范围与版本信息 | Agent 的政策查询工具 |
| `run_conversation_agent` | 按用户和店铺读取会话，调用 Agent 后保存问答；使用版本条件更新避免并发覆盖，失败时回滚 | Agent HTTP 接口的会话协调与事务边界 |

`main.py` 中的 `get_low_stock_products`、`upload_orders_csv`、`upload_order_items_csv`、`get_store_orders`、`get_sales_summary`、`get_product_sales` 是 HTTP 适配层：获取参数和依赖，调用相应业务函数，将业务异常映射为 404、422 或 409。

## 本地运行

以下命令从项目根目录执行，使用 PowerShell。已有虚拟环境时跳过创建：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m pip install alembic pytest httpx
```

复制 `.env.example` 为 `.env` 并填写数据库配置；已有 `.env` 时保留。数据库默认端口为 `3307`。生成 JWT 签名密钥并填入 `.env` 的 `JWT_SECRET_KEY`：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

`.env` 和真实密钥不提交到 Git。上传 CSV 需要 `python-multipart`，已加入 requirements。

启动数据库并执行迁移：

```powershell
docker compose up -d mysql
python -m alembic upgrade head
```

`upgrade head` 执行尚未应用的迁移；`stamp head` 只登记版本、不建表，不能代替空库初始化。

启动后端：

```powershell
cd backend
python -m uvicorn main:app --reload
```

- [Swagger API 文档](http://127.0.0.1:8000/docs)
- [数据库连接检查](http://127.0.0.1:8000/database-check)

首次使用顺序：注册 → 登录 → Swagger Authorize 填入 access_token 本身 → 创建店铺 → 创建商品 → 导入订单 → 导入明细 → 查询。

登录接口不会自动切换 Swagger 的授权令牌；双账号验证时需主动更换令牌。

前端在另一个可见终端启动：

```powershell
cd D:\Project\SellerPilot\frontend
npm ci
npm run dev
```

打开 [前端工作台](http://127.0.0.1:5188)，使用已注册账号登录；前端当前还没有注册与创建店铺页面。前后端开发进程分别在各自终端按Ctrl+C停止。5188是当前配置，启用strictPort后端口被占用会直接报错。

模型配置位于项目根目录.env：LLM_BASE_URL、LLM_MODEL、LLM_API_KEY由后端读取。前端只保存登录JWT，模型密钥不写入前端代码或Vite环境变量。前端详细说明见 [frontend/README.md](frontend/README.md)。

## API

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | `/auth/register` | 注册用户 |
| POST | `/auth/login` | 登录，令牌有效期 30 分钟 |
| GET | `/auth/me` | 查询当前登录用户 |
| POST | `/stores` | 创建自己的店铺 |
| GET | `/stores` | 列出自己的店铺 |
| GET | `/stores/{store_id}` | 查询自己的店铺 |
| POST | `/products` | 在自己的店铺创建商品，store_id 必填 |
| GET | `/products` | 列出自己的商品，支持可选 store_id 和 limit |
| GET | `/products/{sku}` | 查询自己的商品 |
| PUT | `/products/{sku}` | 修改 title、price、currency、stock，四项均必填 |
| DELETE | `/products/{sku}` | 删除商品，成功返回 204 |
| GET | `/stores/{store_id}/products/low-stock` | 低库存查询 |
| POST | `/stores/{store_id}/imports/orders` | 上传订单 CSV |
| POST | `/stores/{store_id}/imports/order-items` | 上传明细 CSV |
| GET | `/stores/{store_id}/orders` | 按时间与状态查询订单 |
| GET | `/stores/{store_id}/sales/summary` | 按币种汇总经营指标 |
| GET | `/stores/{store_id}/sales/products` | 商品销量排行 |
| POST | `/store/{store_id}/agent/query` | 查询只读 Agent；可提交可选 `conversation_id` 延续会话 |
| POST | `/stores/{store_id}/products/{product_id}/title-drafts` | 根据现有标题生成并保存pending草稿，返回201 |
| GET | `/stores/{store_id}/title-drafts/{draft_id}` | 预览自己的草稿或查看应用回执 |
| POST | `/stores/{store_id}/title-drafts/{draft_id}/confirm` | 明确确认后应用标题；旧标题不匹配返回409 |

Agent请求体示例：

```json
{
  "message": "请分别说明演示店铺的发货时限，以及签收后的退货申请期限和商品条件。"
}
```

延续已有对话时，在请求体中加入该会话的 `conversation_id`。政策回答的响应包含 `citations` 和 `policy_status`：`answered` 表示模型提交了回答且引用通过来源 ID 校验；`insufficient_evidence` 表示后端返回固定资料不足提示。前者不保证模型内容在语义上完全受原文支持。

所有受保护的商品、店铺、导入、经营查询及 Agent 接口均要求有效 Bearer 令牌，未认证返回 401。新业务函数对不存在或无权访问的店铺统一返回“店铺不存在”，接口映射为 404。

商品创建默认币种为 USD、库存为 0。SKU 当前仍在全部商品中唯一，响应金额使用十进制字符串。原有无归属店铺和商品不通过当前业务接口暴露。

低库存查询参数为 `threshold`（默认 10，最小 0）和 `limit`（默认 20，范围 1～100）。条件是 `stock < threshold`，按库存升序、商品 ID 升序排列；有权访问但没有匹配商品时返回空列表。

## CSV 模板与导入规则

两个上传接口都使用 multipart 表单字段 `file`。文件扩展名为 `.csv`，编码为 UTF-8（支持 BOM），最多 5 MiB、10000 条数据记录，表头及顺序固定。

订单模板：

```csv
external_order_id,ordered_at,status,currency
DEMO-001,2026-10-12T10:00:00+08:00,paid,USD
DEMO-002,2026-10-13T09:30:00+08:00,pending,USD
```

明细模板：

```csv
external_order_id,line_no,sku,quantity,unit_price,refund_amount
DEMO-001,1,W2-SHOE,2,20.00,0.00
DEMO-001,2,W2-HAT,1,10.00,0.00
```

导入明细前，目标店铺必须已有对应订单与商品。示例 SKU 需通过商品接口预先创建。

- 订单时间必须含偏移，转为 UTC 后以 MySQL DATETIME 保存。状态限 pending、paid、shipped、cancelled，币种为三个大写字母。
- 数量和行号必须是正整数，金额使用 Decimal、最多两位小数。退款非负且不能超过该行成交额。
- 明细只能引用同店铺的订单和商品，商品币种必须与订单一致。数据库复合外键同时约束店铺及对象 ID。
- 同一文件内，订单号不能重复；明细的“订单号 + 行号”不能重复。
- 同一店铺、同一导入类型、相同文件内容通过 SHA-256 去重；改文件名不会绕过去重。
- 新文件中的已有订单号更新时间和状态，不能改币种；已有明细行可更新数量、成交单价和退款，不能换商品。未出现在新文件中的旧记录保留。
- 订单、明细、导入记录和店铺 data_version 在对应导入事务中统一提交；失败整批回滚。原子性以单个文件为单位，两个文件之间不是同一事务。
- 成功的新文件使店铺 data_version 加一；重复文件返回首次导入结果，不增加当前版本，也不恢复被后续文件更新的旧值。
- 导入以店铺行锁串行协调；去重及已有记录查询使用锁定读取，避免并发请求读到旧快照。
- 导入历史订单与明细不扣减当前库存，退款也不自动回补库存。

成功响应包括 `import_job_id`、`row_count`、`data_version`、`duplicate`。其中 data_version 是该文件首次成功导入时的版本。校验失败返回 422，并提供行号、字段和原因；数据库写入异常回滚后返回 409。

## 经营查询口径

三个查询均要求 `start_at`、`end_at` 含时区偏移，开始时间必须早于结束时间。查询前转 UTC，区间为 `[start_at, end_at)`。

查询北京时间 10 月 12 日整天，可在 Swagger 分别填写：

```text
start_at = 2026-10-12T00:00:00+08:00
end_at   = 2026-10-13T00:00:00+08:00
```

订单列表默认展示所有状态，可用 `status` 筛选，按下单时间和 ID 倒序。订单列表与商品销量支持 `limit`（默认 20，范围 1～100）、`offset`（默认 0），通过 `has_more` 指示后续结果。

销售汇总与商品销量只统计 paid、shipped：

| 指标 | 口径 |
| --- | --- |
| 订单数 | 区间内有效状态订单的去重计数；一单多行不重复计数 |
| 销售件数 | 有效订单已导入明细的 quantity 之和；退款金额不推断退货件数 |
| 销售额 | quantity × unit_price 之和，使用历史成交单价 |
| 退款金额 | 上述明细记录的 refund_amount 之和 |
| 净销售额 | 销售额减退款金额 |
| 币种 | 按订单币种分别统计，不合并 USD 和 EUR |
| 无明细订单 | 用 orders_without_items 及 has_orders_without_items 标记，订单数仍包含这些有效订单 |

商品销量按销售件数降序排列，同量按商品 ID、订单币种排序。响应包含查询边界、统计状态和 data_version。金额基于已导入明细，商品当前改价不会影响历史销售额。

当前没有退款发生时间，退款金额按所属订单的下单时间归入查询区间，不是退款期间现金流统计。无明细提示只能识别完全缺少明细的订单，不能发现一笔订单只漏导了部分明细。

## Agent 与政策检索

Agent API 为 `POST /store/{store_id}/agent/query`。请求包含 `message`，可选正整数 `conversation_id`；新请求不传会创建会话。登录用户由 JWT 确定，目标店铺经 `require_owned_store` 校验。会话按用户和店铺联合读取；服务端只向模型提供最近有限轮问答。会话保存通过版本条件更新处理并发；Agent 本身只读，不在此事务中修改商品、库存或订单。

| 文件 / 函数 | 作用与流程位置 |
| --- | --- |
| `llm.py:chat` | 根据 `.env` 配置请求 GLM，支持工具调用及政策回答所用的 JSON 模式；把网络和服务错误转成受控异常。 |
| `agent.py:execute_tool` | 先按工具名白名单查找，再以 Pydantic 严格校验参数；将已认证的 user_id 和路由 store_id 交给既有业务函数。 |
| `agent.py:run_store_agent` | 构造店铺上下文和模型消息，最多循环 4 次模型请求、累计执行 3 次工具调用。多主题政策问题可分轮补查。它不提交数据库事务。 |
| `agent.py:build_policy_response` | 对模型返回的状态与 JSON 结构做校验，要求正向回答引用本轮检索片段；拒答时使用固定服务端文本并清空引用。 |
| `policy_search.py:retrieve_policy_chunks` | 用词项重合度对四条共享演示政策排序，返回最多指定数量的片段；检索相关度不是答案正确概率。 |
| `policy_service.py:search_store_policy` | 检索前再次验证店铺归属，标注共享演示资料的范围和版本。 |
| `conversations.py:run_conversation_agent` | 在会话事务中读取历史、调用 Agent、写入本轮问答；乐观版本更新失败或数据库错误会回滚。 |

当前政策文件是项目自编的共享演示内容，涵盖发货、取消、退货和商品标题规范。所有店铺检索相同资料；目前没有店铺私有文档上传、外部平台同步、向量数据库或独立的知识库管理界面。

后端能够限制模型调用哪些工具、校验工具参数、验证店铺归属，并确认引用 ID 来自本次检索。它不能普遍证明模型生成的每句话都被引用原文语义支持；`answered` 状态也是模型先作出的判断。因此，引用存在不等于内容必然正确，仍需用真实问题持续核对回答和原文。

验证记录：

- 修复前真实 GLM 的 12 题开发集为 9/12 机械检查通过；发现多主题问题失败、缺资料时附带无关条款、真实平台问题范围不清等问题，原始结果留档。
- 修复迭代的完整开发集为 11/12，发现提示注入场景发生过度拒答；之后调整提示并复测关键场景。
- 最终候选版本通过 4/4 关键真实 GLM 场景，另通过 4/4 未用于提示调整的补充问题；补充集规模较小，不代表独立正式评测。
- 最终修复文件另有 36 项本地自动检查通过，使用 SQLite 和模拟模型/HTTP，不代表真实 GLM 或 MySQL 集成测试。
- 用户确认已复制后，在 Swagger 成功验证修复。以上结果不构成语义正确率保证；最终候选版没有重跑完整 12 题集。

验证报告、测试脚本和阶段修复说明保存在本次协作工作目录的 `sellerpilot_policy_evaluation/`、`sellerpilot_policy_fix_step/` 等文件夹，目前未加入 SellerPilot 仓库。

## 标题草稿与确认

`title_drafts.py`将生成与应用分开：生成只保存pending草稿，用户查看后再通过独立确认API修改商品。当前没有把确认操作注册为Agent工具。

| 函数 | 作用与事务 |
| --- | --- |
| `generate_title_suggestion` | 根据原标题请求一次GLM，校验JSON、字符串长度和是否有变化；不访问数据库 |
| `create_product_title_draft` | 先验证店铺与商品归属，再生成并保存草稿；负责提交与失败回滚，不更新商品 |
| `title_draft_result` | 格式化草稿与应用回执，不执行SQL |
| `get_product_title_draft` | 按用户、店铺、草稿ID读取，供预览和查看结果；只读 |
| `confirm_product_title_draft` | 要求confirmed为true，锁定草稿与商品，核对原标题，将标题与应用记录在同一事务提交 |

确认请求体为 `{"confirmed": true}`。只有草稿创建者能在自己店铺确认；商品ID是数字id。待确认草稿要求商品当前标题与original_title精确相同，否则409；此检查比较当前值，不追踪改动后又改回的历史。

MySQL通过FOR UPDATE读取当前记录并加锁，populate_existing刷新ORM缓存对象。已applied的草稿直接返回原回执，不再次修改商品；即使后来手动改过标题，重试也不会撤销后来修改。应用时间与现有DATETIME秒精度对齐，确保首次与重试回执一致。

草稿表同时充当这一动作的最小操作记录：原标题、建议标题、创建者、状态与应用时间。因只允许创建者确认，applied_by由created_by确定。这不覆盖所有商品CRUD或导入操作，也不是通用审计系统。草稿生成请求尚未去重；幂等保证针对同一draft_id的确认。

用户已报告标题生成与确认步骤完成。27项本地测试及三个真实MySQL并发/重试场景通过，临时样本已清理；这些不等于本轮文档更新重跑了HTTP验收。后端仅校验标题格式与长度，建议内容仍需人工审阅。

## 前端工作台

App管理登录和当前店铺，StoreWorkspace提供运营问答、经营数据、商品与库存、CSV导入、标题审核五个入口。首次打开模块才挂载；同店铺切换用hidden隐藏已打开模块，保留聊天、草稿、文件选择和查询结果。在途请求可继续完成。账号或店铺改变时，工作区key改变，旧组件卸载、取消等待并清空页面状态。

api.ts统一附带Bearer JWT、处理错误及CSV结构化行错误。FormData文件请求由浏览器生成multipart boundary。浏览器请求/api，由Vite开发代理转发到127.0.0.1:8000；生产环境仍需单独配置代理。

经营查询页面按北京时间选择日期，包含结束当天，转成下一天零点作为后端不包含的上界。订单状态筛选只影响订单列表；销售汇总始终统计paid和shipped，金额保留后端精确字符串，按币种分别展示。缺明细与两接口数据版本不同均会提示。

商品和低库存查询由后端筛选，不在前100个商品内做本地过滤。当前商品接口没有分页，页面最多显示100条并披露截断。导入或应用标题后，已打开模块不会自动刷新，需要重新查询或刷新商品。

JWT保存在当前标签页sessionStorage，不保存密码；模型密钥仅在后端。401清空整个工作区。退出不撤销已签发JWT，令牌仍按到期规则失效。浏览器刷新、切店或退出不恢复旧页面会话，后端保存记录仍存在。

用户已确认各步功能成功，包含真实GLM提问、追问和政策引用。浏览器自动化使用模拟接口，覆盖导航状态保留、在途请求、跨店铺清理、错误、401与手机布局。页面不使用SSE，也没有历史会话列表。详细流程与函数说明见 [前端README](frontend/README.md)。

## 迁移与验证记录

当前代码包含标题草稿迁移 **`d6c7744dd9bc`**，父版本为会话迁移 `b6e4d2c81a90`。启动含草稿功能的环境前执行 `python -m alembic upgrade head`；2026-10-18已只读确认业务库为该head；独立sellerpilot_test从导入记录版本补齐会话与标题草稿迁移后执行完整验收。

新增迁移：

- `d741de3672aa`：订单、订单明细，以及商品联合唯一约束。
- `1ae0fe8ad4e4`：导入记录、店铺 data_version。
- `b6e4d2c81a90`：Agent 对话记录及用户、店铺关联。
- `d6c7744dd9bc`：商品标题草稿、归属外键和状态约束。

测试库使用同一 MySQL 实例中的 `sellerpilot_test`，需提前创建并授权，再从项目根目录升级：

```powershell
python -c "import os; os.environ['DB_NAME'] = 'sellerpilot_test'; from alembic.config import main; main(['upgrade', 'head'])"
```

运行仓库内的基础测试和开发库迁移检查：

```powershell
python -m pytest backend/test_main.py -q
python -m alembic current
python -m alembic check
```

以下保留历史阶段记录；2026-10-18新增验证见 [演示验收](演示验收.md)：8项原有测试和1项业务闭环测试通过，实际前端构建通过，运行中的前端模块加载200、未登录代理请求401。本轮未重跑真实GLM评测集。不同验证方式应分开理解：

| 验证范围 | 最近记录 | 验证方式 |
| --- | --- | --- |
| 仓库基础接口测试 | 8 passed | pytest，使用独立测试库并清理测试数据 |
| 低库存 | 21/21 检查通过 | 真实 HTTP 与业务函数检查 |
| 订单模型与约束 | 20/20 检查通过 | MySQL 约束、手算金额、事务与清理检查 |
| 订单 CSV | 39/39 流程检查通过 | 迁移、真实上传、去重、回滚、权限、并发和回归流程 |
| 明细 CSV | 42/42 流程检查通过 | 真实上传、金额、跨店铺关联、并发、回滚及回归流程 |
| 经营查询示例 | 26/26 检查通过 | 之前的示例验证，使用测试库与本地临时路由 |
| 经营查询真实服务 | 70/70 流程检查通过（2026-10-15） | 实际注册登录、两类 CSV 上传、手算汇总、历史价格、退款、日期边界、分页、无明细、权限、无写入副作用和清理 |
| 标题草稿与确认 | 27项本地测试通过（2026-10-17） | 实际项目模型、内存SQLite与模拟模型；生成、权限、回滚、重复确认、旧标题冲突 |
| 标题确认并发 | 三个真实MySQL场景通过（2026-10-17） | 同草稿并发回执一致、重试保留后续修改、不同草稿竞争；样本已清理 |
| 前端基础 | 类型检查、构建及九组浏览器流程检查通过 | 页面账号数据为模拟；另验证开发代理向现有后端转发未登录请求得到401 |
| 前端聊天 | 类型检查、构建及九组浏览器流程检查通过 | 模拟Agent接口；会话续接、切店隔离、引用、失败/401处理、手机布局 |

流程检查数包含环境检查、数据清理或回归测试汇总项，不应相加为独立 pytest 用例总数。Week 2 的专项脚本和报告目前保存在本次协作的临时工作目录，尚未纳入项目仓库；执行 `test_main.py` 不会覆盖所有新增功能；新增 `test_acceptance.py` 将主要闭环纳入仓库，但不代替专项并发、政策语义和完整浏览器真实模型验收。专项测试使用独立临时账号或回滚事务，已清理样本。本次经营查询脚本为 `sellerpilot_analytics_verification.py`，报告为 `sellerpilot_analytics_results.json`，基础回归报告为 `sellerpilot_analytics_regression.xml`；均保存在协作工作目录。

## 下一步

1. 按演示验收清单完成一次连贯演示，记录问题并准备简历项目说明。
2. 若目标是部署，再单独补充空库重建、生产代理、密钥管理和运行维护验收。
3. 按实际需要处理带明细商品删除的友好冲突提示；不为进度额外引入Redis等基础设施。

本地演示版主要功能已接入。尚未实现真实电商平台、SSE、历史会话恢复、通用审计、完整生产部署、商品/库存CSV和前端注册/建店/商品CRUD。SKU仍全局唯一。政策引用合法不等于语义正确，标题建议仍需人工审核。完整空库重建与生产部署尚未验收。

## 开发与学习约定

继续按“用户编写和理解代码，助手检查与验证”的节奏推进。为加快进度可以提供完整文件，但每次新增函数都应说明：

1. 函数解决什么问题，属于路由、业务、校验、数据访问还是响应格式化。
2. 输入和输出是什么，参数由用户、登录状态、数据库还是其他函数提供。
3. 核心实现如何工作，为什么选择这种查询、校验或事务方式。
4. 谁调用它、它调用谁，参与请求流程中的哪一步。
5. 是否访问或修改数据库，事务由谁提交，失败如何处理。

每轮以一个能验证的小闭环为目标，并明确区分“代码已写”“示例已验证”和“项目实际接口已验收”。

新增前端语法先结合当前请求流程解释，再继续扩展；本次已讲解useState、props、useRef、AbortController和pending.current。阶段完成时围绕刚完成模块进行真实面试式回顾，重点讨论设计、事务、并发和验证，不用语法填空，也不要求突然介绍整个项目。

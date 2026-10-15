# SellerPilot——你的私人智能电商运营 Agent 平台

SellerPilot 是面向跨境电商卖家的智能运营 Agent 学习项目，使用演示数据逐步实现商品管理、经营分析、政策检索与经确认的运营动作。

截至 **2026-10-15**，Week 1 后端基础已完成，Week 2 的数据能力闭环已验收：低库存、订单建表、两类 CSV 导入、订单查询、销售汇总与商品销量。三个经营查询接口本次通过 70/70 项真实 HTTP 流程检查，基础接口回归为 8 passed。当前使用 Swagger 联调，模型与 Agent 尚未接入。

## 当前进度与停点

| 模块 | 当前状态 | 说明 |
| --- | --- | --- |
| 用户、店铺、商品 | 已实现并验证 | 注册登录、JWT、商品 CRUD、价格校验、店铺归属及双账号隔离 |
| 低库存查询 | 已验收 | 指定店铺、库存阈值、排序、返回数量限制、业务函数权限校验 |
| 订单与订单明细 | 已迁移并验证 | 店内订单号唯一、明细行号唯一、复合外键、状态与金额约束 |
| 订单 CSV 导入 | 已验收 | 文件校验、UTC 转换、新增或更新、文件去重、版本递增、整批回滚 |
| 明细 CSV 导入 | 已验收 | 店内订单与 SKU 关联、数量与退款校验、新增或更新、并发去重 |
| 订单查询、销售汇总、商品销量 | 已验收 | 真实 HTTP、手算金额、日期边界、分页、多币种、缺明细与双账号隔离 |
| LLM / Agent / RAG | 尚未开始 | 后续基于已验证的业务函数接入 |

**当前停点：** `summarize_sales` 导入已补齐。三个经营查询已通过当前运行服务的真实 HTTP 验收，测试样本通过注册、建店、建商品、订单 CSV 与明细 CSV 接口写入，验证后已清理。下一步整理可重复执行的专项测试，并选择模型服务、接入第一个受权限约束的只读工具调用。模型候选为 GLM、MiMo、DeepSeek，尚未确定。

## 技术栈

Python、FastAPI、Pydantic、SQLAlchemy、PyMySQL、MySQL 8.4、Alembic、pytest、HTTPX、Docker Compose、pwdlib/Argon2、PyJWT、python-multipart。

## 项目结构

```text
SellerPilot/
├── backend/
│   ├── main.py                 # 请求/响应模型、认证依赖、HTTP 接口
│   ├── database.py             # 数据库连接、Base、get_db
│   ├── models.py               # 用户、店铺、商品、订单、明细、导入记录
│   ├── services.py             # 店铺授权与低库存业务函数
│   ├── imports.py              # 订单 CSV 解析与事务导入
│   ├── order_items_import.py   # 明细 CSV 解析、关联校验与事务导入
│   ├── analytics.py            # 订单查询、销售汇总、商品销量
│   ├── secuity.py              # 密码哈希与 JWT 工具（当前文件名）
│   ├── test_main.py            # 已纳入仓库的基础接口自动化测试
│   ├── requirements.txt
│   └── migrations/            # Alembic 配置入口与版本脚本
├── alembic.ini
├── compose.yaml                # MySQL 容器与持久化卷
├── .env.example
├── .gitignore
├── README.md
└── 技术方案.md
```

## 请求流程与函数分工

普通查询的调用路径为：HTTP 路由 → 登录认证与数据库会话依赖 → 业务函数 → 店铺授权与 SQL 查询 → 响应格式化。后续 Agent 将调用同一组业务函数，用户身份由服务端注入。

| 函数或方法 | 实现与作用 | 参与的流程 |
| --- | --- | --- |
| `get_db` | 为请求提供 Session，结束后关闭会话；不替业务函数自动提交写入 | 所有数据库接口 |
| `get_current_user` | 验证 Bearer JWT，读取当前用户 | 需要登录的接口；提供可信 user_id |
| `require_owned_store` | 同时按店铺 ID 和 owner_id 查询；查不到时抛业务异常 | 查询与导入共用的权限入口 |
| `list_low_stock_products` | 校验阈值和数量，筛选库存小于阈值的商品，按库存及 ID 排序 | 低库存 API，后续库存工具 |
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
| `list_store_orders` | 按店铺、时间、可选状态筛选，倒序排列，多取一条判断 has_more | 订单查询 API，后续订单工具 |
| `summarize_sales` | 外连接订单与明细，按币种分组，用 COUNT DISTINCT 计订单数、SUM 计数量和金额，并识别无明细订单 | 销售汇总 API，后续经营工具 |
| `list_product_sales` | 关联明细、订单和商品，按商品与订单币种分组，按销售件数排序 | 商品销量 API，后续销量工具 |

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

商品、店铺、导入及经营查询均要求有效 Bearer 令牌，未认证返回 401。新业务函数对不存在或无权访问的店铺统一返回“店铺不存在”，接口映射为 404。

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

## 迁移与验证记录

最近一次已验证的开发库和测试库迁移版本为 **`1ae0fe8ad4e4`**，当时 `alembic check` 未发现模型与表结构差异。经营查询本次未引入新表或迁移。

新增迁移：

- `d741de3672aa`：订单、订单明细，以及商品联合唯一约束。
- `1ae0fe8ad4e4`：导入记录、店铺 data_version。

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

验证记录如下；2026-10-15 新增当前运行服务的经营查询验收，并重新执行 8 项基础接口测试；其余为之前的阶段记录：

| 验证范围 | 最近记录 | 验证方式 |
| --- | --- | --- |
| 仓库基础接口测试 | 8 passed | pytest，使用独立测试库并清理测试数据 |
| 低库存 | 21/21 检查通过 | 真实 HTTP 与业务函数检查 |
| 订单模型与约束 | 20/20 检查通过 | MySQL 约束、手算金额、事务与清理检查 |
| 订单 CSV | 39/39 流程检查通过 | 迁移、真实上传、去重、回滚、权限、并发和回归流程 |
| 明细 CSV | 42/42 流程检查通过 | 真实上传、金额、跨店铺关联、并发、回滚及回归流程 |
| 经营查询示例 | 26/26 检查通过 | 之前的示例验证，使用测试库与本地临时路由 |
| 经营查询真实服务 | 70/70 流程检查通过（2026-10-15） | 实际注册登录、两类 CSV 上传、手算汇总、历史价格、退款、日期边界、分页、无明细、权限、无写入副作用和清理 |

流程检查数包含环境检查、数据清理或回归测试汇总项，不应相加为独立 pytest 用例总数。Week 2 的专项脚本和报告目前保存在本次协作的临时工作目录，尚未纳入项目仓库；执行 `test_main.py` 不会覆盖所有新增功能。专项测试使用独立临时账号或回滚事务，已清理样本。本次经营查询脚本为 `sellerpilot_analytics_verification.py`，报告为 `sellerpilot_analytics_results.json`，基础回归报告为 `sellerpilot_analytics_regression.xml`；均保存在协作工作目录。

## 下一步与两周安排

剩余工作按两周推进：本周完成数据导入、经营查询与基础 Agent；下周完成小型政策 RAG、单一确认修改动作、最小页面和交付验证。

1. 将已有专项验证整理为仓库内可重复执行的测试，并记录固定样本和手算答案。
2. 确定模型服务，验证一次真实工具调用；建立工具参数模型、注册表、服务端权限注入、调用上限与失败处理。
3. 将低库存、订单查询和销售汇总接入同一 Agent，增加有限上下文与调用记录。
4. 后续实现演示政策检索与引用、英文标题草稿及显式确认、幂等与审计、最小页面、可复现运行和录屏。

当前边界：商品和库存通过商品接口维护，尚无商品/库存 CSV；未连接真实电商平台；SKU 仍为全局唯一；未完成最新全流程空库重建演练。认证异常的独立自动化覆盖仍需补充。带订单明细的商品受外键保护，删除时的友好冲突响应也需在后续收尾中补齐。

## 开发与学习约定

继续按“用户编写和理解代码，助手检查与验证”的节奏推进。为加快进度可以提供完整文件，但每次新增函数都应说明：

1. 函数解决什么问题，属于路由、业务、校验、数据访问还是响应格式化。
2. 输入和输出是什么，参数由用户、登录状态、数据库还是其他函数提供。
3. 核心实现如何工作，为什么选择这种查询、校验或事务方式。
4. 谁调用它、它调用谁，参与请求流程中的哪一步。
5. 是否访问或修改数据库，事务由谁提交，失败如何处理。

每轮以一个能验证的小闭环为目标，并明确区分“代码已写”“示例已验证”和“项目实际接口已验收”。

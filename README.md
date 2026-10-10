# SellerPilot——你的私人智能电商运营 Agent 平台

SellerPilot 是面向跨境电商卖家的智能运营 Agent 学习项目，计划逐步实现商品管理、运营数据分析、知识库检索和 Agent 工具调用。目前处于 **Week 1：后端与数据库基础** 阶段。

## 当前进度

截至 2026-10-11，已完成：

- FastAPI 商品创建、列表、详情、完整修改（PUT）和删除接口，统一使用 MySQL 持久化。
- 商品字段：ID、SKU、名称、价格、币种、库存；支持列表数量限制。
- Pydantic 请求校验与响应模型：SKU 格式、非负价格与库存、价格最多两位小数等。
- SKU 数据库唯一约束，以及创建时的约束异常处理和事务回滚。
- SQLAlchemy 数据库连接、表模型与接口代码拆分；通过 `Depends(get_db)` 管理商品接口的 Session 生命周期。
- Alembic 迁移：创建商品表、增加库存字段，并完成现有数据库版本登记与结构检查。
- 六个自动化测试：商品生命周期（含修改与库存）、负数价格、缺少修改字段、价格精度、数据库唯一约束、模拟提交异常处理。

最新会话依赖注入调整已完成，需运行现有测试确认最终结果。用户、店铺、权限及 Agent/RAG 功能尚未实现；测试目前仍使用 `.env` 中的开发数据库，独立测试数据库待补充。

## 技术栈

Python、FastAPI、Pydantic、SQLAlchemy、PyMySQL、MySQL 8.4、Alembic、pytest、Docker Compose。

## 项目结构

```text
SellerPilot/
├── backend/
│   ├── main.py          # 请求/响应模型与 API
│   ├── database.py      # 数据库连接、Base 和 get_db
│   ├── models.py        # Product 表模型
│   ├── test_main.py     # 自动化测试
│   ├── requirements.txt
│   └── migrations/     # Alembic 配置入口与版本脚本
├── alembic.ini
├── compose.yaml         # MySQL 容器与持久化卷
├── .env.example         # 环境变量模板
├── .gitignore
└── 跨境电商卖家Agent技术方案.md
```

## 本地运行

以下命令从项目根目录执行，使用 PowerShell。

创建并激活虚拟环境，安装依赖（已有 `.venv` 时跳过创建）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m pip install alembic pytest httpx
```

复制 `.env.example` 为 `.env`，填写数据库密码。已有 `.env` 时保留现有配置；`.env` 不提交到 Git。默认连接本机端口 `3307`。

启动 MySQL，等待数据库就绪后，对空数据库执行迁移：

```powershell
docker compose up -d mysql
python -m alembic upgrade head
```

已有数据库已登记迁移版本时，`upgrade head` 仅执行尚未应用的迁移。`stamp head` 只登记版本，不建表，不适用于初始化空数据库。

启动后端：

```powershell
cd backend
python -m uvicorn main:app --reload
```

- [Swagger API 文档](http://127.0.0.1:8000/docs)
- [数据库连接检查](http://127.0.0.1:8000/database-check)

## 商品 API

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | `/products` | 创建商品 |
| GET | `/products?limit=10` | 商品列表，limit 范围 1～100 |
| GET | `/products/{sku}` | 查询单件商品 |
| PUT | `/products/{sku}` | 修改商品，必须提交 title、price、currency、stock |
| DELETE | `/products/{sku}` | 删除商品，成功返回 204 |

创建时 currency 默认 USD、stock 默认 0；SKU 不通过修改接口变更。响应价格使用十进制字符串表示。

## 验证

在项目根目录执行，MySQL 需保持运行：

```powershell
python -m pytest backend/test_main.py -q
python -m alembic current
python -m alembic check
```

预期六个测试通过，迁移版本位于 head，模型与数据库无结构差异。模拟异常测试验证错误处理；真实数据库唯一约束由另一个测试验证，目前尚未覆盖并发创建场景。

## 下一步

1. 隔离测试数据库，避免测试操作开发数据。
2. 增加用户、店铺与访问权限。
3. 逐步接入运营工具、LLM、Agent 与知识库检索。

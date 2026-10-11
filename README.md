# SellerPilot——你的私人智能电商运营 Agent 平台

SellerPilot 是面向跨境电商卖家的智能运营 Agent 学习项目，计划逐步实现商品管理、运营数据分析、知识库检索和 Agent 工具调用。目前处于 **Week 1：后端与数据库基础** 阶段。

## 当前进度

截至 2026-10-11，已完成：

- FastAPI 商品增删改查、库存管理、价格精度校验及响应模型，数据统一保存到 MySQL。
- 店铺创建、列表与详情查询；商品通过外键关联店铺，并支持按店铺筛选。
- 用户注册、Argon2 密码哈希、JWT 登录及 `/auth/me` 当前用户查询。
- 店铺绑定登录用户；店铺接口要求认证，仅返回当前用户拥有的店铺。
- SQLAlchemy 连接、模型和接口拆分，通过 `Depends(get_db)` 管理会话；支持约束异常处理与事务回滚。
- Alembic 管理商品、库存、店铺、用户及关联字段的结构迁移。
- 测试使用独立的 `sellerpilot_test` 数据库；现有七个测试覆盖商品流程、校验、约束异常及店铺筛选。

当前停点：店铺权限已通过双账号手动验证；商品接口尚未检查用户权限。七个测试曾在店铺权限改造前通过，原店铺筛选测试尚未添加登录凭证，需更新后重新验证。注册、登录和 `/auth/me` 已手动验证，尚未加入自动化测试。Agent/RAG 功能尚未开始。

## 技术栈

Python、FastAPI、Pydantic、SQLAlchemy、PyMySQL、MySQL 8.4、Alembic、pytest、Docker Compose、pwdlib/Argon2、PyJWT。

## 项目结构

```text
SellerPilot/
├── backend/
│   ├── main.py          # 请求/响应模型与 API
│   ├── database.py      # 数据库连接、Base 和 get_db
│   ├── models.py        # 商品、店铺、用户表模型
│   ├── secuity.py       # 密码哈希与 JWT 工具（当前文件名）
│   ├── test_main.py     # 自动化测试
│   ├── requirements.txt
│   └── migrations/      # Alembic 配置入口与版本脚本
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

复制 `.env.example` 为 `.env`，填写数据库密码。已有 `.env` 时保留现有配置；`.env` 不提交到 Git。默认连接本机端口 `3307`。另外生成 JWT 签名密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

将输出填入 `.env` 的 `JWT_SECRET_KEY`，不要提交实际密钥。

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

## API

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | `/products` | 创建商品 |
| GET | `/products?limit=10&store_id=1` | 商品列表，store_id 可省略，limit 范围 1～100 |
| GET | `/products/{sku}` | 查询单件商品 |
| PUT | `/products/{sku}` | 修改商品，必须提交 title、price、currency、stock |
| DELETE | `/products/{sku}` | 删除商品，成功返回 204 |
| POST | `/stores` | 为当前登录用户创建店铺 |
| GET | `/stores` | 当前用户的店铺列表 |
| GET | `/stores/{store_id}` | 查询自己的店铺，他人的店铺返回 404 |
| POST | `/auth/register` | 注册用户 |
| POST | `/auth/login` | 登录，返回有效期为 30 分钟的令牌 |
| GET | `/auth/me` | 校验令牌并返回当前用户 |

创建时 currency 默认 USD、stock 默认 0，store_id 可省略；SKU 不通过修改接口变更。响应价格使用十进制字符串表示。

店铺接口及 `/auth/me` 使用 Bearer 令牌认证：先登录，再在 Swagger 的 Authorize 中粘贴 access_token。现有无归属的旧店铺不会出现在用户店铺列表中；商品权限仍待补齐。

## 验证

测试使用同一 MySQL 实例中的 `sellerpilot_test` 数据库，需要先创建该库并授权应用用户。之后用已有迁移建立或更新测试表结构：

```powershell
python -c "import os; os.environ['DB_NAME'] = 'sellerpilot_test'; from alembic.config import main; main(['upgrade', 'head'])"
```

在项目根目录执行，MySQL 需保持运行，且 `.env` 中应配置 JWT 密钥：

```powershell
python -m pytest backend/test_main.py -q
python -m alembic current
python -m alembic check
```

迁移应位于 head，模型与数据库应无结构差异。当前店铺筛选测试缺少认证，预计会在创建店铺时收到 401；待权限相关测试更新后再确认全部通过。模拟异常测试与真实数据库唯一约束测试分别验证错误处理和数据库约束，目前尚未覆盖并发创建场景。

## 下一步

1. 为商品创建、查询、修改和删除补齐用户归属检查。
2. 更新测试登录凭证，验证两个账号之间的店铺与商品访问隔离。
3. 明确旧的无归属数据处理方式，完成后端基础阶段验收。
4. 接入运营工具、LLM、Agent 与知识库检索。

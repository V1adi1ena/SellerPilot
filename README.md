# SellerPilot——你的私人智能电商运营Agent平台

SellerPilot 是一个面向跨境电商卖家的智能运营 Agent 学习项目。项目计划逐步实现商品管理、运营数据分析、知识库检索和 Agent 自动化能力。

## 当前进度

目前处于 **Week 1：后端与数据库基础** 阶段，已经完成：

- 使用 FastAPI 创建后端服务和 Swagger API 文档
- 学习查询参数、路径参数及参数校验
- 使用 Pydantic 定义商品请求模型
- 实现基于内存的商品创建、查询、列表和删除接口
- 编写并通过商品生命周期测试
- 使用 Docker Compose 启动 MySQL 8.4
- 使用 SQLAlchemy 和 PyMySQL 连接 MySQL
- 定义 `Product` 数据表模型
- 实现向 MySQL 写入商品的临时接口

当前商品接口仍同时存在内存版和数据库版，后续会逐步统一为 MySQL 持久化实现。

## 项目结构

```text
SellerPilot/
├── backend/
│   ├── main.py          # FastAPI 应用、商品接口和数据库模型
│   ├── requirements.txt # Python 依赖
│   └── test_main.py     # 商品接口测试
├── .env.example         # 环境变量示例
├── .gitignore
├── compose.yaml         # MySQL 容器配置
└── 跨境电商卖家Agent技术方案.md
```

## 本地运行

复制 `.env.example` 为 `.env`，填写数据库密码后启动 MySQL：

```powershell
docker compose up -d mysql
```

安装依赖并启动后端：

```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

打开以下地址查看和调试接口：

- API 文档：http://127.0.0.1:8000/docs
- 数据库连接检查：http://127.0.0.1:8000/database-check

运行现有测试：

```powershell
cd backend
pytest test_main.py -q
```

## 下一步

1. 从 MySQL 查询商品列表和商品详情
2. 使用 MySQL 完成商品删除
3. 将内存接口统一迁移到数据库
4. 更新自动化测试
5. 引入 Alembic 管理数据库结构变更

# SellerPilot 前端

截至2026-10-18，已接入登录选店及五模块工作区：运营问答、经营数据、商品与库存、CSV导入、标题审核。用户已逐步确认成功，真实GLM提问、追问与引用已确认跑通。实际项目生产构建通过，开发端口为5188；本地演示版功能已贯通，生产部署尚未验收。

## 启动与停止

后端由用户在可见终端保持运行，地址为127.0.0.1:8000。另开PowerShell终端：

```powershell
cd D:\Project\SellerPilot\frontend
npm ci
npm run dev
```

打开 [店铺工作台](http://127.0.0.1:5188)。端口在vite.config.ts中设为5188，strictPort使端口占用时直接报错。停止前端时在该终端按Ctrl+C。已有依赖且锁文件未变时，后续只需npm run dev。生产构建命令为npm run build；当前开发代理不代替生产部署配置。

使用已注册账号；注册、创建店铺和商品新增/编辑/删除目前仍使用Swagger。订单与明细CSV已可从前端导入，标题修改走草稿审核确认。后端运行和迁移见 [项目README](../README.md)。

## 文件与调用关系

| 文件 | 职责 |
| --- | --- |
| index.html / src/main.tsx | 提供root节点，挂载React App并加载样式 |
| src/App.tsx | 登录表单、账号和店铺加载、当前店铺选择、退出及登录过期处理 |
| src/StoreWorkspace.tsx | 导航、首次打开时挂载、同店铺保留状态与切店重建 |
| src/AgentChat.tsx | 当前店铺问答、会话ID、发送状态、引用展示与请求清理 |
| src/ProductTitles.tsx | 生成草稿、前后对照、审核确认、冲突与回执查询 |
| src/CsvImports.tsx | FormData上传、重复回执、行级错误和文件校验 |
| src/StoreOperations.tsx | 北京时间日期筛选、分币种汇总、订单状态与分页 |
| src/ProductInventory.tsx | 商品与后端低库存查询，披露100条限制 |
| src/workspace.css及各模块CSS | 导航、表格和手机布局 |
| src/api.ts | fetch公共封装、JWT、错误类及登录、问答、草稿、导入和经营查询API封装 |
| src/style.css | 页面布局、问答展示和手机适配 |
| vite.config.ts | 开发端口5188、/api请求代理 |
| package.json / package-lock.json / tsconfig.json | 依赖、命令、安装版本与类型检查 |

```text
登录表单 -> handleLogin -> login -> request -> FastAPI登录接口
保存JWT -> App的useEffect -> getCurrentUser/getStores -> 显示店铺
选择店铺 -> StoreWorkspace -> AgentChat -> handleSend -> askAgent -> request -> 后端Agent
回答成功 -> 保存conversation_id并追加问答 -> 下次提问续接会话
```

## API与函数

| 函数 | 输入与输出、所在流程 |
| --- | --- |
| request<T> | 接收路径和fetch选项，附加JWT、检查HTTP状态，返回JSON或抛错；T只提供开发期类型提示，不校验真实JSON |
| login | 用户名/密码 -> POST /auth/login -> JWT |
| getCurrentUser | 取消信号 -> GET /auth/me -> User |
| getStores | 取消信号 -> GET /stores?limit=100 -> Store数组；店铺归属由后端控制 |
| askAgent | 店铺ID、问题、取消信号、可选会话ID -> POST /store/{store_id}/agent/query -> AgentReply |
| handleLogin / handleLogout | 保存JWT和清空密码，或清除标签页JWT与账号、店铺状态 |
| App的useEffect | 登录或刷新店铺时并行加载身份和店铺，清理过时的读取请求 |
| AgentChat | 接收当前店铺及登录过期回调，保存聊天状态并返回JSX页面 |
| handleSend | 清理问题空白、阻止重复发送、请求回答；成功后追加问答、保存会话ID，失败保留输入与已有问答，401交父组件退出 |
| handleNewConversation | 清空页面问答、输入、错误和会话ID；不删除后端已保存会话 |

浏览器发送 `/api/...`，开发代理去掉/api后转发到127.0.0.1:8000。Agent接口沿用单数store路径，其余已有店铺接口多为复数stores。首次提问省略conversation_id；成功后记住后端返回值，追问携带该ID。页面不上传一整份任意聊天历史，后端自行读取有限历史。

## AgentChat状态与关键语法

| 项目 | 含义 |
| --- | --- |
| props | 父组件传入的store和onSessionExpired回调 |
| useState | 保存question、turns、conversationId、sending和error；更新函数安排重新渲染，当前函数里的旧值不会立即改写 |
| useRef / pending | 跨重新渲染保留同一个引用容器，修改current不会触发页面重画 |
| pending.current | 保存当前请求的AbortController；非空时阻止再次发送 |
| controller | 每次请求创建的浏览器控制器，signal传给fetch，abort发出取消通知 |
| effect清理函数 | 组件卸载时调用pending.current?.abort，取消浏览器等待；代码也检查aborted以忽略旧结果 |
| 工作区key | 按用户ID和店铺ID确定整个工作区身份，切店时清理所有模块；同店铺切模块用hidden保留状态 |

setTurns(previous => [...previous, newTurn])创建新的问答数组。turns只追加成功问答；发送失败时保留输入。页面用普通文本展示回答和原文，details/summary负责展开引用。政策资料不足时显示后端提示及标记，引用合法不等于答案语义一定准确。

## 登录与会话边界

JWT保存在当前标签页sessionStorage中，刷新后重新验证身份，不存密码；模型API Key只留在后端.env。退出只清理浏览器状态，已签发JWT按后端到期规则失效，没有服务端撤销功能。浏览器存储按来源区分，继续使用127.0.0.1:5188。

刷新页面、退出或切换店铺时清空当前页面聊天；成功刷新同一店铺列表则保留聊天组件。后端已保存的会话仍存在，但目前没有历史列表或恢复功能。“新对话”只让下一次请求不带旧会话ID。

AbortController停止浏览器等待，不保证终止后端已经开始的模型请求或事务。整个问答请求没有客户端幂等ID，网络中断后人工重试可能再次运行。当前展示一次完整HTTP回复，尚未接SSE逐字输出。

## 模块状态与刷新

handleNavigate更新activePanel，并通过函数式setVisited记录已打开模块。未访问的模块不挂载；访问后只隐藏，不卸载，所以聊天、草稿、核对勾选、文件选择和查询结果可在切模块后继续使用。换店铺或退出会卸载整个工作区，取消浏览器等待；不保证撤销后端已收到的写操作。

导入成功后，在经营数据页重新查询；应用标题后，在库存页点击查询获取当前标题。没有自动跨模块刷新，也没有URL路由或浏览器历史导航。页面刷新不会恢复聊天与草稿界面。

CSV的文件名与体积在前端快速校验，内容、归属、去重和事务在后端处理。日期输入统一解释为北京时间，结束日期转为下一天零点。销售只含已付款与已发货，不受订单列表状态筛选影响。库存严格小于阈值，商品接口最多100条，没有真实总数或分页。

## 验证与当前停点

2026-10-18在实际frontend运行npm run build通过；当前开发服务器App.tsx和StoreWorkspace.tsx返回200，未登录/api/stores经代理返回401。

用户已确认各功能阶段成功，包含真实GLM提问、追问和政策引用。各阶段浏览器自动化使用模拟接口：经营查询7组、库存7组、导航9组；另有登录、聊天、标题和导入的历史浏览器检查。不同组数不可相加为独立测试用例总数，也不等于正式模型评测。

模拟脚本和截图仍在协作目录。新后端业务闭环已纳入backend/test_acceptance.py，使用真实独立MySQL测试库、进程内ASGI HTTP请求和模拟模型，具体范围见 [演示验收](../演示验收.md)。本轮没有重新运行真实GLM全套评测，也没有从空库验收生产部署。

前端主体已完成，下一步按演示清单连贯运行并准备项目讲解。

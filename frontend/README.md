# SellerPilot 前端

截至2026-10-17，已接入账号登录、当前用户、自己的店铺列表，以及当前店铺的Agent问答、追问和政策引用。用户已确认开发页面在5188运行成功；聊天组件已加入项目，真实GLM端到端页面验收仍待明确记录。商品管理、CSV上传与标题草稿确认页面尚待接入。

## 启动与停止

后端由用户在可见终端保持运行，地址为127.0.0.1:8000。另开PowerShell终端：

```powershell
cd D:\Project\SellerPilot\frontend
npm ci
npm run dev
```

打开 [店铺工作台](http://127.0.0.1:5188)。端口在vite.config.ts中设为5188，strictPort使端口占用时直接报错。停止前端时在该终端按Ctrl+C。已有依赖且锁文件未变时，后续只需npm run dev。生产构建命令为npm run build；当前开发代理不代替生产部署配置。

使用已注册账号；注册、创建店铺、商品维护和CSV导入目前仍使用后端Swagger。后端运行和迁移见 [项目README](../README.md)。

## 文件与调用关系

| 文件 | 职责 |
| --- | --- |
| index.html / src/main.tsx | 提供root节点，挂载React App并加载样式 |
| src/App.tsx | 登录表单、账号和店铺加载、当前店铺选择、退出及登录过期处理 |
| src/AgentChat.tsx | 当前店铺问答、会话ID、发送状态、引用展示与请求清理 |
| src/api.ts | fetch公共封装、JWT、错误类及四个API包装函数 |
| src/style.css | 页面布局、问答展示和手机适配 |
| vite.config.ts | 开发端口5188、/api请求代理 |
| package.json / package-lock.json / tsconfig.json | 依赖、命令、安装版本与类型检查 |

```text
登录表单 -> handleLogin -> login -> request -> FastAPI登录接口
保存JWT -> App的useEffect -> getCurrentUser/getStores -> 显示店铺
选择店铺 -> AgentChat -> handleSend -> askAgent -> request -> 后端Agent
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
| 组件key | 按用户ID和店铺ID确定聊天组件身份，切店时重建状态，避免复用上家店铺会话 |

setTurns(previous => [...previous, newTurn])创建新的问答数组。turns只追加成功问答；发送失败时保留输入。页面用普通文本展示回答和原文，details/summary负责展开引用。政策资料不足时显示后端提示及标记，引用合法不等于答案语义一定准确。

## 登录与会话边界

JWT保存在当前标签页sessionStorage中，刷新后重新验证身份，不存密码；模型API Key只留在后端.env。退出只清理浏览器状态，已签发JWT按后端到期规则失效，没有服务端撤销功能。浏览器存储按来源区分，继续使用127.0.0.1:5188。

刷新页面、退出或切换店铺时清空当前页面聊天；成功刷新同一店铺列表则保留聊天组件。后端已保存的会话仍存在，但目前没有历史列表或恢复功能。“新对话”只让下一次请求不带旧会话ID。

AbortController停止浏览器等待，不保证终止后端已经开始的模型请求或事务。整个问答请求没有客户端幂等ID，网络中断后人工重试可能再次运行。当前展示一次完整HTTP回复，尚未接SSE逐字输出。

## 验证与下次停点

已通过TypeScript检查和Vite生产构建。前端基础、聊天各有九组浏览器流程检查；账号与Agent数据使用模拟接口，覆盖错误、401、追问、切店旧回复隔离、引用纯文本展示、重复提交和手机布局。基础阶段另对实际后端验证了未登录请求经代理返回401。

报告和截图位于本次协作目录的sellerpilot_frontend_verification与sellerpilot_frontend_chat_verification，尚未纳入项目仓库。上述结果不是完整真实GLM页面验收，本轮文档更新没有重跑测试。

下次先用真实账号检查低库存提问、追问、演示政策引用与切店；随后接商品列表和标题草稿生成、预览、明确确认页面。

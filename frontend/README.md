# SellerPilot 前端第一步：登录与店铺选择

本阶段接入现有JSON登录接口、当前用户接口和自己的店铺列表。下一阶段会在已选店铺下加入运营问答与标题草稿确认。

## 放入项目并启动

将本目录的源文件放到 `D:/Project/SellerPilot/frontend/`，保留src目录结构。node_modules、dist和本次协作目录中的验证脚本不用复制。仓库原有.gitignore已忽略node_modules和dist。

本机已核对Node v24.15.0满足所锁定Vite的版本要求。保持自己终端中的后端在127.0.0.1:8000运行，再在另一个PowerShell终端执行：

```powershell
cd D:\Project\SellerPilot\frontend
npm ci
npm run dev
```

打开 http://127.0.0.1:5173 。结束前端时，在这个终端按Ctrl+C。端口固定且已设置strictPort，5173被占用时会明确报错。

使用已有注册账号登录。此阶段还没有注册与创建店铺页面，需要账号和店铺已在Swagger中创建。

## 最值得先读的文件

| 文件 | 作用 |
| --- | --- |
| src/api.ts | 封装fetch、JWT请求头和后端错误；提供login/getCurrentUser/getStores |
| src/App.tsx | 登录表单、身份加载、店铺列表、选中状态与退出 |
| src/style.css | 页面布局、颜色、控件和手机布局 |
| vite.config.ts | 开发端口及/api到后端的代理 |

其余文件是运行入口与依赖配置：index.html提供root节点；src/main.tsx将App挂载到root；package.json定义依赖和命令；package-lock.json锁定实际安装；tsconfig.json约束TypeScript编译。

## 每个函数参与什么

| 函数 | 输入、输出、实现与调用位置 |
| --- | --- |
| request<T> | 输入接口路径和fetch选项，读取sessionStorage中的JWT，设置Authorization，发送/api请求，检查HTTP状态；返回JSON或抛ApiError。所有API包装函数共用它。T提供开发期返回类型提示，不对实际JSON进行运行时校验。 |
| login | 输入用户名、密码，POST JSON到/auth/login，返回access_token/token_type；handleLogin调用。 |
| getCurrentUser | 输入取消信号，GET/auth/me，返回User；登录后或页面恢复时调用。 |
| getStores | 输入取消信号，GET/stores?limit=100，返回Store列表；后端负责用户隔离，页面不根据owner_id自己认定权限。 |
| App | React组件，维护账号、店铺、选中项、加载状态与错误，返回页面结构；main.tsx挂载它。 |
| handleLogin | 接收表单提交事件，阻止浏览器默认跳页，调用login；成功只保存JWT，清空密码，更新token状态。 |
| handleLogout | 清除当前标签页JWT及组件里的用户、店铺和选择状态，切回登录页；不调用服务端JWT撤销接口。 |

App中的useEffect在token或刷新计数变化时重新读取身份和店铺。两个查询可独立进行，所以用Promise.all一起等待；AbortController在退出或新一轮加载时取消旧请求，防止旧结果覆盖新状态。React开发模式StrictMode可能执行一次“启动、清理、再启动”，这里的查询是只读且支持取消的。

useState保存页面状态；调用setToken、setStores、setSelectedId等更新函数后，React会重新渲染相应界面。选店铺按钮只更新selectedId，目前不发起经营查询或修改。

## 请求和身份

```text
浏览器 fetch /api/auth/login
  -> Vite移除/api，转发到127.0.0.1:8000/auth/login
  -> FastAPI返回JWT
  -> 当前标签页sessionStorage保存JWT
  -> 后续请求附Authorization: Bearer ...
  -> 后端校验JWT并返回该用户的店铺
```

模型API Key始终留在后端.env，前端只持有登录JWT。sessionStorage用于在同一标签页刷新后继续使用JWT，不保存密码；打开页面时仍向后端验证身份，401会清除凭证并要求重新登录。退出仅清除浏览器当前登录状态，已签发JWT仍按原后端规则到期失效。关闭标签页会结束该标签页的存储会话；浏览器恢复或复制标签页行为可能影响存储恢复，不能把关页视为服务端撤销。

开发代理让前端在同源/api地址发请求，本轮不需要修改后端CORS。该代理只供Vite开发服务使用，生产部署还需后续配置同域API转发。浏览器保存的JWT按来源隔离，请始终使用同一个127.0.0.1:5173地址。

## 验收

1. 已有账号登录后能看到自己的店铺；用户名/密码错误时留在登录页并显示后端提示。
2. 多家店铺可切换选中项；一家店铺会自动选中。没有店铺时显示空状态。当前最多显示前100家店铺，不声称是全部店铺。
3. 刷新页面后，未过期JWT自动重新验证；店铺选择本身没有持久化，多店铺时需要重新选择。
4. 退出后回到登录表单，原用户与店铺不再显示。
5. JWT过期返回401后要求重新登录；服务暂不可用时显示错误，可以刷新店铺重试。

本阶段已通过TypeScript检查和Vite生产构建。浏览器验证结果及截图位于协作工作目录的sellerpilot_frontend_verification目录，具体区分真实后端代理检查与模拟账号数据场景。暂存前端未安装到实际项目，本轮不改后端代码。

## 官方参考

- Vite入门：https://vite.dev/guide/
- React与TypeScript：https://react.dev/learn/typescript

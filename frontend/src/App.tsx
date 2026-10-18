import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, getCurrentUser, getStores, login, TOKEN_KEY } from './api'
import type { Store, User } from './api'
import AgentChat from './AgentChat'
import ProductTitles from './ProductTitles'
import CsvImports from './CsvImports'

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) ?? '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [user, setUser] = useState<User | null>(null)
  const [stores, setStores] = useState<Store[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const selectedStore = stores.find((store) => store.id === selectedId)

  // 登录或刷新后，重新向后端验证身份并读取店铺。取消已过期的请求，避免覆盖新状态。
  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    setLoading(true)
    setError('')
    Promise.all([getCurrentUser(controller.signal), getStores(controller.signal)])
      .then(([currentUser, ownStores]) => {
        if (controller.signal.aborted) return
        setUser(currentUser)
        setStores(ownStores)
        setSelectedId((current) => ownStores.some((store) => store.id === current)
          ? current : ownStores.length === 1 ? ownStores[0].id : null)
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return
        if (cause instanceof ApiError && cause.status === 401) {
          sessionStorage.removeItem(TOKEN_KEY)
          setToken('')
          setUser(null)
          setStores([])
          setSelectedId(null)
          setError('登录已过期，请重新登录。')
        } else {
          setError(cause instanceof Error ? cause.message : '加载店铺失败，请重试。')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [token, refresh])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await login(username.trim(), password)
      sessionStorage.setItem(TOKEN_KEY, result.access_token)
      setPassword('')
      setToken(result.access_token)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '登录失败，请重试。')
    } finally {
      setBusy(false)
    }
  }

  function handleLogout() {
    sessionStorage.removeItem(TOKEN_KEY)
    setToken('')
    setPassword('')
    setUser(null)
    setStores([])
    setSelectedId(null)
    setError('')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="SellerPilot 首页">
          <span className="brand-mark" aria-hidden="true">S</span>
          <span>SellerPilot<small>店铺工作台</small></span>
        </a>
        {token && <div className="account">
          <span>{user?.username ?? '正在验证账号'}</span>
          <button className="quiet-button" onClick={handleLogout}>退出登录</button>
        </div>}
      </header>

      <main>
        {!token ? (
          <section className="login-layout">
            <div className="login-intro">
              <div className="route-line" aria-hidden="true"><span /><span /><span /></div>
              <h1>从你的店铺，<br />开始今天的运营。</h1>
              <p>查看经营数据，查阅政策依据，审核每一次标题修改。</p>
            </div>
            <form className="login-form" onSubmit={handleLogin}>
              <h2>登录 SellerPilot</h2>
              <p>使用已注册的账号进入工作台。</p>
              <label htmlFor="username">用户名</label>
              <input id="username" name="username" autoComplete="username" required
                minLength={3} maxLength={50} value={username}
                onChange={(event) => setUsername(event.target.value)} disabled={busy} />
              <label htmlFor="password">密码</label>
              <input id="password" name="password" type="password" autoComplete="current-password"
                required maxLength={128} value={password}
                onChange={(event) => setPassword(event.target.value)} disabled={busy} />
              {error && <p className="error-message" role="alert">{error}</p>}
              <button className="primary-button" type="submit" disabled={busy}>
                {busy ? '正在登录…' : '登录工作台'}
              </button>
            </form>
          </section>
        ) : (
          <section className="workspace">
            <div className="section-heading">
              <div><h1>我的店铺</h1><p>选择本次工作的店铺。</p></div>
              <button className="quiet-button" disabled={loading}
                onClick={() => setRefresh((value) => value + 1)}>刷新店铺</button>
            </div>
            {error && <p className="error-message" role="alert">{error}</p>}
            {loading ? <p className="empty-state" role="status">正在加载店铺…</p> : !error && <>
              {stores.length === 0 ? (
                <p className="empty-state">你还没有可用店铺。创建店铺后，可在这里刷新列表。</p>
              ) : (
                <div className="store-list" aria-label="选择店铺">
                  {stores.map((store) => (
                    <button className={`store-option ${selectedId === store.id ? 'selected' : ''}`}
                      key={store.id} aria-pressed={selectedId === store.id}
                      onClick={() => setSelectedId(store.id)}>
                      <span className="store-symbol" aria-hidden="true">{store.platform === 'amazon' ? 'a' : 's'}</span>
                      <span className="store-copy"><strong>{store.name}</strong>
                        <small>{store.platform === 'amazon' ? 'Amazon' : store.platform === 'shopify' ? 'Shopify' : store.platform}</small>
                      </span>
                      <span className="selection-label">{selectedId === store.id ? '已选择' : '选择店铺'}</span>
                    </button>
                  ))}
                </div>
              )}
              {stores.length === 100 && <p className="hint">当前显示前100家店铺。</p>}
              {selectedStore && <aside className="store-context" aria-label="当前店铺">
                <span className="context-label">当前店铺</span>
                <h2>{selectedStore.name}</h2>
                <p>{selectedStore.platform === 'amazon' ? 'Amazon' : selectedStore.platform === 'shopify' ? 'Shopify' : selectedStore.platform}</p>
              </aside>}
            </>}
            {selectedStore && user && <AgentChat
              key={`${user.id}:${selectedStore.id}`}
              store={selectedStore}
              onSessionExpired={() => {
                handleLogout()
                setError('登录已过期，请重新登录。')
              }}
            />}
            {selectedStore && user && <ProductTitles
              key={`${user.id}:${selectedStore.id}`}
              store={selectedStore}
              onSessionExpired={() => {
                handleLogout()
                setError('登录已过期，请重新登录。')
              }}
            />}
            {selectedStore && user && <CsvImports
              key={`${user.id}:${selectedStore.id}`}
              store={selectedStore}
              onSessionExpired={() => {
                handleLogout()
                setError('登录已过期，请重新登录。')
              }}
            />}
          </section>
        )}
      </main>
      <footer>SellerPilot<span>每项运营工作，都从明确店铺开始。</span></footer>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, getLowStockProducts, getProducts } from './api'
import type { Product, Store } from './api'
import './inventory.css'

interface Props {
  store: Store
  onSessionExpired: () => void
}

type QueryMode = 'products' | 'low-stock'

interface InventoryResult {
  // 记录结果使用的条件。用户编辑表单时，不改变已展示结果的含义。
  mode: QueryMode
  threshold: number | null
  products: Product[]
}

export default function ProductInventory({ store, onSessionExpired }: Props) {
  const [mode, setMode] = useState<QueryMode>('products')
  // 用字符串保存输入，允许用户暂时清空输入框；不能把空字符串直接当成0。
  const [thresholdText, setThresholdText] = useState('10')
  const [result, setResult] = useState<InventoryResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const pending = useRef<AbortController | null>(null)
  const criteriaChanged = result !== null && (
    result.mode !== mode || (mode === 'low-stock' && (
      thresholdText.trim() === '' || Number(thresholdText) !== result.threshold
    ))
  )

  async function loadInventory(queryMode: QueryMode, threshold = 10) {
    // ref同步加锁，阻止按钮尚未禁用时的快速重复提交。
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setLoading(true)
    setError('')
    try {
      // 两种查询共用展示和错误处理，但分别调用对应的后端接口。
      // 低库存必须由后端筛选，不能在已截断的商品列表里用filter代替。
      const products = queryMode === 'products'
        ? await getProducts(store.id, controller.signal)
        : await getLowStockProducts(store.id, threshold, controller.signal)
      // 切换店铺、退出登录后，不把旧店铺的迟到响应写回页面。
      if (controller.signal.aborted) return
      setResult({ mode: queryMode, threshold: queryMode === 'low-stock' ? threshold : null, products })
    } catch (cause) {
      if (controller.signal.aborted) return
      setResult(null)
      if (cause instanceof ApiError && cause.status === 401) onSessionExpired()
      else setError(cause instanceof Error ? cause.message : '查询失败，请稍后重试。')
    } finally {
      // 只释放本次持有的锁；旧请求结束时不能清掉新请求的控制器。
      if (pending.current === controller) {
        pending.current = null
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    // 进入当前店铺时先显示商品列表，之后由用户主动选择条件并查询。
    void loadInventory('products')
    return () => {
      pending.current?.abort()
      pending.current = null
    }
  }, [store.id])

  function handleQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending.current) return
    let threshold = 10
    if (mode === 'low-stock') {
      threshold = Number(thresholdText)
      // Number('')是0，所以单独拒绝空输入；安全整数检查避免数字转换丢失精度。
      if (thresholdText.trim() === '' || !Number.isSafeInteger(threshold) || threshold < 0) {
        setError('低库存阈值必须是大于或等于0的安全整数。')
        return
      }
    }
    void loadInventory(mode, threshold)
  }

  return (
    <section className="inventory-panel" aria-labelledby="inventory-heading" aria-busy={loading}>
      <div className="chat-heading">
        <div><h2 id="inventory-heading">商品与库存</h2><p>当前店铺：{store.name}</p></div>
      </div>
      <form className="inventory-form" onSubmit={handleQuery}>
        <label>查询范围<select value={mode} disabled={loading}
          onChange={(event) => setMode(event.target.value as QueryMode)}>
          <option value="products">商品列表</option><option value="low-stock">低库存</option>
        </select></label>
        {mode === 'low-stock' && <label>低库存阈值<input type="number" required min="0" step="1"
          max={Number.MAX_SAFE_INTEGER} value={thresholdText} disabled={loading}
          onChange={(event) => setThresholdText(event.target.value)} /></label>}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? '正在查询…' : '查询库存'}
        </button>
      </form>
      <p className="hint">低库存指库存严格小于阈值，等于阈值的商品不会入选。阈值为0时不会查询到库存为0的商品。</p>
      <p className="hint">每次最多显示100条。商品列表按商品编号排列，低库存按库存从少到多排列。</p>
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading && <p className="chat-progress" role="status">正在读取当前店铺的库存…</p>}
      {criteriaChanged && <p className="inventory-warning" role="status">条件已修改，请点击查询更新结果。</p>}
      {result && <>
        <p className="inventory-context">已查询：{result.mode === 'products' ? '商品列表' : `库存小于 ${result.threshold}`}；本次返回 {result.products.length} 条。</p>
        {result.products.length === 100 && <p className="inventory-warning" role="status">
          已达到100条显示上限，可能还有未展示的商品。本页条数不代表店铺商品总数。
        </p>}
        {result.products.length === 0 ? <p className="hint">
          {result.mode === 'products' ? '当前店铺暂无商品。' : '没有符合该阈值的商品；这不表示店铺没有商品。'}
        </p> : <div className="inventory-table" role="region" aria-label="商品库存表" tabIndex={0}>
          <table><thead><tr><th>SKU</th><th>商品名称</th><th>库存</th><th>单价</th><th>币种</th></tr></thead>
            <tbody>{result.products.map((product) => <tr key={product.id}>
              <td>{product.sku}</td><td className="inventory-title">{product.title}</td>
              <td><span className={product.stock === 0 ? 'inventory-zero' : undefined}>
                {product.stock}{product.stock === 0 && '（缺货）'}
              </span></td>
              <td>{product.price}</td><td>{product.currency}</td>
            </tr>)}</tbody>
          </table>
        </div>}
      </>}
      <p className="hint inventory-note">修改商品或应用标题后，点击查询读取最新数据。导入订单不会扣减这里的库存。</p>
    </section>
  )
}

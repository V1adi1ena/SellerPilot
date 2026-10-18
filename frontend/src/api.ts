export const TOKEN_KEY = 'sellerpilot_token'

export interface User {
  id: number
  username: string
}

export interface Store {
  id: number
  name: string
  platform: string
  owner_id: number | null
}

interface LoginResult {
  access_token: string
  token_type: string
}

export interface CsvIssue {
  row: number | null
  field: string
  reason: string
}

export class ApiError extends Error {
  // 普通接口没有行级错误时使用空数组；CSV接口保留明细供页面逐条展示。
  constructor(public status: number, message: string, public issues: CsvIssue[] = []) {
    super(message)
  }
}

// 统一发送JWT并处理HTTP错误。类型参数T描述接口预期返回的数据形状。
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  // JSON请求仍设置JSON类型；FormData由浏览器生成multipart类型和boundary。
  // boundary是文件各部分的分隔标识，手动设置JSON头或仅写multipart都会破坏解析。
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`/api${path}`, { ...options, headers })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    throw new Error('无法连接服务，请检查网络后重试。')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    // FastAPI普通错误的detail是字符串；CSV错误是包含message/errors的对象。
    const detail = payload?.detail
    const message = typeof detail === 'string' ? detail
      : typeof detail?.message === 'string' ? detail.message
      : `请求失败（${response.status}），请稍后重试。`
    // 保留后端提供的行号、字段和原因，而不是把整个对象压成一条笼统提示。
    const issues: CsvIssue[] = Array.isArray(detail?.errors) ? detail.errors : []
    throw new ApiError(response.status, message, issues)
  }
  return response.json() as Promise<T>
}

export function login(username: string, password: string): Promise<LoginResult> {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function getCurrentUser(signal: AbortSignal): Promise<User> {
  return request('/auth/me', { signal })
}

export function getStores(signal: AbortSignal): Promise<Store[]> {
  return request('/stores?limit=100', { signal })
}

export interface PolicyCitation {
  chunk_id: string
  title: string
  section: string
  text: string
  document_version: string
}

export interface AgentReply {
  answer: string
  citations: PolicyCitation[]
  policy_status?: 'answered' | 'insufficient_evidence'
  conversation_id: number
  conversation_version: number
}

export function askAgent(
  storeId: number, message: string, signal: AbortSignal, conversationId?: number,
): Promise<AgentReply> {
  return request(`/store/${storeId}/agent/query`, {
    method: 'POST',
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal,
  })
}

export interface Product {
  id: number
  sku: string
  title: string
  price: string
  currency: string
  stock: number
  store_id: number | null
}

export interface TitleDraft {
  draft_id: number
  store_id: number
  product_id: number
  original_title: string
  proposed_title: string
  status: 'pending' | 'applied'
  created_at: string
  created_by?: number
  applied_by?: number | null
  applied_at?: string | null
}

export function getProducts(storeId: number, signal: AbortSignal): Promise<Product[]> {
  return request(`/products?store_id=${storeId}&limit=100`, { signal })
}

export function getLowStockProducts(
  storeId: number, threshold: number, signal: AbortSignal,
): Promise<Product[]> {
  // 让后端先按店铺和阈值筛选，再限制条数，不能在前端已取到的100个商品内筛选。
  const query = new URLSearchParams({ threshold: String(threshold), limit: '100' })
  return request(`/stores/${storeId}/products/low-stock?${query}`, { signal })
}

export function generateTitleDraft(
  storeId: number, productId: number, signal: AbortSignal,
): Promise<TitleDraft> {
  return request(`/stores/${storeId}/products/${productId}/title-drafts`, {
    method: 'POST', signal,
  })
}

export function getTitleDraft(
  storeId: number, draftId: number, signal: AbortSignal,
): Promise<TitleDraft> {
  return request(`/stores/${storeId}/title-drafts/${draftId}`, { signal })
}

export function confirmTitleDraft(
  storeId: number, draftId: number, signal: AbortSignal,
): Promise<TitleDraft> {
  return request(`/stores/${storeId}/title-drafts/${draftId}/confirm`, {
    method: 'POST', body: JSON.stringify({ confirmed: true }), signal,
  })
}

export type ImportKind = 'orders' | 'order-items'

export interface ImportResult {
  import_job_id: number
  row_count: number
  data_version: number
  duplicate: boolean
}

export function importCsv(
  storeId: number, kind: ImportKind, file: File, signal: AbortSignal,
): Promise<ImportResult> {
  // File是浏览器读取的文件对象，用FormData传递文件字节，而不是JSON.stringify
  const body = new FormData()
  // 字段名必须与后端UploadFile参数file一致
  body.append('file', file)
  // request复用JWT和错误处理；文件请求的Content-Type留给浏览器生成
  return request(`/stores/${storeId}/imports/${kind}`, {
    method: 'POST', body, signal,
  })
}

export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'cancelled'

export interface SalesGroup {
  currency: string
  order_count: number
  units_sold: number
  // 后端用字符串传递精确金额，展示时不转成浮点数，也不跨币种相加。
  gross_sales: string
  refund_amount: string
  net_sales: string
  orders_without_items: number
}

interface QueryContext {
  store_id: number
  start_at: string
  end_at: string
  data_version: number
}

export interface SalesSummary extends QueryContext {
  included_statuses: OrderStatus[]
  has_orders_without_items: boolean
  by_currency: SalesGroup[]
}

export interface OrderPage extends QueryContext {
  status_filter: OrderStatus | null
  limit: number
  offset: number
  has_more: boolean
  items: {
    id: number
    external_order_id: string
    ordered_at: string
    status: OrderStatus
    currency: string
  }[]
}

export interface SalesRange {
  start_at: string
  end_at: string
}

export function getSalesSummary(
  storeId: number, range: SalesRange, signal: AbortSignal,
): Promise<SalesSummary> {
  // URLSearchParams负责转义时间中的冒号、加号等字符，避免手工拼接破坏时区。
  const query = new URLSearchParams({ ...range })
  return request(`/stores/${storeId}/sales/summary?${query}`, { signal })
}

export function getOrderPage(
  storeId: number, range: SalesRange, status: OrderStatus | '',
  offset: number, signal: AbortSignal,
): Promise<OrderPage> {
  const query = new URLSearchParams({ ...range, limit: '20', offset: String(offset) })
  // “全部状态”表示不传status，而不是向后端发送空字符串。
  if (status) query.set('status', status)
  return request(`/stores/${storeId}/orders?${query}`, { signal })
}

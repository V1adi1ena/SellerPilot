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

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

// 统一发送JWT并处理HTTP错误。类型参数T描述接口预期返回的数据形状。
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body) headers.set('Content-Type', 'application/json')

  let response: Response
  try {
    response = await fetch(`/api${path}`, { ...options, headers })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    throw new Error('无法连接服务，请检查网络后重试。')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const message = typeof payload?.detail === 'string'
      ? payload.detail
      : `请求失败（${response.status}），请稍后重试。`
    throw new ApiError(response.status, message)
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

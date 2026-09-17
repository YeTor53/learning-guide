/** 统一请求封装：拼 /api、带 Cookie、拆信封、失败抛 ApiError（架构页 §8/§9.7）。 */

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

type Envelope<T> = { ok: true; data: T } | { ok: false; error: { code: string; message: string } }

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
  let response: Response
  try {
    response = await fetch(path, { credentials: 'include', ...init, headers })
  } catch {
    throw new ApiError('NETWORK', '网络不可用，请检查后端是否已启动', 0)
  }

  let payload: Envelope<T> | null = null
  try {
    payload = (await response.json()) as Envelope<T>
  } catch {
    payload = null
  }
  if (payload === null) {
    throw new ApiError('INTERNAL', '服务返回了非预期内容，请稍后重试', response.status)
  }
  if (!payload.ok) {
    throw new ApiError(payload.error.code, payload.error.message, response.status)
  }
  return payload.data
}

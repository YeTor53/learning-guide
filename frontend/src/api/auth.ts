import { request } from './http'

export interface User {
  id: string
  email: string
  displayName: string
  createdAt: string
}

export interface RegisterBody {
  email: string
  displayName: string
  password: string
}

export interface LoginBody {
  email: string
  password: string
}

export const authApi = {
  register: (body: RegisterBody) =>
    request<{ user: User }>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }).then((r) => r.user),

  login: (body: LoginBody) =>
    request<{ user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }).then((r) => r.user),

  logout: () => request<{ user: null }>('/api/auth/logout', { method: 'POST' }),

  me: () => request<{ user: User | null }>('/api/auth/me').then((r) => r.user),
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { authApi, type LoginBody, type RegisterBody, type User } from '../api/auth'

/**
 * 会话状态：`['me']` 缓存驱动导航栏与路由守卫（功能页 F-A-04 首屏会话恢复）。
 * 登录/注册成功后直接把用户写进缓存，避免多一次往返导致导航栏闪一下"登录/注册"。
 */
export function useSession() {
  const queryClient = useQueryClient()
  const meQuery = useQuery({ queryKey: ['me'], queryFn: authApi.me, retry: false })

  const login = useMutation({
    mutationFn: (body: LoginBody) => authApi.login(body),
    onSuccess: (user: User) => queryClient.setQueryData(['me'], user),
  })

  const register = useMutation({
    mutationFn: (body: RegisterBody) => authApi.register(body),
    onSuccess: (user: User) => queryClient.setQueryData(['me'], user),
  })

  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      queryClient.setQueryData(['me'], null)
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    },
  })

  return {
    user: meQuery.data ?? null,
    isLoading: meQuery.isLoading,
    login,
    register,
    logout,
  }
}

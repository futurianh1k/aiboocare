import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { authApi } from '../api/client'

interface User {
  id: string
  email: string
  name: string
  role: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

// 실제 프로덕션에서는 Context로 관리
// 여기서는 간단히 로컬 상태로 구현

export function useAuth(): AuthContextType {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // 개발 환경에서는 자동 로그인 처리
    const checkAuth = async () => {
      try {
        // 실제로는 /auth/me 호출
        // 개발용으로 더미 유저 설정
        setUser({
          id: 'admin-001',
          email: 'admin@aiboocare.com',
          name: '관리자',
          role: 'admin',
        })
      } catch (error) {
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }
    
    checkAuth()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    try {
      await authApi.login(email, password)
      const response = await authApi.me()
      setUser(response.data)
    } catch (error) {
      throw error
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
    }
  }, [])

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  }
}

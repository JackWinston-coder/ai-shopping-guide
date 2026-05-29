'use client'

import * as React from 'react'
import { getStoredToken, clearToken } from '@/lib/api'

interface AuthState {
  isAuthenticated: boolean
  token: string | null
  logout: () => void
}

const AuthContext = React.createContext<AuthState>({
  isAuthenticated: false,
  token: null,
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(null)

  React.useEffect(() => {
    setToken(getStoredToken())
    const handleStorage = () => setToken(getStoredToken())
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  const logout = React.useCallback(() => {
    clearToken()
    setToken(null)
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!token, token, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return React.useContext(AuthContext)
}

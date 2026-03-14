"use client"
import { createContext, useContext, useState, ReactNode } from "react"

interface AuthState {
  token: string | null
  user_id: string | null
  username: string | null
}

interface AuthContextType extends AuthState {
  setAuth: (token: string, user_id: string, username: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuthState] = useState<AuthState>(() => ({
    token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
    user_id: typeof window !== "undefined" ? localStorage.getItem("user_id") : null,
    username: typeof window !== "undefined" ? localStorage.getItem("username") : null,
  }))

  const setAuth = (token: string, user_id: string, username: string) => {
    localStorage.setItem("token", token)
    localStorage.setItem("user_id", user_id)
    localStorage.setItem("username", username)
    setAuthState({ token, user_id, username })
  }

  const logout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("user_id")
    localStorage.removeItem("username")
    setAuthState({ token: null, user_id: null, username: null })
  }

  return (
    <AuthContext.Provider value={{ ...auth, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

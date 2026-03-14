"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { AuthForm } from "@/components/AuthForm"
import { useAuth } from "@/context/AuthContext"
import { apiFetch, decodeJwtPayload } from "@/lib/api"

export default function LoginPage() {
  const { setAuth } = useAuth()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(username: string, pin: string, mode: "register" | "login") {
    setError(null)
    setLoading(true)
    try {
      const endpoint = mode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login"
      const res = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ username, pin }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? "Something went wrong")
        return
      }
      const { user_id, username: decodedUsername } = decodeJwtPayload(data.token)
      setAuth(data.token, user_id, decodedUsername)
      router.replace("/dashboard")
    } catch {
      setError("Network error — is the backend running?")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex items-center justify-center min-h-screen px-4">
      <AuthForm onSubmit={handleSubmit} error={error} loading={loading} />
    </main>
  )
}

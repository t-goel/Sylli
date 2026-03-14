"use client"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/context/AuthContext"

export default function RootPage() {
  const { token } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (token) {
      router.replace("/dashboard")
    } else {
      router.replace("/login")
    }
  }, [token, router])

  return null
}

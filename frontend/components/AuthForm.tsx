"use client"
import { useState } from "react"

interface AuthFormProps {
  onSubmit: (username: string, pin: string, mode: "register" | "login") => Promise<void>
  error?: string | null
  loading?: boolean
}

export function AuthForm({ onSubmit, error, loading }: AuthFormProps) {
  const [mode, setMode] = useState<"register" | "login">("login")
  const [username, setUsername] = useState("")
  const [pin, setPin] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onSubmit(username, pin, mode)
  }

  return (
    <div className="w-full max-w-sm mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-center">
        {mode === "login" ? "Sign in to Sylli" : "Create your account"}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3}
            required
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:border-blue-500"
            placeholder="at least 3 characters"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="pin">
            PIN
          </label>
          <input
            id="pin"
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            pattern="[0-9]{4,8}"
            minLength={4}
            maxLength={8}
            required
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:border-blue-500"
            placeholder="4–8 digits"
            inputMode="numeric"
          />
        </div>
        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md font-medium transition-colors"
        >
          {loading ? "..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-gray-400">
        {mode === "login" ? (
          <>
            No account?{" "}
            <button onClick={() => setMode("register")} className="text-blue-400 hover:underline">
              Register
            </button>
          </>
        ) : (
          <>
            Already have an account?{" "}
            <button onClick={() => setMode("login")} className="text-blue-400 hover:underline">
              Sign in
            </button>
          </>
        )}
      </p>
    </div>
  )
}

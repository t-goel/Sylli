const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001"

export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  return fetch(`${API_BASE}${path}`, { ...options, headers })
}

export function decodeJwtPayload(token: string): { user_id: string; username: string } {
  const payload = token.split(".")[1]
  const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
  return JSON.parse(decoded)
}

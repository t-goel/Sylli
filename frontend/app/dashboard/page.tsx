"use client"
import { useState, useEffect } from "react"
import { useAuth } from "@/context/AuthContext"
import { SyllabusUpload } from "@/components/SyllabusUpload"
import { WeekTimeline } from "@/components/WeekTimeline"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"

interface WeekMap {
  course_name: string
  weeks: Array<{
    week: number
    topic: string
    readings: string[]
    notes?: string
  }>
}

export default function DashboardPage() {
  const { username, logout } = useAuth()
  const router = useRouter()
  const [weekMap, setWeekMap] = useState<WeekMap | null>(null)

  useEffect(() => {
    const syllabusId = localStorage.getItem("syllabus_id")
    if (!syllabusId) return
    apiFetch(`/api/v1/syllabus/${syllabusId}`)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => { if (data?.week_map) setWeekMap(data.week_map) })
      .catch(() => {})
  }, [])

  function handleUploadSuccess(data: unknown) {
    const parsed = data as { syllabus_id: string; week_map: WeekMap }
    localStorage.setItem("syllabus_id", parsed.syllabus_id)
    setWeekMap(parsed.week_map)
  }

  function handleLogout() {
    logout()
    router.replace("/login")
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">
          Hi, {username ?? "there"}
        </h1>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          Sign out
        </button>
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-3">Upload Syllabus</h2>
        <SyllabusUpload onUploadSuccess={handleUploadSuccess} />
      </section>

      {weekMap && (
        <section className="mt-8">
          <WeekTimeline weekMap={weekMap} />
        </section>
      )}
    </main>
  )
}

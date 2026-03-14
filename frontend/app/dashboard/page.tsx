"use client"
import { useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { SyllabusUpload } from "@/components/SyllabusUpload"
import { WeekTimeline } from "@/components/WeekTimeline"
import { useRouter } from "next/navigation"

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

  function handleUploadSuccess(data: unknown) {
    const parsed = data as { week_map: WeekMap }
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

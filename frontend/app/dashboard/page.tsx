"use client"
import { useState, useEffect } from "react"
import { useAuth } from "@/context/AuthContext"
import { SyllabusUpload } from "@/components/SyllabusUpload"
import { WeekTimeline } from "@/components/WeekTimeline"
import { MaterialUpload } from "@/components/MaterialUpload"
import { MaterialLibrary } from "@/components/MaterialLibrary"
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

interface Material {
  material_id: string
  filename: string
  file_type: "pdf" | "pptx"
  week_number: number
  week_confirmed: boolean
  embed_status: "pending" | "processing" | "ready" | "error"
  uploaded_at: string
}

export default function DashboardPage() {
  const { username, logout } = useAuth()
  const router = useRouter()
  const [weekMap, setWeekMap] = useState<WeekMap | null>(null)
  const [syllabusId, setSyllabusId] = useState<string | null>(null)
  const [materials, setMaterials] = useState<Material[]>([])

  useEffect(() => {
    const id = localStorage.getItem("syllabus_id")
    setSyllabusId(id)
    if (id) {
      apiFetch(`/api/v1/syllabus/${id}`)
        .then((res) => res.ok ? res.json() : null)
        .then((data) => { if (data?.week_map) setWeekMap(data.week_map) })
        .catch(() => {})
    }
    fetchMaterials()
  }, [])

  async function fetchMaterials() {
    const res = await apiFetch("/api/v1/materials")
    if (res.ok) {
      const data = await res.json()
      setMaterials(data.materials ?? [])
    }
  }

  function handleUploadSuccess(data: unknown) {
    const parsed = data as { syllabus_id: string; week_map: WeekMap }
    localStorage.setItem("syllabus_id", parsed.syllabus_id)
    setSyllabusId(parsed.syllabus_id)
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

      {weekMap && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold mb-3">Upload Materials</h2>
          <MaterialUpload
            syllabusId={syllabusId}
            weekMap={weekMap}
            onMaterialUploaded={fetchMaterials}
          />
        </section>
      )}

      {weekMap && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold mb-3">Course Materials</h2>
          <MaterialLibrary
            weekMap={weekMap}
            materials={materials}
            onRefresh={fetchMaterials}
          />
        </section>
      )}
    </main>
  )
}

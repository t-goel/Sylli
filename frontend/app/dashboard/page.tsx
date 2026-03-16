"use client"
import { useState, useEffect } from "react"
import { useAuth } from "@/context/AuthContext"
import { SyllabusUpload } from "@/components/SyllabusUpload"
import { MaterialUpload } from "@/components/MaterialUpload"
import { MaterialLibrary } from "@/components/MaterialLibrary"
import { TutorChat } from "@/components/TutorChat"
import { QuizTab } from "@/components/QuizTab"
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
  const [activeTab, setActiveTab] = useState<"library" | "tutor" | "quiz">("library")
  const [showSyllabusUpload, setShowSyllabusUpload] = useState(false)

  useEffect(() => {
    // Always load syllabus from server — not localStorage — so it works across browsers/incognito
    apiFetch("/api/v1/syllabus")
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (data?.week_map) {
          setWeekMap(data.week_map)
          setSyllabusId(data.syllabus_id)
        }
      })
      .catch(() => {})
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

      <section className="mb-8">
        {weekMap === null ? (
          <>
            <h2 className="text-lg font-semibold mb-3">Upload Syllabus</h2>
            <SyllabusUpload onUploadSuccess={handleUploadSuccess} />
          </>
        ) : (
          <div>
            <button
              onClick={() => setShowSyllabusUpload((v) => !v)}
              className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              {showSyllabusUpload ? "Cancel" : "Replace syllabus"}
            </button>
            {showSyllabusUpload && (
              <div className="mt-3">
                <SyllabusUpload
                  onUploadSuccess={(data) => {
                    handleUploadSuccess(data)
                    setShowSyllabusUpload(false)
                  }}
                />
              </div>
            )}
          </div>
        )}
      </section>

      {weekMap && (
        <div className="flex gap-1 mb-6 border-b border-gray-800">
          {(["library", "tutor", "quiz"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              disabled={false}
              className={`px-4 py-2 text-sm capitalize transition-colors ${
                activeTab === tab
                  ? "border-b-2 border-white text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      )}

      {weekMap && (
        <>
          {activeTab === "library" && (
            <>
              <section className="mb-8">
                <h2 className="text-lg font-semibold mb-3">Upload Materials</h2>
                <MaterialUpload
                  syllabusId={syllabusId}
                  weekMap={weekMap}
                  onMaterialUploaded={fetchMaterials}
                />
              </section>
              <section>
                <MaterialLibrary
                  weekMap={weekMap}
                  materials={materials}
                  onRefresh={fetchMaterials}
                />
              </section>
            </>
          )}
          {activeTab === "tutor" && <TutorChat weekMap={weekMap} />}
          {activeTab === "quiz" && <QuizTab weekMap={weekMap} materials={materials} />}
        </>
      )}
    </main>
  )
}

"use client"
import { useState, useEffect, useRef } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001"

interface WeekMap {
  course_name: string
  weeks: Array<{
    week: number
    topic: string
    readings: string[]
    notes?: string
  }>
}

interface UploadedMaterial {
  material_id: string
  filename: string
  file_type: "pdf" | "pptx" | "docx"
  week_number: number
  week_confirmed: boolean
  embed_status: "pending" | "processing" | "ready" | "error"
}

interface MaterialUploadProps {
  syllabusId: string | null
  weekMap: WeekMap | null
  onMaterialUploaded: () => void
}

export function MaterialUpload({ syllabusId, weekMap, onMaterialUploaded }: MaterialUploadProps) {
  const [pendingMaterial, setPendingMaterial] = useState<UploadedMaterial | null>(null)
  const [selectedWeek, setSelectedWeek] = useState<number>(1)
  const [showWeekDropdown, setShowWeekDropdown] = useState(false)
  const [embedStatus, setEmbedStatus] = useState<"pending" | "processing" | "ready" | "error" | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollStartRef = useRef<number | null>(null)
  const POLL_TIMEOUT_MS = 5 * 60 * 1000 // 5 minutes

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    // Clear any in-progress polling from a previous upload
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setUploading(true)
    setError(null)
    setPendingMaterial(null)
    setEmbedStatus(null)

    try {
      const token = localStorage.getItem("token")
      const formData = new FormData()
      formData.append("file", file)
      const url = syllabusId
        ? `${API_BASE}/api/v1/materials?syllabus_id=${syllabusId}`
        : `${API_BASE}/api/v1/materials`
      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
        // Do NOT set Content-Type — browser sets multipart boundary automatically
      })

      if (!res.ok) {
        const msg = await res.text()
        setError(`Upload failed: ${msg}`)
        return
      }

      const data = await res.json()
      setPendingMaterial(data)
      setSelectedWeek(data.week_number ?? 1)
      setShowWeekDropdown(false)

      // Reset file input so user can upload again
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    } catch (err) {
      setError(`Upload error: ${String(err)}`)
    } finally {
      setUploading(false)
    }
  }

  async function handleConfirm() {
    if (!pendingMaterial) return

    try {
      const { apiFetch } = await import("@/lib/api")
      const res = await apiFetch(`/api/v1/materials/${pendingMaterial.material_id}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ week_number: selectedWeek }),
      })

      if (!res.ok) {
        setError("Confirm failed. Please try again.")
        return
      }

      const confirmData = await res.json()
      const initialStatus = confirmData.embed_status ?? "processing"
      setEmbedStatus(initialStatus)

      // Refresh the library immediately so the confirmed material appears
      onMaterialUploaded()

      // If no embedding triggered (local dev), clear the upload row after a moment
      if (initialStatus !== "processing") {
        setTimeout(() => {
          setPendingMaterial(null)
          setEmbedStatus(null)
        }, 1500)
        return
      }

      // Start polling every 4000ms until embed completes
      pollStartRef.current = Date.now()
      intervalRef.current = setInterval(async () => {
        // Stop polling after 5 minutes regardless
        if (pollStartRef.current && Date.now() - pollStartRef.current > POLL_TIMEOUT_MS) {
          clearInterval(intervalRef.current!)
          intervalRef.current = null
          setEmbedStatus("error")
          setTimeout(() => { setPendingMaterial(null); setEmbedStatus(null) }, 3000)
          return
        }

        const { apiFetch: apiFetchInner } = await import("@/lib/api")
        const statusRes = await apiFetchInner(`/api/v1/materials/${pendingMaterial.material_id}/status`)
        if (!statusRes.ok) {
          // Material was deleted or no longer accessible — stop polling and clear the row
          clearInterval(intervalRef.current!)
          intervalRef.current = null
          setPendingMaterial(null)
          setEmbedStatus(null)
          return
        }
        const statusData = await statusRes.json()
        const status = statusData.embed_status
        if (status === "ready" || status === "error") {
          clearInterval(intervalRef.current!)
          intervalRef.current = null
          setEmbedStatus(status)
          onMaterialUploaded()
          setTimeout(() => {
            setPendingMaterial(null)
            setEmbedStatus(null)
          }, 2000)
        } else if (status === "pending") {
          // Lambda never fired (e.g. running locally) — stop polling
          clearInterval(intervalRef.current!)
          intervalRef.current = null
          setEmbedStatus("error")
          setTimeout(() => { setPendingMaterial(null); setEmbedStatus(null) }, 3000)
        }
      }, 4000)
    } catch (err) {
      setError(`Confirm error: ${String(err)}`)
    }
  }

  const weekTopic = weekMap?.weeks.find((w) => w.week === selectedWeek)?.topic ?? ""

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-2">
          Select a PDF, PPTX, or DOCX file to upload
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.pptx,.docx,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleFileChange}
          disabled={uploading}
          className="block w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-gray-700 file:text-gray-200 hover:file:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        />
      </div>

      {uploading && (
        <p className="text-sm text-gray-400">Uploading...</p>
      )}

      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}

      {pendingMaterial && (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="text-sm">
              <span className="font-medium text-gray-200">
                &apos;{pendingMaterial.filename}&apos;
              </span>
              <span className="text-gray-400"> &rarr; </span>
              <span className="text-gray-300">
                Week {selectedWeek}{weekTopic ? `: ${weekTopic}` : ""}
              </span>
            </div>

            {embedStatus === null && (
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={handleConfirm}
                  className="rounded px-3 py-1 text-sm font-medium bg-green-700 hover:bg-green-600 text-white transition-colors"
                >
                  Confirm
                </button>
                <button
                  onClick={() => setShowWeekDropdown((v) => !v)}
                  className="rounded px-3 py-1 text-sm font-medium bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors"
                >
                  Change week
                </button>
              </div>
            )}
          </div>

          {showWeekDropdown && weekMap && embedStatus === null && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Select week</label>
              <select
                value={selectedWeek}
                onChange={(e) => setSelectedWeek(Number(e.target.value))}
                className="bg-gray-800 border border-gray-600 text-gray-200 text-sm rounded px-2 py-1 w-full"
              >
                {weekMap.weeks.map((w) => (
                  <option key={w.week} value={w.week}>
                    Week {w.week}: {w.topic}
                  </option>
                ))}
              </select>
            </div>
          )}

          {embedStatus === "pending" && (
            <p className="text-xs text-gray-400">Confirmed — embedding queued</p>
          )}
          {embedStatus === "processing" && (
            <p className="text-xs text-gray-400">Processing...</p>
          )}
          {embedStatus === "ready" && (
            <p className="text-xs text-green-400">Embedded</p>
          )}
          {embedStatus === "error" && (
            <p className="text-xs text-red-400">Embedding failed</p>
          )}
        </div>
      )}
    </div>
  )
}

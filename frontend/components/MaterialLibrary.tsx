"use client"
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

interface MaterialLibraryProps {
  weekMap: WeekMap | null
  materials: Material[]
  onRefresh: () => void
}

async function handleOpenMaterial(materialId: string) {
  const res = await apiFetch(`/api/v1/materials/${materialId}/view`)
  if (res.ok) {
    const data = await res.json()
    window.open(data.url, "_blank", "noopener,noreferrer")
  }
}

async function handleDeleteMaterial(materialId: string, onRefresh: () => void) {
  await apiFetch(`/api/v1/materials/${materialId}`, { method: "DELETE" })
  onRefresh()
}

function FileTypeBadge({ fileType }: { fileType: "pdf" | "pptx" }) {
  if (fileType === "pdf") {
    return (
      <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-red-900 text-red-200">
        PDF
      </span>
    )
  }
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-orange-900 text-orange-200">
      PPT
    </span>
  )
}

export function MaterialLibrary({ weekMap, materials, onRefresh }: MaterialLibraryProps) {
  if (!weekMap || weekMap.weeks.length === 0) {
    return null
  }

  return (
    <div className="space-y-6">
      {weekMap.weeks.map((week) => {
        const weekMaterials = materials.filter((m) => m.week_number === week.week)

        return (
          <div key={week.week}>
            <h3 className="text-base font-semibold text-gray-200 mb-2">
              Week {week.week}: {week.topic}
            </h3>

            <div className="space-y-1">
              {weekMaterials.length === 0 ? (
                <p className="text-sm text-gray-500 pl-2">no materials yet</p>
              ) : (
                weekMaterials.map((material) => (
                  <div
                    key={material.material_id}
                    className="flex items-center gap-3 rounded-md px-3 py-2 hover:bg-gray-800 transition-colors group"
                  >
                    <FileTypeBadge fileType={material.file_type} />
                    <span
                      onClick={() => handleOpenMaterial(material.material_id)}
                      className="text-sm text-gray-300 truncate flex-1 cursor-pointer"
                    >
                      {material.filename}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      {!material.week_confirmed && (
                        <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-amber-900 text-amber-200">
                          Unconfirmed
                        </span>
                      )}
                      {material.embed_status === "processing" && (
                        <span className="text-xs text-gray-400">Processing...</span>
                      )}
                      {material.embed_status === "error" && (
                        <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-red-900 text-red-300">
                          Error
                        </span>
                      )}
                      <button
                        onClick={() => handleDeleteMaterial(material.material_id, onRefresh)}
                        className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all text-xs px-1"
                        title="Delete"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

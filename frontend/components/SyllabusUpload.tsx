"use client"
import { useState, useRef } from "react"

interface SyllabusUploadProps {
  onUploadSuccess: (data: unknown) => void
}

export function SyllabusUpload({ onUploadSuccess }: SyllabusUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith(".pdf") && !file.name.toLowerCase().endsWith(".docx")) {
      setError("Only PDF and DOCX files are supported.")
      return
    }

    setError(null)
    setUploading(true)

    try {
      const token = localStorage.getItem("token")
      const formData = new FormData()
      formData.append("file", file)

      // Use raw fetch (NOT apiFetch) — apiFetch sets Content-Type: application/json
      // which conflicts with multipart/form-data boundary. Let the browser set
      // the correct Content-Type header automatically when using FormData.
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:3001/Prod"}/api/v1/syllabus`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            // Do NOT set Content-Type here — browser sets it with the boundary
          },
          body: formData,
        }
      )

      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? "Upload failed")
        return
      }
      onUploadSuccess(data)
    } catch {
      setError("Upload failed — is the backend running?")
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  return (
    <div className="w-full">
      <label
        htmlFor="syllabus-upload"
        className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 transition-colors"
      >
        <span className="text-gray-400 text-sm">
          {uploading ? "Uploading and parsing..." : "Click to upload your syllabus"}
        </span>
        <span className="text-gray-500 text-xs mt-1">PDF or DOCX</span>
      </label>
      <input
        ref={inputRef}
        id="syllabus-upload"
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={handleFileChange}
        disabled={uploading}
      />
      {error && <p className="mt-2 text-red-400 text-sm">{error}</p>}
    </div>
  )
}

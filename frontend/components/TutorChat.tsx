"use client"
import { useState, useRef, useEffect } from "react"
import { apiFetch } from "@/lib/api"

interface WeekMap {
  course_name: string
  weeks: Array<{ week: number; topic: string; readings: string[]; notes?: string }>
}

interface Citation {
  filename: string
  week_number: number | null
  url: string | null
}

interface ChatMessage {
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
}

interface TutorChatProps {
  weekMap: WeekMap
}

function TypingIndicator() {
  return (
    <div className="flex self-start">
      <div className="bg-gray-800 text-gray-100 rounded-lg px-4 py-3 max-w-[85%] flex items-center gap-1">
        <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
        <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
        <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  )
}

export function TutorChat({ weekMap }: TutorChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const userMessage: ChatMessage = { role: "user", content: trimmed }
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setInput("")
    setLoading(true)

    try {
      const res = await apiFetch("/api/v1/tutor/chat", {
        method: "POST",
        body: JSON.stringify({
          question: trimmed,
          history: messages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
          week_number: selectedWeek,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.answer,
            citations: data.citations ?? [],
          },
        ])
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Sorry, something went wrong. Please try again.", citations: [] },
        ])
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again.", citations: [] },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleWeekChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    setSelectedWeek(val === "" ? null : parseInt(val, 10))
  }

  return (
    <div className="flex flex-col h-[600px]">
      {/* Header: week filter */}
      <div className="flex items-center gap-3 pb-4 border-b border-gray-800 mb-4">
        <label className="text-sm text-gray-400">Filter by week:</label>
        <select
          value={selectedWeek === null ? "" : String(selectedWeek)}
          onChange={handleWeekChange}
          className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded px-2 py-1 focus:outline-none focus:border-gray-500"
        >
          <option value="">All weeks</option>
          {weekMap.weeks.map((w) => (
            <option key={w.week} value={String(w.week)}>
              Week {w.week}: {w.topic}
            </option>
          ))}
        </select>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-3 mb-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`rounded-lg px-4 py-3 max-w-[85%] ${
                message.role === "user"
                  ? "bg-blue-600 text-white self-end"
                  : "bg-gray-800 text-gray-100 self-start"
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.role === "assistant" &&
                message.citations &&
                message.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-700 text-sm">
                    <p className="text-gray-400 font-medium mb-1">Sources:</p>
                    <ul className="space-y-1">
                      {message.citations.map((c, i) => {
                        const weekEntry = weekMap.weeks.find(
                          (w) => w.week === c.week_number
                        )
                        const label = weekEntry
                          ? `Week ${c.week_number}: ${weekEntry.topic}`
                          : c.week_number
                          ? `Week ${c.week_number}`
                          : ""
                        const display = label ? `${c.filename} — ${label}` : c.filename
                        return (
                          <li key={i}>
                            {c.url ? (
                              <a
                                href={c.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300 underline transition-colors"
                              >
                                {display}
                              </a>
                            ) : (
                              <span className="text-gray-400">{display}</span>
                            )}
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                )}
            </div>
          </div>
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex gap-2 pt-4 border-t border-gray-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your course materials..."
          disabled={loading}
          className="flex-1 bg-gray-900 border border-gray-700 text-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500 disabled:opacity-50 placeholder:text-gray-600"
        />
        <button
          onClick={handleSend}
          disabled={loading || input.trim() === ""}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm px-4 py-2 rounded transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  )
}

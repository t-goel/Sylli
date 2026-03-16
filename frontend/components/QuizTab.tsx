"use client"
import { useState } from "react"
import { apiFetch } from "@/lib/api"

interface WeekMap {
  course_name: string
  weeks: Array<{ week: number; topic: string; readings: string[]; notes?: string }>
}

interface Material {
  material_id: string
  filename: string
  week_number: number
  embed_status: "pending" | "processing" | "ready" | "error"
}

interface Citation {
  filename: string
  week_number: number | null
  url: string | null
}

interface Question {
  question: string
  choices: string[]
  correct_index: number
  explanation: string
  material_id: string | null
  citation: Citation | null
}

interface QuizTabProps {
  weekMap: WeekMap
  materials: Material[]
}

export function QuizTab({ weekMap, materials }: QuizTabProps) {
  const [view, setView] = useState<"scope" | "quiz" | "results">("scope")
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [count, setCount] = useState<5 | 10 | 15>(5)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<(number | null)[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasEmbeddedMaterials =
    selectedWeek === null
      ? materials.some((m) => m.embed_status === "ready")
      : materials.some((m) => m.week_number === selectedWeek && m.embed_status === "ready")

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch("/api/v1/quiz/generate", {
        method: "POST",
        body: JSON.stringify({ week_number: selectedWeek, count }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.questions.length === 0) {
          setError("No materials found for this scope. Please upload and embed materials first.")
          return
        }
        setQuestions(data.questions)
        setAnswers(new Array(data.questions.length).fill(null))
        setCurrentIndex(0)
        setView("quiz")
      } else {
        setError("Quiz generation failed. Please try again.")
      }
    } catch {
      setError("Quiz generation failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  function handleAnswer(qIndex: number, choiceIndex: number) {
    if (answers[qIndex] !== null) return
    setAnswers((prev) => {
      const next = [...prev]
      next[qIndex] = choiceIndex
      return next
    })
  }

  function handleNewQuiz() {
    setView("scope")
    setQuestions([])
    setAnswers([])
    setCurrentIndex(0)
    setError(null)
  }

  // Scope screen — loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <svg
          className="animate-spin h-8 w-8 text-gray-400"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <p className="text-gray-400 text-sm">Generating your quiz...</p>
      </div>
    )
  }

  // Scope screen
  if (view === "scope") {
    return (
      <div className="flex flex-col gap-6 py-4">
        <h2 className="text-lg font-semibold">Generate a Quiz</h2>

        <div className="flex flex-col gap-4">
          {/* Week selector */}
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">Scope</label>
            <select
              value={selectedWeek === null ? "" : String(selectedWeek)}
              onChange={(e) =>
                setSelectedWeek(e.target.value === "" ? null : parseInt(e.target.value, 10))
              }
              className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded px-2 py-1 focus:outline-none focus:border-gray-500"
            >
              <option value="">All weeks</option>
              {weekMap.weeks.map((w) => (
                <option key={w.week} value={String(w.week)}>
                  Week {w.week}: {w.topic}
                </option>
              ))}
            </select>
            {!hasEmbeddedMaterials && selectedWeek !== null && (
              <p className="text-orange-400 text-xs mt-1">
                No materials embedded for Week {selectedWeek}
              </p>
            )}
          </div>

          {/* Question count segmented control */}
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">Number of questions</label>
            <div className="flex rounded overflow-hidden border border-gray-700 w-fit">
              {([5, 10, 15] as const).map((n) => (
                <button
                  key={n}
                  onClick={() => setCount(n)}
                  className={`px-4 py-1.5 text-sm transition-colors ${
                    count === n
                      ? "bg-blue-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex flex-col gap-2">
            <p className="text-red-400 text-sm">{error}</p>
            <button
              onClick={handleGenerate}
              className="self-start text-sm px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={loading || !hasEmbeddedMaterials}
          className="self-start px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Generate Quiz
        </button>
      </div>
    )
  }

  // Quiz screen
  if (view === "quiz") {
    const q = questions[currentIndex]
    const answered = answers[currentIndex] !== null
    const selectedAnswer = answers[currentIndex]
    const isLast = currentIndex === questions.length - 1

    return (
      <div className="flex flex-col gap-6 py-4">
        {/* Progress header */}
        <p className="text-sm text-gray-400">
          Question {currentIndex + 1} of {questions.length}
        </p>

        {/* Question card */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-4">
          <p className="text-gray-100 font-medium">{q.question}</p>

          {/* Choices */}
          <div className="flex flex-col gap-2">
            {q.choices.map((choice, i) => {
              const isCorrect = i === q.correct_index
              const isSelected = selectedAnswer === i

              let bg = "bg-gray-800 hover:bg-gray-700 text-gray-200"
              let prefix = ""
              if (answered) {
                if (isCorrect) {
                  bg = "bg-green-700 text-white"
                  prefix = "✔ "
                } else if (isSelected && !isCorrect) {
                  bg = "bg-red-700 text-white"
                  prefix = "✘ "
                } else {
                  bg = "bg-gray-800 text-gray-500"
                }
              }

              return (
                <button
                  key={i}
                  onClick={() => handleAnswer(currentIndex, i)}
                  disabled={answered}
                  className={`text-left text-sm px-3 py-2 rounded transition-colors ${bg} disabled:cursor-default`}
                >
                  {prefix}{choice}
                </button>
              )
            })}
          </div>

          {/* Explanation + citation */}
          {answered && (
            <div className="border-t border-gray-700 pt-3 flex flex-col gap-1">
              <p className="text-sm text-gray-300">{q.explanation}</p>
              {q.citation && q.citation.url && (
                <CitationLink citation={q.citation} weekMap={weekMap} />
              )}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex gap-3">
          <button
            onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            disabled={currentIndex === 0}
            className="px-3 py-1.5 text-sm rounded bg-gray-800 hover:bg-gray-700 text-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Prev
          </button>
          {isLast ? (
            <button
              onClick={() => setView("results")}
              disabled={!answered}
              className="px-3 py-1.5 text-sm rounded bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Finish
            </button>
          ) : (
            <button
              onClick={() => setCurrentIndex((i) => Math.min(questions.length - 1, i + 1))}
              disabled={!answered}
              className="px-3 py-1.5 text-sm rounded bg-gray-800 hover:bg-gray-700 text-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          )}
        </div>
      </div>
    )
  }

  // Results screen
  if (view === "results") {
    const score = questions.reduce(
      (acc, q, i) => acc + (answers[i] === q.correct_index ? 1 : 0),
      0
    )
    const passed = score > questions.length / 2

    return (
      <div className="flex flex-col gap-6 py-4">
        <div className="text-center py-4">
          <p className="text-lg font-semibold text-gray-200 mb-1">Quiz Complete</p>
          <p className="text-2xl font-bold">
            <span className={passed ? "text-green-400" : "text-red-400"}>{score}</span>
            <span className="text-gray-400 text-lg"> / {questions.length} correct</span>
          </p>
        </div>

        {/* Per-question review */}
        <div className="flex flex-col gap-4">
          {questions.map((q, i) => {
            const userAnswer = answers[i]
            const correct = userAnswer === q.correct_index
            return (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-2">
                <p className="text-sm text-gray-400">Question {i + 1}</p>
                <p className="text-gray-100 text-sm font-medium">{q.question}</p>
                <div className="flex flex-col gap-1 text-sm">
                  <p>
                    <span className="text-gray-500">Your answer: </span>
                    <span className={correct ? "text-green-400" : "text-red-400"}>
                      {userAnswer !== null ? q.choices[userAnswer] : "—"}
                      {correct ? " ✔" : " ✘"}
                    </span>
                  </p>
                  {!correct && (
                    <p>
                      <span className="text-gray-500">Correct answer: </span>
                      <span className="text-green-400">{q.choices[q.correct_index]}</span>
                    </p>
                  )}
                </div>
                <p className="text-xs text-gray-400">{q.explanation}</p>
                {q.citation && q.citation.url && (
                  <CitationLink citation={q.citation} weekMap={weekMap} />
                )}
              </div>
            )
          })}
        </div>

        <button
          onClick={handleNewQuiz}
          className="self-start px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm transition-colors"
        >
          New quiz
        </button>
      </div>
    )
  }

  return null
}

function CitationLink({
  citation,
  weekMap,
}: {
  citation: { filename: string; week_number: number | null; url: string | null }
  weekMap: WeekMap
}) {
  if (!citation.url) return null
  const weekEntry = citation.week_number !== null
    ? weekMap.weeks.find((w) => w.week === citation.week_number)
    : null
  const label = weekEntry
    ? `Week ${citation.week_number}: ${weekEntry.topic}`
    : citation.week_number !== null
    ? `Week ${citation.week_number}`
    : null
  const display = label ? `${citation.filename} — ${label}` : citation.filename

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-400 hover:text-blue-300 underline transition-colors text-xs"
    >
      {display}
    </a>
  )
}

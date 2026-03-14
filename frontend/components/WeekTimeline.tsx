interface Week {
  week: number
  topic: string
  readings: string[]
  notes?: string
}

interface WeekMap {
  course_name: string
  weeks: Week[]
}

interface WeekTimelineProps {
  weekMap: WeekMap
}

export function WeekTimeline({ weekMap }: WeekTimelineProps) {
  const weeks = weekMap?.weeks ?? []

  return (
    <div className="space-y-4 mt-6">
      <h2 className="text-xl font-semibold text-gray-100">
        {weekMap?.course_name ?? "Course Timeline"}
      </h2>
      {weeks.length === 0 && (
        <p className="text-gray-400 text-sm">No weeks found in syllabus.</p>
      )}
      {weeks.map((w) => (
        <div
          key={w.week}
          className="border-l-2 border-blue-500 pl-4 py-1"
        >
          <p className="font-medium text-gray-100">
            Week {w.week}: {w.topic ?? "Untitled"}
          </p>
          {(w.readings ?? []).length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {(w.readings ?? []).map((r, i) => (
                <li key={i} className="text-sm text-gray-400">
                  {r}
                </li>
              ))}
            </ul>
          )}
          {w.notes && (
            <p className="mt-1 text-xs text-gray-500">{w.notes}</p>
          )}
        </div>
      ))}
    </div>
  )
}

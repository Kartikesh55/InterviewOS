import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ArrowLeft, AlertCircle, LoaderCircle } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { extractApiError, getInterviewReport } from '../services/interviewApi'
import type { InterviewReportResponse } from '../types'

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function InterviewReportPage() {
  const { interviewId } = useParams<{ interviewId: string }>()
  const [report, setReport] = useState<InterviewReportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const requestGeneration = useRef(0)

  useEffect(() => {
    if (!interviewId || !UUID_PATTERN.test(interviewId)) {
      requestGeneration.current += 1
      return
    }

    const generation = ++requestGeneration.current
    getInterviewReport(interviewId)
      .then((result) => {
        if (requestGeneration.current === generation) setReport(result)
      })
      .catch((requestError: unknown) => {
        if (requestGeneration.current === generation) setError(extractApiError(requestError))
      })
      .finally(() => {
        if (requestGeneration.current === generation) setLoading(false)
      })
    return () => {
      if (requestGeneration.current === generation) requestGeneration.current += 1
    }
  }, [interviewId])

  if (!interviewId || !UUID_PATTERN.test(interviewId)) {
    return (
      <ReportMessage
        title="Invalid report link"
        message="The interview ID in this URL is not valid."
        icon={<AlertCircle className="h-5 w-5" />}
      />
    )
  }

  if (loading) {
    return (
      <ReportMessage
        title="Loading interview report"
        message="Retrieving saved answers and evaluation results..."
        icon={<LoaderCircle className="h-5 w-5 animate-spin" />}
      />
    )
  }

  if (error || !report) {
    return (
      <ReportMessage
        title="Unable to load report"
        message={error ?? 'No report data was returned.'}
        icon={<AlertCircle className="h-5 w-5" />}
        action={<Link to={`/interviews/${interviewId}/room`} className={linkClass}>Return to interview</Link>}
      />
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link
        to={`/interviews/${interviewId}/room`}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Interview room
      </Link>
      <header className="space-y-2">
        <p className="font-mono text-xs font-semibold uppercase tracking-wide text-indigo-400">
          Interview report
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">{report.targetRole}</h1>
        <p className="text-sm text-zinc-400">
          {formatDifficulty(report.difficulty)} · {report.status.replaceAll('_', ' ')} ·{' '}
          {report.questions.length} questions
        </p>
      </header>

      <div className="space-y-4">
        {report.questions.map((question) => (
          <section
            key={question.id}
            className="space-y-4 rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-5 sm:p-6"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-mono text-xs text-zinc-500">
                Question {question.questionOrder} · {question.source.replaceAll('_', ' ')}
              </p>
              <span className="text-xs text-zinc-500">
                {question.answers.length
                  ? `${question.answers.length} answer${question.answers.length === 1 ? '' : 's'}`
                  : 'Not answered'}
              </span>
            </div>
            <h2 className="text-base font-semibold leading-relaxed text-zinc-100">
              {question.questionText}
            </h2>
            {question.answers.map((answer) => (
              <article
                key={answer.id}
                className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4"
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">
                  {answer.candidateAnswer}
                </p>
                <div className="flex flex-wrap items-center gap-3 border-t border-zinc-800 pt-3">
                  <span className="text-xs text-zinc-500">
                    Evaluation: <span className="font-medium text-zinc-300">{answer.evaluationStatus}</span>
                  </span>
                  {answer.overallScore !== null && (
                    <span className="text-xs text-zinc-500">
                      Overall score:{' '}
                      <span className="font-mono font-semibold text-indigo-300">
                        {answer.overallScore.toFixed(2)} / 10
                      </span>
                    </span>
                  )}
                </div>
                {answer.feedback && (
                  <p className="text-sm leading-relaxed text-zinc-400">{answer.feedback}</p>
                )}
              </article>
            ))}
          </section>
        ))}
      </div>
    </div>
  )
}

function ReportMessage({
  title,
  message,
  icon,
  action,
}: {
  title: string
  message: string
  icon: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-2xl items-center">
      <section className="w-full space-y-4 rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-6 sm:p-8">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-300">
          {icon}
        </div>
        <h1 className="text-xl font-bold text-zinc-100">{title}</h1>
        <p className="text-sm leading-relaxed text-zinc-400">{message}</p>
        {action}
      </section>
    </div>
  )
}

function formatDifficulty(difficulty: string): string {
  return difficulty.charAt(0) + difficulty.slice(1).toLowerCase()
}

const linkClass =
  'inline-flex items-center rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-700'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  CircleHelp,
  Clock3,
  LoaderCircle,
  RotateCw,
  Send,
  Sparkles,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import {
  advanceToNextQuestion,
  completeInterview,
  extractApiError,
  getCurrentQuestion,
  getInterview,
  getInterviewReport,
  startInterview,
  submitAnswer,
} from '../services/interviewApi'
import type {
  CriterionAssessmentStatus,
  InterviewAnswerResponse,
  InterviewDetailsResponse,
  InterviewQuestionResponse,
} from '../types'

type RoomAction = 'idle' | 'loading' | 'submitting' | 'advancing' | 'completing'

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const SCORE_DIMENSIONS = [
  { key: 'technicalAccuracy', label: 'Technical accuracy' },
  { key: 'completeness', label: 'Completeness' },
  { key: 'clarity', label: 'Clarity' },
  { key: 'depth', label: 'Depth' },
  { key: 'overallScore', label: 'Overall score' },
] as const

const ASSESSMENT_STYLES: Record<CriterionAssessmentStatus, string> = {
  COVERED: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
  PARTIALLY_COVERED: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
  MISSING: 'border-rose-500/20 bg-rose-500/10 text-rose-300',
}

function isValidUuid(value: string | undefined): value is string {
  return value !== undefined && UUID_PATTERN.test(value)
}

export function InterviewRoomPage() {
  const { interviewId } = useParams<{ interviewId: string }>()
  const [interview, setInterview] = useState<InterviewDetailsResponse | null>(null)
  const [question, setQuestion] = useState<InterviewQuestionResponse | null>(null)
  const [answer, setAnswer] = useState<InterviewAnswerResponse | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [action, setAction] = useState<RoomAction>('loading')
  const [error, setError] = useState<string | null>(null)
  const [answerError, setAnswerError] = useState<string | null>(null)
  const [submissionUncertain, setSubmissionUncertain] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [hasLoaded, setHasLoaded] = useState(false)
  const initialLoadStarted = useRef<string | null>(null)
  const roomLoadGeneration = useRef(0)

  const loadRoom = useCallback(async () => {
    if (!isValidUuid(interviewId)) {
      return
    }

    const generation = ++roomLoadGeneration.current
    const isCurrentLoad = () => roomLoadGeneration.current === generation
    setAction('loading')
    setError(null)

    try {
      const details = await getInterview(interviewId)
      if (!isCurrentLoad()) return

      if (details.status === 'COMPLETED') {
        setInterview(details)
        setQuestion(null)
        setAnswer(null)
        setCompleted(true)
        setHasLoaded(true)
        setAction('idle')
        return
      }

      const currentInterview =
        details.status === 'CREATED'
          ? await startInterview(interviewId)
          : details

      if (!isCurrentLoad()) return
      if (currentInterview.status !== 'IN_PROGRESS') {
        throw new Error('The interview is not available to start.')
      }

      const [currentQuestion, report] = await Promise.all([
        getCurrentQuestion(interviewId),
        getInterviewReport(interviewId),
      ])
      if (!isCurrentLoad()) return

      const savedAnswer =
        report.questions.find((item) => item.id === currentQuestion.id)?.answers[0] ?? null
      setInterview({
        ...details,
        ...currentInterview,
        currentQuestionOrder: currentQuestion.questionOrder,
      })
      setQuestion(currentQuestion)
      setAnswer(savedAnswer)
      setAnswerText(savedAnswer?.candidateAnswer ?? '')
      setAnswerError(null)
      setSubmissionUncertain(false)
      setCompleted(false)
      setHasLoaded(true)
      setAction('idle')
    } catch (requestError: unknown) {
      if (!isCurrentLoad()) return
      setError(extractApiError(requestError))
      setHasLoaded(true)
      setAction('idle')
    }
  }, [interviewId])

  useEffect(() => {
    if (initialLoadStarted.current === interviewId) return
    initialLoadStarted.current = interviewId ?? null
    if (!isValidUuid(interviewId)) {
      roomLoadGeneration.current += 1
      return
    }
    void Promise.resolve().then(() => loadRoom())
  }, [interviewId, loadRoom])

  async function handleSubmitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!interviewId || !question || action !== 'idle' || answer || submissionUncertain) return

    if (!answerText.trim()) {
      setAnswerError('Write an answer before submitting.')
      return
    }

    setAnswerError(null)
    setError(null)
    setAction('submitting')
    try {
      const savedAnswer = await submitAnswer(interviewId, question.id, {
        candidateAnswer: answerText,
      })
      setAnswer(savedAnswer)
      setAnswerText(savedAnswer.candidateAnswer)
      setSubmissionUncertain(false)
      setAction('idle')
    } catch (requestError: unknown) {
      const message = extractApiError(requestError)
      setAction('loading')
      try {
        const report = await getInterviewReport(interviewId)
        const savedAnswer = report.questions
          .find((item) => item.id === question.id)
          ?.answers[0]
        if (savedAnswer) {
          setAnswer(savedAnswer)
          setAnswerText(savedAnswer.candidateAnswer)
          setError(null)
          setSubmissionUncertain(false)
        } else {
          setError(message)
          setSubmissionUncertain(false)
        }
      } catch {
        setError(
          `${message} The save status could not be confirmed. Check the interview state before retrying.`
        )
        setSubmissionUncertain(true)
      } finally {
        setAction('idle')
      }
    }
  }

  async function handleAdvance() {
    if (!interviewId || !question || action !== 'idle' || answer?.evaluationStatus !== 'COMPLETED') {
      return
    }
    setAction('advancing')
    setError(null)
    try {
      const nextQuestion = await advanceToNextQuestion(interviewId)
      setQuestion(nextQuestion)
      setInterview((current) =>
        current ? { ...current, currentQuestionOrder: nextQuestion.questionOrder } : current
      )
      setAnswer(null)
      setAnswerText('')
      setAnswerError(null)
      setSubmissionUncertain(false)
      setAction('idle')
    } catch (requestError: unknown) {
      const message = extractApiError(requestError)
      await loadRoom()
      setError(`Could not confirm question progression. Room state was refreshed. ${message}`)
    }
  }

  async function handleComplete() {
    if (!interviewId || action !== 'idle' || answer?.evaluationStatus !== 'COMPLETED') {
      return
    }
    setAction('completing')
    setError(null)
    try {
      const result = await completeInterview(interviewId)
      setInterview((current) => (current ? { ...current, ...result } : current))
      setCompleted(true)
      setAction('idle')
    } catch (requestError: unknown) {
      const message = extractApiError(requestError)
      await loadRoom()
      setError(`Could not confirm interview completion. Room state was refreshed. ${message}`)
    }
  }

  const isBusy = action !== 'idle'
  const hasNextQuestion =
    question !== null && interview !== null && question.questionOrder < interview.numberOfQuestions

  if (!isValidUuid(interviewId)) {
    return (
      <RoomMessage
        icon={<AlertCircle className="h-5 w-5" />}
        title="Invalid interview link"
        message="The interview ID in this URL is not valid."
        action={<BackToDashboard />}
      />
    )
  }

  if (!hasLoaded && isBusy) {
    return (
      <RoomMessage
        icon={<LoaderCircle className="h-5 w-5 animate-spin" />}
        title="Preparing your interview"
        message="Loading the interview and its current question..."
      />
    )
  }

  if (error && !interview) {
    return (
      <RoomMessage
        icon={<AlertCircle className="h-5 w-5" />}
        title="Unable to load interview"
        message={error}
        action={
          <button type="button" onClick={() => void loadRoom()} className={secondaryButtonClass}>
            <RotateCw className="h-4 w-4" />
            Try again
          </button>
        }
      />
    )
  }

  if (completed) {
    return (
      <RoomMessage
        icon={<CheckCircle2 className="h-5 w-5" />}
        title="Interview completed"
        message="Your interview has been completed. Your answers and evaluation results are available in the report."
        action={
          <Link to={`/interviews/${interviewId}/report`} className={primaryButtonClass}>
            View interview report
            <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />
    )
  }

  if (!interview || !question) {
    return (
      <RoomMessage
        icon={<CircleHelp className="h-5 w-5" />}
        title="Interview question unavailable"
        message={error ?? 'No current question was returned for this interview.'}
        action={<BackToDashboard />}
      />
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Dashboard
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Interview room</h1>
          <p className="text-sm text-zinc-400">
            {interview.targetRole}
            <span className="mx-2 text-zinc-700">/</span>
            <span className="text-zinc-300">{formatDifficulty(interview.difficulty)}</span>
          </p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1.5 text-xs font-medium text-indigo-300">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />
          In progress
        </span>
      </header>

      <section className="space-y-5 rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-5 sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Question {question.questionOrder} of {interview.numberOfQuestions}
            </p>
            <div className="mt-2 h-1.5 w-48 max-w-full overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-violet-500 transition-all"
                style={{
                  width: `${Math.min(
                    (question.questionOrder / interview.numberOfQuestions) * 100,
                    100
                  )}%`,
                }}
              />
            </div>
          </div>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
              question.source === 'FOLLOW_UP'
                ? 'border-violet-500/20 bg-violet-500/10 text-violet-300'
                : 'border-zinc-700 bg-zinc-800/70 text-zinc-300'
            }`}
          >
            {question.source === 'FOLLOW_UP' && <Sparkles className="h-3 w-3" />}
            {question.source === 'FOLLOW_UP' ? 'Adaptive follow-up' : 'Generated question'}
          </span>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 sm:p-6">
          <p className="text-lg font-medium leading-relaxed text-zinc-100 sm:text-xl">
            {question.questionText}
          </p>
        </div>

        {answer ? (
          <EvaluationResult answer={answer} />
        ) : (
          <form onSubmit={handleSubmitAnswer} className="space-y-3">
            <label htmlFor="candidate-answer" className="block text-sm font-semibold text-zinc-200">
              Your answer
            </label>
            <textarea
              id="candidate-answer"
              value={answerText}
              onChange={(event) => {
                setAnswerText(event.target.value)
                if (answerError) setAnswerError(null)
              }}
              disabled={isBusy || submissionUncertain}
              rows={9}
              placeholder="Explain your approach, key decisions, and trade-offs..."
              aria-invalid={answerError !== null}
              aria-describedby={answerError ? 'answer-error' : 'answer-hint'}
              className="w-full resize-y rounded-xl border border-zinc-700/70 bg-zinc-950/70 px-4 py-3 text-sm leading-relaxed text-zinc-100 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            />
            {answerError && (
              <p id="answer-error" role="alert" className="text-xs text-rose-400">
                {answerError}
              </p>
            )}
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <p id="answer-hint" className="text-xs text-zinc-500">
                Your evaluation is based on the answer you submit. Take your time.
              </p>
              <button
                type="submit"
                disabled={isBusy || submissionUncertain}
                className={primaryButtonClass}
              >
                {action === 'submitting' || action === 'loading' ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {action === 'submitting'
                  ? 'Submitting answer...'
                  : action === 'loading'
                    ? 'Checking saved answer...'
                    : 'Submit answer'}
              </button>
            </div>
            {submissionUncertain && (
              <button
                type="button"
                onClick={() => void loadRoom()}
                disabled={isBusy}
                className="inline-flex items-center gap-2 text-xs font-medium text-amber-300 hover:text-amber-200 disabled:opacity-50"
              >
                <RotateCw className="h-3.5 w-3.5" />
                Check whether the answer was saved
              </button>
            )}
          </form>
        )}
      </section>

      {error && (
        <div role="alert" className="flex items-start gap-2.5 rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 text-sm text-rose-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {answer?.evaluationStatus === 'COMPLETED' && (
        <div className="flex flex-col justify-end gap-3 sm:flex-row">
          {hasNextQuestion ? (
            <button
              type="button"
              onClick={() => void handleAdvance()}
              disabled={isBusy}
              className={primaryButtonClass}
            >
              {action === 'advancing' ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {action === 'advancing' ? 'Loading next question...' : 'Next question'}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void handleComplete()}
              disabled={isBusy}
              className={primaryButtonClass}
            >
              {action === 'completing' ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              {action === 'completing' ? 'Completing interview...' : 'Complete interview'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function EvaluationResult({ answer }: { answer: InterviewAnswerResponse }) {
  if (answer.evaluationStatus === 'FAILED') {
    return (
      <div className="space-y-3 rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 sm:p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-rose-300">
          <AlertCircle className="h-4 w-4" />
          Evaluation could not be completed
        </div>
        <p className="text-sm leading-relaxed text-zinc-400">
          Your answer was saved, but automated evaluation was unsuccessful. The backend does not
          currently provide an evaluation retry endpoint, so this answer cannot be resubmitted and
          the interview will not advance.
        </p>
        <SavedAnswer answer={answer} />
      </div>
    )
  }

  if (answer.evaluationStatus === 'PENDING') {
    return (
      <div className="space-y-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 sm:p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-amber-300">
          <Clock3 className="h-4 w-4" />
          Evaluation is pending
        </div>
        <p className="text-sm leading-relaxed text-zinc-400">
          Your answer is saved and is awaiting evaluation. It cannot be resubmitted, and you cannot
          advance yet. There is no evaluation retry endpoint available from the interview room.
        </p>
        <SavedAnswer answer={answer} />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <SavedAnswer answer={answer} />

      <section aria-labelledby="evaluation-heading" className="space-y-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <h2 id="evaluation-heading" className="text-sm font-semibold text-zinc-100">
            Evaluation
          </h2>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {SCORE_DIMENSIONS.map(({ key, label }) => {
            const score = answer[key]
            return (
              <div key={key} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                <p className="text-[11px] leading-snug text-zinc-500">{label}</p>
                <p className="mt-2 font-mono text-xl font-semibold text-zinc-100">
                  {score === null ? '—' : score.toFixed(2)}
                  {score !== null && <span className="ml-1 text-xs font-normal text-zinc-500">/ 10</span>}
                </p>
              </div>
            )
          })}
        </div>

        {answer.criterionAssessments.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Criterion assessment
            </h3>
            {answer.criterionAssessments.map((assessment, index) => (
              <article
                key={`${assessment.criterion}-${index}`}
                className="space-y-2 rounded-xl border border-zinc-800 bg-zinc-950/40 p-4"
              >
                <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                  <p className="text-sm font-medium text-zinc-200">{assessment.criterion}</p>
                  <span
                    className={`w-fit rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                      ASSESSMENT_STYLES[assessment.status]
                    }`}
                  >
                    {assessment.status.replaceAll('_', ' ')}
                  </span>
                </div>
                {assessment.evidence && (
                  <blockquote className="border-l-2 border-indigo-500/40 pl-3 text-xs italic leading-relaxed text-zinc-400">
                    “{assessment.evidence}”
                  </blockquote>
                )}
              </article>
            ))}
          </div>
        )}

        {(answer.strengths.length > 0 || answer.missingConcepts.length > 0) && (
          <div className="grid gap-3 sm:grid-cols-2">
            {answer.strengths.length > 0 && (
              <SummaryList title="Strengths" items={answer.strengths} tone="emerald" />
            )}
            {answer.missingConcepts.length > 0 && (
              <SummaryList title="Concepts to address" items={answer.missingConcepts} tone="amber" />
            )}
          </div>
        )}

        {answer.feedback && (
          <div className="rounded-xl border border-indigo-500/15 bg-indigo-500/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-300">Feedback</p>
            <p className="mt-2 text-sm leading-relaxed text-zinc-300">{answer.feedback}</p>
          </div>
        )}

        {answer.suggestedFollowUp && (
          <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-300">
              Suggested follow-up
            </p>
            <p className="mt-2 text-sm leading-relaxed text-zinc-200">
              {answer.suggestedFollowUp}
            </p>
            {answer.suggestedFollowUpCriteria.length > 0 && (
              <ul className="mt-3 list-inside list-disc space-y-1 text-xs text-zinc-400">
                {answer.suggestedFollowUpCriteria.map((criterion, index) => (
                  <li key={`${criterion}-${index}`}>{criterion}</li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-[11px] text-zinc-500">
              The interviewer selects the next question. The suggestion may not be used.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}

function SavedAnswer({ answer }: { answer: InterviewAnswerResponse }) {
  return (
    <details className="rounded-xl border border-zinc-800 bg-zinc-950/40">
      <summary className="cursor-pointer px-4 py-3 text-xs font-medium text-zinc-400 hover:text-zinc-200">
        View your submitted answer
      </summary>
      <p className="whitespace-pre-wrap border-t border-zinc-800 px-4 py-3 text-sm leading-relaxed text-zinc-300">
        {answer.candidateAnswer}
      </p>
    </details>
  )
}

function SummaryList({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: 'emerald' | 'amber'
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
      <h3 className={`text-xs font-semibold ${tone === 'emerald' ? 'text-emerald-300' : 'text-amber-300'}`}>
        {title}
      </h3>
      <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-zinc-400">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="flex gap-2">
            <span aria-hidden="true">·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function RoomMessage({
  icon,
  title,
  message,
  action,
}: {
  icon: ReactNode
  title: string
  message: string
  action?: ReactNode
}) {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-2xl items-center">
      <section className="w-full space-y-5 rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-6 sm:p-8">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-300">
          {icon}
        </div>
        <div className="space-y-2">
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">{title}</h1>
          <p className="text-sm leading-relaxed text-zinc-400">{message}</p>
        </div>
        {action}
      </section>
    </div>
  )
}

function BackToDashboard() {
  return (
    <Link to="/" className={secondaryButtonClass}>
      <ArrowLeft className="h-4 w-4" />
      Back to dashboard
    </Link>
  )
}

function formatDifficulty(difficulty: string): string {
  return difficulty.charAt(0) + difficulty.slice(1).toLowerCase()
}

const primaryButtonClass =
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/15 transition-colors hover:bg-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/60 disabled:cursor-not-allowed disabled:opacity-50'

const secondaryButtonClass =
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-200 transition-colors hover:border-zinc-600 hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/60 disabled:cursor-not-allowed disabled:opacity-50'

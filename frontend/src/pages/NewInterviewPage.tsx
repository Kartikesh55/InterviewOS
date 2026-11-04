import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Briefcase,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Zap,
  BookOpen,
  Rocket,
  ArrowRight,
} from 'lucide-react'
import { createInterview, generateInterviewQuestions, extractApiError } from '../services/interviewApi'
import type { Difficulty } from '../types'

// ─── Types ─────────────────────────────────────────────────────────────────────

type CreationStep =
  | 'idle'
  | 'creating'
  | 'generating'
  | 'navigating'

interface DifficultyOption {
  value: Difficulty
  label: string
  description: string
  icon: React.ElementType
  accentClass: string
  borderClass: string
  activeBg: string
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const DIFFICULTY_OPTIONS: DifficultyOption[] = [
  {
    value: 'BEGINNER',
    label: 'Beginner',
    description: 'Foundational concepts, CS basics, and guided problem-solving.',
    icon: BookOpen,
    accentClass: 'text-emerald-400',
    borderClass: 'border-emerald-500/30',
    activeBg: 'bg-emerald-500/8',
  },
  {
    value: 'INTERMEDIATE',
    label: 'Intermediate',
    description: 'Real-world system design, trade-offs, and production patterns.',
    icon: Zap,
    accentClass: 'text-indigo-400',
    borderClass: 'border-indigo-500/30',
    activeBg: 'bg-indigo-500/8',
  },
  {
    value: 'ADVANCED',
    label: 'Advanced',
    description: 'Deep architecture, distributed systems, and expert-level depth.',
    icon: Rocket,
    accentClass: 'text-violet-400',
    borderClass: 'border-violet-500/30',
    activeBg: 'bg-violet-500/8',
  },
]

const STEP_LABELS: Record<CreationStep, string> = {
  idle: '',
  creating: 'Creating your interview...',
  generating: 'Generating technical questions with AI...',
  navigating: 'Preparing your interview room...',
}

const MIN_QUESTIONS = 1
const MAX_QUESTIONS = 20
const DEFAULT_QUESTIONS = 5

// ─── Component ─────────────────────────────────────────────────────────────────

export const NewInterviewPage: React.FC = () => {
  const navigate = useNavigate()

  // Form state
  const [targetRole, setTargetRole] = useState('')
  const [difficulty, setDifficulty] = useState<Difficulty>('INTERMEDIATE')
  const [numberOfQuestions, setNumberOfQuestions] = useState(DEFAULT_QUESTIONS)

  // Submission workflow state
  const [step, setStep] = useState<CreationStep>('idle')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)

  // Keep the created interview when generation fails so retries never create
  // a duplicate record.
  const [createdInterviewId, setCreatedInterviewId] = useState<string | null>(null)

  const isSubmitting = step !== 'idle'
  const isRetryingGeneration = createdInterviewId !== null

  // ─── Validation ──────────────────────────────────────────────────────────────

  function validate(): boolean {
    setFieldError(null)
    if (!targetRole.trim()) {
      setFieldError('Target role is required.')
      return false
    }
    return true
  }

  // ─── Submission workflow ──────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isSubmitting) return
    if (!validate()) return

    setApiError(null)

    try {
      // ── Step A: Create interview (skip if retrying after a generation failure) ──
      let interviewId = createdInterviewId

      if (!interviewId) {
        setStep('creating')
        const interview = await createInterview({
          targetRole: targetRole.trim(),
          difficulty,
          numberOfQuestions,
        })
        interviewId = interview.id
        setCreatedInterviewId(interview.id)
      }

      // ── Step B: Generate questions (idempotent — safe to retry) ──────────────
      setStep('generating')
      const questions = await generateInterviewQuestions(interviewId)
      if (questions.length === 0) {
        throw new Error('No questions were returned. Retry question generation.')
      }

      // ── Step C: Navigate to the interview room ────────────────────────────────
      setStep('navigating')
      navigate(`/interviews/${interviewId}/room`)
    } catch (err: unknown) {
      setApiError(extractApiError(err))
      setStep('idle')
    }
  }

  // ─── Question stepper helpers ────────────────────────────────────────────────

  function increment() {
    setNumberOfQuestions((n) => Math.min(n + 1, MAX_QUESTIONS))
  }

  function decrement() {
    setNumberOfQuestions((n) => Math.max(n - 1, MIN_QUESTIONS))
  }

  function handleQuestionsInput(e: React.ChangeEvent<HTMLInputElement>) {
    const val = parseInt(e.target.value, 10)
    if (!isNaN(val)) {
      setNumberOfQuestions(Math.min(Math.max(val, MIN_QUESTIONS), MAX_QUESTIONS))
    }
  }

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 text-xs text-indigo-400 font-mono font-medium mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI-Powered Technical Interview</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
          Configure New Interview
        </h1>
        <p className="text-sm text-zinc-400 mt-1.5 leading-relaxed">
          Define the role and parameters. InterviewOS will generate a tailored question set
          with weighted evaluation criteria using the local{' '}
          <span className="font-mono text-indigo-400">qwen2.5:3b</span> model.
        </p>
      </div>

      {/* Form Card */}
      <form onSubmit={handleSubmit} noValidate className="space-y-6">

        {/* ── Target Role ─────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
              <Briefcase className="w-4 h-4 text-indigo-400" />
            </div>
            <label htmlFor="target-role" className="text-sm font-semibold text-zinc-200">
              Target Role
            </label>
            <span className="ml-auto text-[10px] font-mono text-rose-400 font-medium">Required</span>
          </div>

          <input
            id="target-role"
            type="text"
            value={targetRole}
            onChange={(e) => {
              setTargetRole(e.target.value)
              if (fieldError) setFieldError(null)
            }}
            placeholder="e.g. Backend Engineer, Software Engineer, Data Engineer"
            disabled={isSubmitting || isRetryingGeneration}
            aria-invalid={fieldError !== null}
            aria-describedby={fieldError ? 'role-error' : undefined}
            className={`
              w-full bg-zinc-950/60 border rounded-lg px-4 py-2.5 text-sm text-zinc-100
              placeholder-zinc-500 focus:outline-none focus:ring-2 transition-all duration-150
              disabled:opacity-50 disabled:cursor-not-allowed
              ${fieldError
                ? 'border-rose-500/60 focus:ring-rose-500/30'
                : 'border-zinc-700/60 hover:border-zinc-600/60 focus:ring-indigo-500/30 focus:border-indigo-500/50'
              }
            `}
          />

          {fieldError && (
            <p id="role-error" role="alert" className="flex items-center gap-1.5 text-xs text-rose-400">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              {fieldError}
            </p>
          )}

          <p className="text-[11px] text-zinc-500">
            Be specific — a precise role description produces better-calibrated questions and rubrics.
          </p>
        </div>

        {/* ── Difficulty ──────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-zinc-200">Difficulty Level</legend>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {DIFFICULTY_OPTIONS.map((opt) => {
              const Icon = opt.icon
              const isSelected = difficulty === opt.value
              return (
                <button
                  key={opt.value}
                  type="button"
                  aria-pressed={isSelected}
                  disabled={isSubmitting || isRetryingGeneration}
                  onClick={() => setDifficulty(opt.value)}
                  className={`
                    relative p-4 rounded-xl border text-left transition-all duration-150
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${isSelected
                      ? `${opt.activeBg} ${opt.borderClass} shadow-sm`
                      : 'bg-zinc-950/40 border-zinc-800/60 hover:border-zinc-700/60 hover:bg-zinc-800/30'
                    }
                  `}
                >
                  {isSelected && (
                    <span className="absolute top-3 right-3">
                      <CheckCircle2 className={`w-3.5 h-3.5 ${opt.accentClass}`} />
                    </span>
                  )}
                  <Icon className={`w-4.5 h-4.5 mb-2.5 ${isSelected ? opt.accentClass : 'text-zinc-500'}`} />
                  <div className={`text-sm font-semibold mb-1 ${isSelected ? opt.accentClass : 'text-zinc-300'}`}>
                    {opt.label}
                  </div>
                  <div className="text-[11px] text-zinc-500 leading-relaxed">
                    {opt.description}
                  </div>
                </button>
              )
            })}
          </div>
          </fieldset>
        </div>

        {/* ── Number of Questions ─────────────────────────────────────────────── */}
        <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-sm font-semibold text-zinc-200">Number of Questions</div>
              <p className="text-[11px] text-zinc-500">
                Each question includes weighted evaluation criteria.{' '}
                <span className="text-zinc-400">Recommended: 5–10 for a 45–60 min session.</span>
              </p>
            </div>

            {/* Stepper control */}
            <div className="flex items-center gap-0 border border-zinc-700/60 rounded-xl overflow-hidden shrink-0 ml-4">
              <button
                type="button"
                onClick={decrement}
                disabled={isSubmitting || isRetryingGeneration || numberOfQuestions <= MIN_QUESTIONS}
                aria-label="Decrease questions"
                className="px-3 py-2.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed border-r border-zinc-700/60"
              >
                <ChevronDown className="w-4 h-4" />
              </button>

              <input
                type="number"
                value={numberOfQuestions}
                onChange={handleQuestionsInput}
                min={MIN_QUESTIONS}
                max={MAX_QUESTIONS}
                disabled={isSubmitting || isRetryingGeneration}
                aria-label="Number of questions"
                className="w-14 text-center bg-transparent text-sm font-mono font-bold text-zinc-100 focus:outline-none py-2.5 disabled:opacity-50"
              />

              <button
                type="button"
                onClick={increment}
                disabled={isSubmitting || isRetryingGeneration || numberOfQuestions >= MAX_QUESTIONS}
                aria-label="Increase questions"
                className="px-3 py-2.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed border-l border-zinc-700/60"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Visual range indicator */}
          <div className="mt-5">
            <div className="flex justify-between text-[10px] text-zinc-600 font-mono mb-1.5">
              <span>1</span>
              <span>10</span>
              <span>20</span>
            </div>
            <div className="relative h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full transition-all duration-200"
                style={{ width: `${((numberOfQuestions - MIN_QUESTIONS) / (MAX_QUESTIONS - MIN_QUESTIONS)) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* ── API Error Banner ────────────────────────────────────────────────── */}
        {apiError && (
          <div
            role="alert"
            className="flex items-start gap-3 p-4 rounded-xl bg-rose-500/8 border border-rose-500/25"
          >
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1 min-w-0">
              <p className="text-sm font-medium text-rose-300">Setup failed</p>
              <p className="text-xs text-rose-400/80">{apiError}</p>
              {createdInterviewId && (
                <p className="text-[11px] text-zinc-400 mt-2">
                  Interview was created successfully. Clicking{' '}
                  <span className="font-semibold text-zinc-300">Generate Interview</span>{' '}
                  again will retry only the question generation step.
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── Progress Status Banner ──────────────────────────────────────────── */}
        {isSubmitting && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-indigo-500/8 border border-indigo-500/25">
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
            <div>
              <p className="text-sm font-medium text-indigo-300">{STEP_LABELS[step]}</p>
              {step === 'generating' && (
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Local model inference may take 20–60 seconds depending on hardware.
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── Submit Button ───────────────────────────────────────────────────── */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="
            w-full flex items-center justify-center gap-2.5
            px-6 py-3.5 rounded-xl
            bg-indigo-600 hover:bg-indigo-500
            disabled:bg-zinc-700 disabled:cursor-not-allowed
            text-white text-sm font-semibold
            shadow-lg shadow-indigo-600/20
            transition-all duration-150 active:scale-[0.99]
            focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/60
          "
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{step === 'creating' ? 'Creating...' : 'Generating Questions...'}</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>{isRetryingGeneration ? 'Retry Question Generation' : 'Generate Interview'}</span>
              <ArrowRight className="w-4 h-4 ml-auto" />
            </>
          )}
        </button>

        <p className="text-center text-[11px] text-zinc-600">
          Questions are generated locally via Ollama and persisted in PostgreSQL.
          No data is sent to external services.
        </p>
      </form>
    </div>
  )
}

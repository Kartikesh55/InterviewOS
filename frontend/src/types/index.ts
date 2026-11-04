export interface HealthResponse {
  status: string
  service: string
}

export interface NavItem {
  name: string
  path: string
  icon: string
  badge?: string
  disabled?: boolean
}

export interface SystemStatus {
  backend: 'online' | 'offline' | 'checking'
  database: 'connected' | 'disconnected'
  aiEngine: string
  latencyMs?: number
}

// ─── Interview domain types ───────────────────────────────────────────────────
// All field names are camelCase to match the backend Pydantic alias_generator.

export type Difficulty = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'

export type InterviewStatus = 'CREATED' | 'IN_PROGRESS' | 'COMPLETED'

export type QuestionSource = 'GENERATED' | 'FOLLOW_UP'

export interface CreateInterviewRequest {
  targetRole: string
  difficulty: Difficulty
  numberOfQuestions: number
}

export interface InterviewResponse {
  id: string
  targetRole: string
  difficulty: Difficulty
  numberOfQuestions: number
  status: InterviewStatus
  createdAt: string
}

export interface InterviewQuestionResponse {
  id: string
  questionText: string
  questionOrder: number
  source: QuestionSource
  evaluationCriteria: string[]
}

export interface InterviewDetailsResponse extends InterviewResponse {
  currentQuestionOrder: number | null
  questions: InterviewQuestionResponse[]
}

export type EvaluationStatus = 'PENDING' | 'COMPLETED' | 'FAILED'

export type CriterionAssessmentStatus =
  | 'COVERED'
  | 'PARTIALLY_COVERED'
  | 'MISSING'

export interface SubmitAnswerRequest {
  candidateAnswer: string
}

export interface CriterionAssessmentResponse {
  criterion: string
  status: CriterionAssessmentStatus
  evidence: string
}

export interface InterviewAnswerResponse {
  id: string
  questionId: string
  candidateAnswer: string
  submittedAt: string
  evaluationStatus: EvaluationStatus
  technicalAccuracy: number | null
  completeness: number | null
  clarity: number | null
  depth: number | null
  overallScore: number | null
  criterionAssessments: CriterionAssessmentResponse[]
  strengths: string[]
  missingConcepts: string[]
  feedback: string | null
  suggestedFollowUp: string | null
  suggestedFollowUpCriteria: string[]
}

export interface InterviewQuestionReportResponse extends InterviewQuestionResponse {
  answers: InterviewAnswerResponse[]
}

export interface InterviewReportResponse extends InterviewDetailsResponse {
  questions: InterviewQuestionReportResponse[]
}

// ─── UI-only types (not from backend) ────────────────────────────────────────

/** Used only in the dashboard sample-data table; not a backend schema. */
export interface InterviewSummary {
  id: string
  candidateName: string
  role: string
  status: InterviewStatus | 'PENDING' | 'FAILED'
  score?: number
  createdAt: string
}

/** Structured API error returned by FastAPI on 4xx/5xx. */
export interface ApiErrorResponse {
  message: string
  errors?: string[]
}

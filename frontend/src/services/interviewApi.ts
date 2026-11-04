import { AxiosError } from 'axios'
import apiClient from './api'
import type {
  CreateInterviewRequest,
  InterviewResponse,
  InterviewDetailsResponse,
  InterviewQuestionResponse,
  InterviewAnswerResponse,
  InterviewReportResponse,
  SubmitAnswerRequest,
  ApiErrorResponse,
} from '../types'

function readApiErrorResponse(value: unknown): ApiErrorResponse | null {
  if (typeof value !== 'object' || value === null || !('message' in value)) {
    return null
  }

  if (typeof value.message !== 'string') {
    return null
  }

  const errors =
    'errors' in value && Array.isArray(value.errors)
      ? value.errors.filter((item): item is string => typeof item === 'string')
      : []

  return { message: value.message, errors }
}

/**
 * Extract a user-friendly error message from an Axios error.
 * The FastAPI error contract is `{ message: string, errors?: string[] }`.
 */
export function extractApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = readApiErrorResponse(error.response?.data)
    const validationDetail = data?.errors?.find((item) => item.trim().length > 0)
    if (error.response?.status === 400 && validationDetail) {
      const detail = validationDetail
        .replace(/^(body|path|query)(\.[^:]+)?:\s*/i, '')
        .replace(/^Value error,\s*/i, '')
      return `Please check your input: ${detail}`
    }
    if (data?.message) return data.message
    if (error.response?.status === 404) return 'Resource not found.'
    if (error.response?.status === 409) return 'Operation conflicts with the current state.'
    if (error.response?.status === 422) return 'Invalid request. Please check your input.'
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return 'Request timed out. The model may be slow to respond.'
    }
    if (!error.response) return 'Cannot reach the server. Check that the backend is running on port 8000.'
    if (error.response.status >= 500) {
      return 'The interview service is temporarily unavailable. Please try again.'
    }
  }
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred. Please try again.'
}

// ─── Interview API ────────────────────────────────────────────────────────────

/**
 * Create a new interview record (status: CREATED).
 * POST /api/interviews — 201 Created
 */
export async function createInterview(
  data: CreateInterviewRequest
): Promise<InterviewResponse> {
  const response = await apiClient.post<InterviewResponse>('/api/interviews', data)
  return response.data
}

/**
 * Trigger LangGraph question generation for an existing interview.
 * Idempotent — if questions already exist they are returned without re-generating.
 * POST /api/interviews/{interviewId}/questions — 200 OK
 * No request body; role/difficulty/count are read from the interview record.
 */
export async function generateInterviewQuestions(
  interviewId: string
): Promise<InterviewQuestionResponse[]> {
  const response = await apiClient.post<InterviewQuestionResponse[]>(
    `/api/interviews/${interviewId}/questions`
  )
  return response.data
}

/**
 * Fetch the full interview details including all questions.
 * GET /api/interviews/{interviewId} — 200 OK
 */
export async function getInterview(
  interviewId: string
): Promise<InterviewDetailsResponse> {
  const response = await apiClient.get<InterviewDetailsResponse>(
    `/api/interviews/${interviewId}`
  )
  return response.data
}

/** Start an interview that is currently in CREATED state. */
export async function startInterview(interviewId: string): Promise<InterviewResponse> {
  const response = await apiClient.post<InterviewResponse>(
    `/api/interviews/${interviewId}/start`
  )
  return response.data
}

/** Fetch the persisted current question for an IN_PROGRESS interview. */
export async function getCurrentQuestion(
  interviewId: string
): Promise<InterviewQuestionResponse> {
  const response = await apiClient.get<InterviewQuestionResponse>(
    `/api/interviews/${interviewId}/current-question`
  )
  return response.data
}

/** Submit one answer for the current question; the backend returns HTTP 201. */
export async function submitAnswer(
  interviewId: string,
  questionId: string,
  data: SubmitAnswerRequest
): Promise<InterviewAnswerResponse> {
  const response = await apiClient.post<InterviewAnswerResponse>(
    `/api/interviews/${interviewId}/questions/${questionId}/answers`,
    data
  )
  return response.data
}

/** Advance to the next persisted question. */
export async function advanceToNextQuestion(
  interviewId: string
): Promise<InterviewQuestionResponse> {
  const response = await apiClient.post<InterviewQuestionResponse>(
    `/api/interviews/${interviewId}/next-question`
  )
  return response.data
}

/** Complete an IN_PROGRESS interview. */
export async function completeInterview(interviewId: string): Promise<InterviewResponse> {
  const response = await apiClient.post<InterviewResponse>(
    `/api/interviews/${interviewId}/complete`
  )
  return response.data
}

/** Load the persisted report, including answers and evaluations. */
export async function getInterviewReport(
  interviewId: string
): Promise<InterviewReportResponse> {
  const response = await apiClient.get<InterviewReportResponse>(
    `/api/interviews/${interviewId}/report`
  )
  return response.data
}

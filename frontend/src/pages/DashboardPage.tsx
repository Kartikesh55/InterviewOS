import React from 'react'
import { Link } from 'react-router-dom'
import {
  Users,
  BrainCircuit,
  Database,
  ArrowUpRight,
  Terminal,
  Play,
  Layers,
  Sparkles,
  Server,
} from 'lucide-react'
import { StatusBadge } from '../components/common/StatusBadge'
import { useHealthCheck } from '../hooks/useHealthCheck'
import type { InterviewSummary } from '../types'

const sampleInterviews: InterviewSummary[] = [
  {
    id: 'int-001',
    candidateName: 'Aditi Sharma',
    role: 'Senior Backend Engineer (Python/FastAPI)',
    status: 'COMPLETED',
    score: 88,
    createdAt: '2026-11-04 18:30',
  },
  {
    id: 'int-002',
    candidateName: 'Devansh Verma',
    role: 'Distributed Systems Architect',
    status: 'IN_PROGRESS',
    score: undefined,
    createdAt: '2026-11-04 19:45',
  },
  {
    id: 'int-003',
    candidateName: 'Kavita Nair',
    role: 'Full Stack Engineer (React/Postgres)',
    status: 'PENDING',
    score: undefined,
    createdAt: '2026-11-04 21:10',
  },
]

export const DashboardPage: React.FC = () => {
  const { health, loading, latencyMs } = useHealthCheck()

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2.5">
            Technical Interview Dashboard
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/60">
              Dev Mode
            </span>
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time telemetry, adaptive interview lifecycles, and LangGraph-powered evaluations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/interviews/new"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all duration-150 active:scale-95"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Start New Interview</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors">
          <div className="flex items-center justify-between text-zinc-400 mb-3">
            <span className="text-xs font-medium">Conducted Interviews</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-zinc-100 font-mono tracking-tight">3</div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-zinc-400">
            <span className="text-emerald-400 font-medium flex items-center">
              Active <ArrowUpRight className="w-3 h-3" />
            </span>
            <span>Recorded in PostgreSQL</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors">
          <div className="flex items-center justify-between text-zinc-400 mb-3">
            <span className="text-xs font-medium">Generated Questions</span>
            <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <BrainCircuit className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-zinc-100 font-mono tracking-tight">6</div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-zinc-400">
            <span className="text-indigo-400 font-mono">9 criteria</span>
            <span>rubric calibrated</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors">
          <div className="flex items-center justify-between text-zinc-400 mb-3">
            <span className="text-xs font-medium">AI Model Engine</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="text-lg font-bold text-zinc-100 font-mono tracking-tight">qwen2.5:3b</div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-zinc-400">
            <span className="text-emerald-400 font-medium">Ollama Live</span>
            <span>11434 local</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors">
          <div className="flex items-center justify-between text-zinc-400 mb-3">
            <span className="text-xs font-medium">Backend Health</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-emerald-400">
            {loading ? '...' : health?.status === 'UP' ? '200 OK' : 'OFFLINE'}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-zinc-400">
            <span className="font-mono text-zinc-300">
              {latencyMs !== null ? `${latencyMs}ms latency` : 'Standby'}
            </span>
          </div>
        </div>
      </div>

      {/* Infrastructure & Architecture Overview */}
      <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-zinc-200">Local Architecture Stack</h2>
          </div>
          <span className="text-xs text-zinc-500 font-mono">InterviewOS Pipeline</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800/60 flex items-start gap-3">
            <Terminal className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-medium text-zinc-200">Python 3.13 & FastAPI</div>
              <p className="text-[11px] text-zinc-400 mt-1">
                Async REST API running on port 8000 with Pydantic v2 validation and Alembic migrations.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800/60 flex items-start gap-3">
            <Database className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-medium text-zinc-200">PostgreSQL 17 Alpine</div>
              <p className="text-[11px] text-zinc-400 mt-1">
                Dockerized database reusing persistent <code className="text-zinc-300">interviewos-postgres-data</code> volume.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800/60 flex items-start gap-3">
            <BrainCircuit className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-medium text-zinc-200">LangGraph & Ollama</div>
              <p className="text-[11px] text-zinc-400 mt-1">
                Evaluations run outside database transactions with dedicated pending state and failure recovery.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Interviews Table */}
      <div className="rounded-xl bg-zinc-900/60 border border-zinc-800/80 overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800/80 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200">Recent Interview Sessions</h2>
            <p className="text-xs text-zinc-500 mt-0.5">Sample candidate evaluations in progress</p>
          </div>
          <button className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
            View All
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-950/50 text-zinc-400 border-b border-zinc-800/80 font-medium">
              <tr>
                <th className="px-6 py-3">Candidate</th>
                <th className="px-6 py-3">Target Role</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Score</th>
                <th className="px-6 py-3">Timestamp</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
              {sampleInterviews.map((interview) => (
                <tr key={interview.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-6 py-3.5 font-medium text-zinc-200 flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-zinc-800 flex items-center justify-center text-[10px] text-zinc-400 font-bold">
                      {interview.candidateName[0]}
                    </div>
                    {interview.candidateName}
                  </td>
                  <td className="px-6 py-3.5 text-zinc-400">{interview.role}</td>
                  <td className="px-6 py-3.5">
                    <StatusBadge status={interview.status} />
                  </td>
                  <td className="px-6 py-3.5 font-mono">
                    {interview.score !== undefined ? (
                      <span className="text-emerald-400 font-semibold">{interview.score}%</span>
                    ) : (
                      <span className="text-zinc-500">—</span>
                    )}
                  </td>
                  <td className="px-6 py-3.5 text-zinc-500 font-mono">{interview.createdAt}</td>
                  <td className="px-6 py-3.5 text-right">
                    <button className="text-xs text-zinc-400 hover:text-zinc-200 font-medium transition-colors">
                      Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

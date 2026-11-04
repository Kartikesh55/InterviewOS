import React from 'react'
import { Bell, Search, Activity, RefreshCw } from 'lucide-react'
import { useHealthCheck } from '../../hooks/useHealthCheck'

export const Header: React.FC = () => {
  const { health, loading, latencyMs, refresh } = useHealthCheck(20000)

  return (
    <header className="h-16 shrink-0 px-4 sm:px-8 flex items-center justify-between border-b border-zinc-800/80 bg-zinc-950/40 backdrop-blur-md sticky top-0 z-10">
      {/* Search Input */}
      <div className="relative hidden w-80 md:block">
        <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search interviews, candidates, rubrics... (Ctrl+K)"
          className="w-full bg-zinc-900/80 border border-zinc-800/80 rounded-lg pl-10 pr-4 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-colors"
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Backend Live Indicator */}
        <button
          onClick={refresh}
          title="Click to re-ping backend API"
          className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-zinc-800/80 hover:border-zinc-700 transition-colors text-xs text-zinc-300"
        >
          <Activity
            className={`w-3.5 h-3.5 ${
              health?.status === 'UP' ? 'text-emerald-400' : 'text-rose-400'
            }`}
          />
          <span>API:</span>
          <span className="font-mono font-medium text-zinc-200">
            {loading ? 'Pinging...' : health?.status === 'UP' ? 'Connected' : 'Offline'}
          </span>
          {latencyMs !== null && (
            <span className="hidden text-[10px] text-zinc-500 font-mono sm:inline">({latencyMs}ms)</span>
          )}
          <RefreshCw
            className={`w-3 h-3 text-zinc-500 hover:text-zinc-300 ml-0.5 ${
              loading ? 'animate-spin' : ''
            }`}
          />
        </button>

        {/* Notification Bell */}
        <button
          className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border border-transparent transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
        </button>

        {/* User Profile */}
        <div className="flex items-center gap-3 pl-2 border-l border-zinc-800/80">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-semibold text-xs text-white shadow-sm ring-1 ring-white/10">
            IO
          </div>
          <div className="hidden md:flex flex-col text-left">
            <span className="text-xs font-medium text-zinc-200 leading-tight">Interviewer</span>
            <span className="text-[10px] text-zinc-500">Lead Evaluator</span>
          </div>
        </div>
      </div>
    </header>
  )
}

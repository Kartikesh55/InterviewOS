import React from 'react'
import { Link } from 'react-router-dom'
import { Home } from 'lucide-react'

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-4">
      <div className="text-5xl font-black font-mono text-zinc-700">404</div>
      <h2 className="text-lg font-semibold text-zinc-200">Page Not Found</h2>
      <p className="text-xs text-zinc-500 max-w-sm">
        The requested InterviewOS view does not exist or has moved.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors"
      >
        <Home className="w-3.5 h-3.5" />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  )
}


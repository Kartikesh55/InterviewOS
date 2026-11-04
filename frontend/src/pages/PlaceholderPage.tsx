import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

interface PlaceholderPageProps {
  title: string
  subtitle: string
  milestone: string
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  subtitle,
  milestone,
}) => {
  return (
    <div className="p-8 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-4">
      <div className="flex items-center gap-2 text-xs text-indigo-400 font-mono">
        <span>Milestone: {milestone}</span>
      </div>
      <h2 className="text-xl font-bold text-zinc-100">{title}</h2>
      <p className="text-sm text-zinc-400">{subtitle}</p>
      <div className="pt-4">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </Link>
      </div>
    </div>
  )
}


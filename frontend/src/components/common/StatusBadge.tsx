import React from 'react'
import type { InterviewStatus } from '../../types'

interface StatusBadgeProps {
  status: InterviewStatus | 'ONLINE' | 'OFFLINE' | 'PENDING' | 'FAILED'
  label?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
  const displayLabel = label || status.replace('_', ' ')

  const getStyles = () => {
    switch (status) {
      case 'COMPLETED':
      case 'ONLINE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
      case 'IN_PROGRESS':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
      case 'PENDING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      case 'FAILED':
      case 'OFFLINE':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20'
      default:
        return 'bg-zinc-800 text-zinc-400 border-zinc-700'
    }
  }

  const getDotStyles = () => {
    switch (status) {
      case 'COMPLETED':
      case 'ONLINE':
        return 'bg-emerald-400'
      case 'IN_PROGRESS':
        return 'bg-indigo-400 animate-pulse'
      case 'PENDING':
        return 'bg-amber-400'
      case 'FAILED':
      case 'OFFLINE':
        return 'bg-rose-400'
      default:
        return 'bg-zinc-500'
    }
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStyles()}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${getDotStyles()}`} />
      {displayLabel}
    </span>
  )
}

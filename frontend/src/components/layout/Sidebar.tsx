import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  FileQuestion,
  BarChart3,
  Settings,
  Cpu,
  Radio,
  ExternalLink,
} from 'lucide-react'
import { useHealthCheck } from '../../hooks/useHealthCheck'

interface NavLinkItem {
  name: string
  to: string
  icon: React.ElementType
  badge?: string
  external?: boolean
}

const navItems: NavLinkItem[] = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Interviews', to: '/interviews', icon: Users, badge: 'Active' },
  { name: 'Question Bank', to: '/questions', icon: FileQuestion },
  { name: 'Analytics', to: '/analytics', icon: BarChart3 },
  { name: 'Settings', to: '/settings', icon: Settings },
]

export const Sidebar: React.FC = () => {
  const { health, loading } = useHealthCheck(15000)

  return (
    <aside className="hidden w-64 shrink-0 flex-col bg-zinc-900/60 backdrop-blur-xl border-r border-zinc-800/80 select-none md:flex">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-zinc-800/80">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 ring-1 ring-white/20">
          <Cpu className="w-5 h-5 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="font-semibold text-base text-zinc-100 tracking-tight flex items-center gap-1.5">
            InterviewOS
            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              v2.0
            </span>
          </span>
          <span className="text-xs text-zinc-400 font-medium">Adaptive Tech AI</span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
          Platform
        </div>
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `group flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border border-transparent'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 transition-transform group-hover:scale-105" />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700/60">
                  {item.badge}
                </span>
              )}
            </NavLink>
          )
        })}

        <div className="pt-6 px-3 pb-2 text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
          Developer
        </div>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border border-transparent transition-all duration-150"
        >
          <div className="flex items-center gap-3">
            <Radio className="w-4 h-4 text-emerald-400" />
            <span>FastAPI Docs</span>
          </div>
          <ExternalLink className="w-3.5 h-3.5 text-zinc-500" />
        </a>
      </nav>

      {/* System Telemetry Indicator Footer */}
      <div className="p-4 m-3 rounded-xl bg-zinc-950/60 border border-zinc-800/80">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-zinc-400">System Telemetry</span>
          <span
            className={`w-2 h-2 rounded-full ${
              loading
                ? 'bg-amber-400 animate-ping'
                : health?.status === 'UP'
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]'
                : 'bg-rose-500'
            }`}
          />
        </div>
        <div className="text-[11px] text-zinc-400 space-y-1">
          <div className="flex justify-between">
            <span className="text-zinc-400">Backend:</span>
            <span className="font-mono text-zinc-300">
              {loading ? 'Checking...' : health?.status === 'UP' ? 'Online (8000)' : 'Offline'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Model:</span>
            <span className="font-mono text-indigo-400">qwen2.5:3b</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

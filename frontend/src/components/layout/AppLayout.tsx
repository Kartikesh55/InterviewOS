import React from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

const mobileNavItems = [
  { label: 'Dashboard', to: '/' },
  { label: 'New Interview', to: '/interviews/new' },
  { label: 'Interviews', to: '/interviews' },
  { label: 'Questions', to: '/questions' },
  { label: 'Analytics', to: '/analytics' },
  { label: 'Settings', to: '/settings' },
]

export const AppLayout: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <nav
          aria-label="Mobile navigation"
          className="flex shrink-0 gap-1 overflow-x-auto border-b border-zinc-800/80 bg-zinc-950/70 px-3 py-2 md:hidden"
        >
          {mobileNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `shrink-0 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300'
                    : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 overflow-y-auto bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.08),rgba(255,255,255,0))] p-4 sm:p-8">
          <div className="max-w-7xl mx-auto space-y-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

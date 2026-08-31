import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { Scale } from 'lucide-react'
import { cn } from '@/lib/utils'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/barcode', label: 'Barcode' },
  { to: '/scan', label: 'Scan Product' },
  { to: '/history', label: 'Scan History' },
  { to: '/dashboard', label: 'Dashboard' },
]

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-white shadow-sm">
              <Scale className="h-5 w-5" />
            </span>
            <div className="leading-tight">
              <div className="font-display text-lg font-bold text-navy-900 tracking-tight">
                PackScan
              </div>
              <div className="text-[11px] text-slate-500">SIH26034 · Legal Metrology Screening</div>
            </div>
          </NavLink>
          <nav className="hidden md:flex items-center gap-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  cn(
                    'rounded-xl px-3 py-2 text-sm font-medium transition',
                    isActive
                      ? 'bg-navy-900 text-white'
                      : 'text-slate-600 hover:bg-navy-50 hover:text-navy-900',
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="md:hidden border-t border-slate-100 px-2 py-2 flex gap-1 overflow-x-auto">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                cn(
                  'shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium',
                  isActive ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-700',
                )
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-6xl px-4 py-8">{children}</main>
      <footer className="border-t border-slate-200 bg-white/70">
        <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
          PackScan prototype for Smart India Hackathon · Automated screening assistance only · Not a
          legal determination.
        </div>
      </footer>
    </div>
  )
}

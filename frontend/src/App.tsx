import React, { useState } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { TrendingUp, Upload, Database, BarChart2, Menu, X } from 'lucide-react'
import clsx from 'clsx'
import { DataRoom } from './pages/DataRoom'
import { ModelView } from './pages/ModelView'
import { ExtractedData } from './pages/ExtractedData'

const NAV_ITEMS = [
  { to: '/', label: 'Data Room', icon: Upload, end: true },
  { to: '/data', label: 'Extracted Data', icon: Database, end: false },
  { to: '/model', label: 'Model', icon: BarChart2, end: false },
]

function NavItem({ to, label, icon: Icon, end }: { to: string; label: string; icon: React.ElementType; end: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
          isActive
            ? 'bg-brand-600 text-white'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </NavLink>
  )
}

export default function App() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-screen-xl mx-auto px-4 h-14 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <span className="text-sm font-bold text-gray-900 hidden sm:block">
              Financial Modelling Platform
            </span>
            <span className="text-sm font-bold text-gray-900 sm:hidden">FinModel</span>
          </div>

          {/* Desktop nav */}
          <nav className="hidden sm:flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </nav>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen((v) => !v)}
            className="sm:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Mobile nav */}
        {mobileMenuOpen && (
          <div className="sm:hidden border-t border-gray-100 px-4 py-2 flex flex-col gap-1">
            {NAV_ITEMS.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-screen-xl mx-auto w-full px-4 py-6">
        <Routes>
          <Route path="/" element={<DataRoom />} />
          <Route path="/data" element={<ExtractedData />} />
          <Route path="/model" element={<ModelView />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        Financial Modelling Platform — Built with FastAPI + React
      </footer>
    </div>
  )
}

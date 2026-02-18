import React, { useState } from 'react'
import { Download, FileSpreadsheet, FileText, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import { exportApi } from '../services/api'
import { useAppStore } from '../store/appStore'

const SECTIONS = [
  { value: 'income_statement', label: 'P&L' },
  { value: 'balance_sheet', label: 'Balance Sheet' },
  { value: 'cashflow', label: 'Cash Flow' },
  { value: 'kpis', label: 'KPIs' },
]

export function ExportButtons() {
  const [open, setOpen] = useState(false)
  const { activeModelId, activeScenarioId } = useAppStore()

  if (!activeModelId) return null

  const downloadExcel = () => {
    window.open(exportApi.excel(activeModelId, activeScenarioId ?? undefined), '_blank')
    setOpen(false)
  }

  const downloadCsv = (section: string) => {
    window.open(exportApi.csv(activeModelId, section, activeScenarioId ?? undefined), '_blank')
    setOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="btn-secondary flex items-center gap-2"
      >
        <Download className="h-4 w-4" />
        Export
        <ChevronDown className={clsx('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-52 bg-white rounded-xl shadow-lg border border-gray-100 z-20 py-1.5 overflow-hidden">
            {/* Excel */}
            <button
              onClick={downloadExcel}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <FileSpreadsheet className="h-4 w-4 text-green-600" />
              <div className="text-left">
                <p className="font-medium">Excel Workbook</p>
                <p className="text-xs text-gray-400">All sheets + assumptions</p>
              </div>
            </button>

            {/* Divider */}
            <div className="my-1 border-t border-gray-100" />
            <p className="px-4 py-1 text-xs text-gray-400 uppercase tracking-wide font-medium">
              CSV by section
            </p>

            {/* CSV sections */}
            {SECTIONS.map((s) => (
              <button
                key={s.value}
                onClick={() => downloadCsv(s.value)}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <FileText className="h-4 w-4 text-blue-500" />
                {s.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

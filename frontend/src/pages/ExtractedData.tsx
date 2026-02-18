import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { financialApi } from '../services/api'
import type { FinancialSummary } from '../types'

const SECTIONS = [
  { key: 'income_statement', label: 'Income Statement' },
  { key: 'balance_sheet', label: 'Balance Sheet' },
  { key: 'cashflow', label: 'Cash Flow' },
  { key: 'kpis', label: 'KPIs' },
] as const

const LABEL_MAP: Record<string, string> = {
  revenue: 'Revenue',
  cogs: 'Cost of Revenue',
  gross_profit: 'Gross Profit',
  opex: 'Operating Expenses',
  ebitda: 'EBITDA',
  net_income: 'Net Income',
  cash: 'Cash',
  receivables: 'Receivables',
  debt: 'Debt',
  equity: 'Equity',
  operating_cf: 'Operating CF',
  net_cf: 'Net Cash Flow',
  headcount: 'Headcount',
  arr: 'ARR',
  mrr: 'MRR',
  churn_rate: 'Churn Rate',
}

export function ExtractedData() {
  const { data, isLoading, isError } = useQuery<FinancialSummary>({
    queryKey: ['financial-summary'],
    queryFn: () => financialApi.getSummary(),
  })

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const toggle = (key: string) => setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }))

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 gap-2 text-brand-500">
        <Loader2 className="h-6 w-6 animate-spin" />
        <span>Loading extracted data…</span>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="card text-center py-12 text-gray-400">
        <Database className="h-10 w-10 mx-auto mb-2 text-gray-300" />
        <p className="text-sm">No extracted data yet. Upload documents to get started.</p>
      </div>
    )
  }

  const hasAnyData = SECTIONS.some((s) => Object.keys(data[s.key] || {}).length > 0)

  if (!hasAnyData) {
    return (
      <div className="card text-center py-12 text-gray-400">
        <Database className="h-10 w-10 mx-auto mb-2 text-gray-300" />
        <p className="text-sm">No financial data extracted yet.</p>
        <p className="text-xs mt-1">Upload financial documents and wait for extraction to complete.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Database className="h-5 w-5 text-brand-500" />
        <h2 className="text-base font-semibold text-gray-900">Extracted Financial Data</h2>
        <span className="badge badge-blue">{data.periods.length} periods</span>
      </div>

      {SECTIONS.map((section) => {
        const sectionData = data[section.key]
        const rows = Object.entries(sectionData)
        if (rows.length === 0) return null
        const isCollapsed = collapsed[section.key]

        return (
          <div key={section.key} className="card overflow-hidden p-0">
            <button
              onClick={() => toggle(section.key)}
              className="w-full flex items-center gap-2 px-6 py-4 hover:bg-gray-50 transition-colors"
            >
              {isCollapsed ? (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              )}
              <h3 className="text-sm font-semibold text-gray-800">{section.label}</h3>
              <span className="badge badge-gray ml-auto">{rows.length} items</span>
            </button>

            {!isCollapsed && (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 border-t border-b border-gray-200">
                      <th className="px-4 py-2.5 text-left font-semibold text-gray-600 w-52">
                        Line Item
                      </th>
                      {data.periods.map((p) => (
                        <th key={p} className="px-4 py-2.5 text-right font-semibold text-gray-600">
                          {p}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {rows.map(([key, series], idx) => (
                      <tr key={key} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                        <td className="px-4 py-2.5 text-gray-700 font-medium">
                          {LABEL_MAP[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                        </td>
                        {data.periods.map((p) => {
                          const val = series[p]
                          return (
                            <td
                              key={p}
                              className={`px-4 py-2.5 text-right tabular-nums ${
                                val !== null && val < 0 ? 'text-red-600' : 'text-gray-900'
                              }`}
                            >
                              {val !== null
                                ? val.toLocaleString('en-US', { maximumFractionDigits: 1 })
                                : '—'}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

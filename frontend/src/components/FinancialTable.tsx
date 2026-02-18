import React, { useState } from 'react'
import clsx from 'clsx'

interface FinancialTableProps {
  title: string
  periods: string[]
  data: Record<string, Record<string, number | null>>
  currency?: string
  unitScale?: string
  highlightRows?: string[]
}

const LABEL_MAP: Record<string, string> = {
  revenue: 'Revenue',
  cogs: 'Cost of Revenue',
  gross_profit: 'Gross Profit',
  opex: 'Operating Expenses',
  ebitda: 'EBITDA',
  ebit: 'EBIT',
  interest: 'Interest',
  tax: 'Tax',
  net_income: 'Net Income',
  cash: 'Cash & Equivalents',
  receivables: 'Accounts Receivable',
  inventory: 'Inventory',
  fixed_assets: 'Fixed Assets',
  total_assets: 'Total Assets',
  payables: 'Accounts Payable',
  debt: 'Total Debt',
  equity: 'Equity',
  total_liabilities: 'Total Liabilities',
  operating_cf: 'Operating Cash Flow',
  investing_cf: 'Investing Cash Flow',
  financing_cf: 'Financing Cash Flow',
  net_cf: 'Net Cash Flow',
  capex: 'CapEx',
  headcount: 'Headcount',
  arr: 'ARR',
  mrr: 'MRR',
  churn_rate: 'Churn Rate',
  gross_margin_pct: 'Gross Margin %',
  ebitda_margin_pct: 'EBITDA Margin %',
}

const SUBTOTAL_ROWS = new Set(['gross_profit', 'ebitda', 'net_income', 'total_assets', 'net_cf'])
const PERCENT_ROWS = new Set(['gross_margin_pct', 'ebitda_margin_pct', 'churn_rate'])

function formatValue(val: number | null | undefined, isPercent: boolean, unitScale: string): string {
  if (val === null || val === undefined) return '—'
  if (isPercent) return `${val.toFixed(1)}%`
  const scale = unitScale === 'millions' ? 'm' : unitScale === 'thousands' ? 'k' : ''
  const formatted = Math.abs(val).toLocaleString('en-US', { maximumFractionDigits: 1 })
  const sign = val < 0 ? '(' : ''
  const endSign = val < 0 ? ')' : ''
  return `${sign}${formatted}${scale}${endSign}`
}

export function FinancialTable({
  title,
  periods,
  data,
  currency = 'USD',
  unitScale = 'thousands',
}: FinancialTableProps) {
  const [collapsed, setCollapsed] = useState(false)
  const rows = Object.entries(data)

  if (rows.length === 0) {
    return (
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">{title}</h3>
        <p className="text-sm text-gray-400 italic">No data available.</p>
      </div>
    )
  }

  const currencySymbols: Record<string, string> = { USD: '$', GBP: '£', EUR: '€' }
  const symbol = currencySymbols[currency] || '$'

  return (
    <div className="card overflow-hidden p-0">
      <button
        onClick={() => setCollapsed((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">{title}</h3>
        <span className="text-xs text-gray-400">{collapsed ? '▶ Show' : '▼ Hide'}</span>
      </button>

      {!collapsed && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-brand-900 text-white">
                <th className="px-4 py-3 text-left font-medium text-xs uppercase tracking-wider w-52">
                  Line Item ({symbol}{unitScale === 'thousands' ? "'000" : unitScale === 'millions' ? 'm' : ''})
                </th>
                {periods.map((p) => (
                  <th key={p} className="px-4 py-3 text-right font-medium text-xs uppercase tracking-wider">
                    {p}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(([key, series], rowIdx) => {
                const isSubtotal = SUBTOTAL_ROWS.has(key)
                const isPercent = PERCENT_ROWS.has(key)
                const label = LABEL_MAP[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

                return (
                  <tr
                    key={key}
                    className={clsx(
                      rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50',
                      isSubtotal && 'font-semibold border-t-2 border-gray-200 bg-blue-50!'
                    )}
                  >
                    <td
                      className={clsx(
                        'px-4 py-2.5 text-xs',
                        isSubtotal ? 'text-gray-900 font-semibold' : 'text-gray-700'
                      )}
                    >
                      {label}
                    </td>
                    {periods.map((p) => {
                      const val = series[p]
                      const isNegative = val !== null && val !== undefined && val < 0
                      return (
                        <td
                          key={p}
                          className={clsx(
                            'px-4 py-2.5 text-right text-xs tabular-nums',
                            isNegative ? 'text-red-600' : 'text-gray-900',
                            isSubtotal && 'font-semibold'
                          )}
                        >
                          {formatValue(val, isPercent, unitScale)}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Loader } from 'lucide-react'
import { modellingApi } from '../services/api'
import type { ModelSummary, SummaryRow } from '../types'
import clsx from 'clsx'

interface Props {
  scenario: string
}

function formatValue(value: number | null | undefined, isPercentage: boolean): string {
  if (value === null || value === undefined) return '—'
  if (isPercentage) {
    return `${value.toFixed(1)}%`
  }
  // Format as financial number with commas
  const abs = Math.abs(value)
  const sign = value < 0 ? '(' : ''
  const end = value < 0 ? ')' : ''

  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(1)}M${end}`
  }
  if (abs >= 1_000) {
    return `${sign}${Math.round(abs).toLocaleString()}${end}`
  }
  return `${sign}${abs.toFixed(0)}${end}`
}

function SectionRow({
  row,
  periods,
  forecastStart,
}: {
  row: SummaryRow
  periods: string[]
  forecastStart: string | null
}) {
  const isHighlight = ['revenue', 'gross_profit', 'ebitda', 'net_income', 'free_cash_flow'].includes(row.key)

  return (
    <tr
      className={clsx(
        'border-b border-slate-100 hover:bg-slate-50 transition',
        isHighlight && 'bg-slate-50 font-semibold'
      )}
    >
      <td className="financial-cell-label pl-6 sticky left-0 bg-white z-10 border-r border-slate-200">
        {row.label}
      </td>
      {periods.map((p) => {
        const val = row.values[p]
        const isForecast = forecastStart && p >= forecastStart
        return (
          <td
            key={p}
            className={clsx(
              'financial-cell',
              isForecast ? 'financial-cell-forecast' : '',
              val !== null && val < 0 && 'text-red-500'
            )}
          >
            {formatValue(val, row.is_percentage)}
          </td>
        )
      })}
    </tr>
  )
}

function Section({
  section,
  periods,
  forecastStart,
}: {
  section: { name: string; rows: SummaryRow[] }
  periods: string[]
  forecastStart: string | null
}) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <>
      <tr
        className="cursor-pointer select-none"
        onClick={() => setCollapsed(!collapsed)}
      >
        <td
          colSpan={periods.length + 1}
          className="financial-section-header"
        >
          <span className="inline-flex items-center gap-1">
            {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
            {section.name}
          </span>
        </td>
      </tr>
      {!collapsed &&
        section.rows.map((row) => (
          <SectionRow
            key={row.key}
            row={row}
            periods={periods}
            forecastStart={forecastStart}
          />
        ))}
    </>
  )
}

export default function FinancialTable({ scenario }: Props) {
  const { data: summary, isLoading, error } = useQuery<ModelSummary>({
    queryKey: ['modelSummary', scenario],
    queryFn: () => modellingApi.getSummary(scenario),
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400">
        <Loader size={24} className="animate-spin mr-2" />
        Loading model...
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400 text-sm">
        No model data. Upload documents and initialise the model to get started.
      </div>
    )
  }

  const { periods, sections, forecast_start } = summary

  return (
    <div className="overflow-auto scrollbar-thin rounded-lg border border-slate-200">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="bg-slate-800 text-white sticky top-0 z-20">
            <th className="financial-cell-label font-semibold sticky left-0 bg-slate-800 z-30 border-r border-slate-600 py-3 min-w-48">
              Line Item
            </th>
            {periods.map((p) => (
              <th
                key={p}
                className={clsx(
                  'financial-cell font-semibold py-3 min-w-28',
                  forecast_start && p >= forecast_start ? 'text-blue-300' : 'text-white'
                )}
              >
                {p}
                {forecast_start && p >= forecast_start && (
                  <span className="block text-xs text-blue-400 font-normal">forecast</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-slate-100">
          {sections.map((section) => (
            <Section
              key={section.name}
              section={section}
              periods={periods}
              forecastStart={forecast_start}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

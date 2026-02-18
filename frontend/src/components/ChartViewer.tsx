import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts'
import { Loader } from 'lucide-react'
import { modellingApi } from '../services/api'
import type { ChartDataPoint, SensitivityResult } from '../types'

const METRIC_OPTIONS = [
  { key: 'revenue', label: 'Revenue', color: '#1e3a5f', type: 'bar' },
  { key: 'gross_profit', label: 'Gross Profit', color: '#2563eb', type: 'bar' },
  { key: 'ebitda', label: 'EBITDA', color: '#16a34a', type: 'bar' },
  { key: 'net_income', label: 'Net Income', color: '#dc2626', type: 'line' },
  { key: 'operating_cashflow', label: 'Operating CF', color: '#9333ea', type: 'line' },
  { key: 'arr', label: 'ARR', color: '#0891b2', type: 'line' },
  { key: 'free_cash_flow', label: 'Free Cash Flow', color: '#ca8a04', type: 'line' },
]

function formatAxisValue(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return value.toFixed(0)
}

interface Props {
  scenario: string
  forecastStart?: string | null
  sensitivityData?: SensitivityResult[] | null
}

export default function ChartViewer({ scenario, forecastStart, sensitivityData }: Props) {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['revenue', 'ebitda', 'net_income'])
  const [chartType, setChartType] = useState<'financial' | 'sensitivity'>('financial')

  const { data: chartData, isLoading } = useQuery<ChartDataPoint[]>({
    queryKey: ['chartData', scenario, selectedMetrics],
    queryFn: () => modellingApi.getChartData(selectedMetrics, scenario),
    retry: false,
    enabled: chartType === 'financial',
  })

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((m) => m !== key) : [...prev, key]
    )
  }

  if (isLoading && chartType === 'financial') {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400">
        <Loader size={24} className="animate-spin mr-2" /> Loading chart...
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Chart type toggle */}
        <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
          <button
            onClick={() => setChartType('financial')}
            className={`px-3 py-1.5 transition ${chartType === 'financial' ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
          >
            Financial
          </button>
          <button
            onClick={() => setChartType('sensitivity')}
            className={`px-3 py-1.5 transition ${chartType === 'sensitivity' ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
            disabled={!sensitivityData}
          >
            Sensitivity
          </button>
        </div>

        {/* Metric toggles */}
        {chartType === 'financial' && (
          <div className="flex flex-wrap gap-1">
            {METRIC_OPTIONS.map((m) => (
              <button
                key={m.key}
                onClick={() => toggleMetric(m.key)}
                className={`px-2 py-1 text-xs rounded-full border transition ${
                  selectedMetrics.includes(m.key)
                    ? 'text-white border-transparent'
                    : 'bg-white text-slate-500 border-slate-200 hover:border-slate-400'
                }`}
                style={selectedMetrics.includes(m.key) ? { backgroundColor: m.color, borderColor: m.color } : {}}
              >
                {m.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Financial chart */}
      {chartType === 'financial' && chartData && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatAxisValue}
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                value != null ? `£${value.toLocaleString()}` : '—',
                METRIC_OPTIONS.find((m) => m.key === name)?.label || name,
              ]}
              contentStyle={{
                fontSize: 12,
                borderRadius: 8,
                border: '1px solid #e2e8f0',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
              }}
            />
            <Legend
              formatter={(value) => METRIC_OPTIONS.find((m) => m.key === value)?.label || value}
              wrapperStyle={{ fontSize: 12 }}
            />
            {forecastStart && (
              <ReferenceLine
                x={forecastStart}
                stroke="#94a3b8"
                strokeDasharray="4 4"
                label={{ value: 'Forecast', position: 'top', fontSize: 10, fill: '#94a3b8' }}
              />
            )}
            {selectedMetrics.map((key) => {
              const meta = METRIC_OPTIONS.find((m) => m.key === key)
              if (!meta) return null
              if (meta.type === 'bar') {
                return (
                  <Bar key={key} dataKey={key} fill={meta.color} opacity={0.85} radius={[2, 2, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={forecastStart && entry.period >= forecastStart ? `${meta.color}99` : meta.color}
                      />
                    ))}
                  </Bar>
                )
              }
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={meta.color}
                  strokeWidth={2}
                  dot={{ r: 3, fill: meta.color }}
                  activeDot={{ r: 5 }}
                />
              )
            })}
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* Sensitivity chart */}
      {chartType === 'sensitivity' && sensitivityData && sensitivityData.length > 0 && (
        <SensitivityChart data={sensitivityData} />
      )}

      {chartType === 'financial' && (!chartData || chartData.length === 0) && !isLoading && (
        <div className="flex items-center justify-center py-16 text-slate-400 text-sm">
          No chart data. Initialise the model first.
        </div>
      )}

      {chartType === 'sensitivity' && !sensitivityData && (
        <div className="flex items-center justify-center py-16 text-slate-400 text-sm">
          Run a sensitivity analysis command to see the tornado chart here.
        </div>
      )}
    </div>
  )
}

function SensitivityChart({ data }: { data: SensitivityResult[] }) {
  // Tornado chart: show output values vs assumption change
  const lastPeriod = Object.keys(data[0]?.output_values || {})[0]
  const chartData = data.map((d) => ({
    change: `${d.change_pct > 0 ? '+' : ''}${d.change_pct.toFixed(1)}%`,
    value: d.output_values[lastPeriod] ?? 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart layout="vertical" data={chartData} margin={{ top: 10, right: 20, left: 40, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis type="number" tickFormatter={formatAxisValue} tick={{ fontSize: 11 }} />
        <YAxis dataKey="change" type="category" tick={{ fontSize: 11 }} width={50} />
        <Tooltip formatter={(v: number) => [`£${v.toLocaleString()}`, 'Output Value']} />
        <Bar dataKey="value" radius={[0, 2, 2, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.value >= 0 ? '#16a34a' : '#dc2626'} />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}

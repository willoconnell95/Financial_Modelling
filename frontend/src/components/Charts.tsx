import React from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { ChartSpec } from '../types'

interface ChartPanelProps {
  charts: ChartSpec[]
}

export function ChartPanel({ charts }: ChartPanelProps) {
  if (charts.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-sm text-gray-400 italic">
          Charts will appear once the model has data. Execute a command to populate the model.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {charts.map((chart) => (
        <SingleChart key={chart.id} spec={chart} />
      ))}
    </div>
  )
}

function SingleChart({ spec }: { spec: ChartSpec }) {
  const data = spec.data.filter((d) => d.value !== null)

  const formatValue = (v: number) =>
    Math.abs(v) >= 1_000_000
      ? `${(v / 1_000_000).toFixed(1)}M`
      : Math.abs(v) >= 1_000
      ? `${(v / 1_000).toFixed(1)}K`
      : v.toFixed(1)

  return (
    <div className="card">
      <h4 className="text-sm font-semibold text-gray-800 mb-4">{spec.title}</h4>
      <ResponsiveContainer width="100%" height={220}>
        {spec.type === 'bar' ? (
          <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey={spec.xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatValue} />
            <Tooltip formatter={(v: number) => formatValue(v)} />
            <Bar dataKey={spec.yKey} fill={spec.color} radius={[3, 3, 0, 0]} />
          </BarChart>
        ) : spec.type === 'area' ? (
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey={spec.xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatValue} />
            <Tooltip formatter={(v: number) => formatValue(v)} />
            <Area type="monotone" dataKey={spec.yKey} fill={spec.color} stroke={spec.color} fillOpacity={0.2} />
          </AreaChart>
        ) : (
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey={spec.xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatValue} />
            <Tooltip formatter={(v: number) => formatValue(v)} />
            <Line
              type="monotone"
              dataKey={spec.yKey}
              stroke={spec.color}
              strokeWidth={2}
              dot={{ r: 4, fill: spec.color }}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

interface WaterfallData {
  name: string
  value: number
  isTotal?: boolean
}

export function WaterfallChart({ data, title }: { data: WaterfallData[]; title: string }) {
  return (
    <div className="card">
      <h4 className="text-sm font-semibold text-gray-800 mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar
            dataKey="value"
            radius={[3, 3, 0, 0]}
            fill="#3b82f6"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function SensitivityChart({
  data,
  variableLabel,
  outputMetric,
}: {
  data: { input_pct_change: number; output_value: number }[]
  variableLabel: string
  outputMetric: string
}) {
  const chartData = data.map((d) => ({
    change: `${d.input_pct_change > 0 ? '+' : ''}${d.input_pct_change}%`,
    output: d.output_value,
  }))

  return (
    <div className="card">
      <h4 className="text-sm font-semibold text-gray-800 mb-1">Sensitivity: {variableLabel}</h4>
      <p className="text-xs text-gray-500 mb-4">Impact on {outputMetric.replace(/_/g, ' ')}</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="change" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="output"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

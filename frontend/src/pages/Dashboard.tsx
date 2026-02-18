import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  BarChart3,
  Table2,
  Settings,
  RefreshCw,
  Loader,
  TrendingUp,
  ChevronDown,
} from 'lucide-react'
import { modellingApi } from '../services/api'
import FileUpload from '../components/FileUpload'
import InstructionConsole from '../components/InstructionConsole'
import FinancialTable from '../components/FinancialTable'
import ChartViewer from '../components/ChartViewer'
import ScenarioSelector from '../components/ScenarioSelector'
import ExportPanel from '../components/ExportPanel'
import type { ModelSummary, SensitivityResult } from '../types'
import clsx from 'clsx'

type Tab = 'table' | 'charts'

export default function Dashboard() {
  const [scenario, setScenario] = useState('base')
  const [activeTab, setActiveTab] = useState<Tab>('table')
  const [initialising, setInitialising] = useState(false)
  const [periodType, setPeriodType] = useState('annual')
  const [forecastPeriods, setForecastPeriods] = useState(3)
  const [sensitivityData, setSensitivityData] = useState<SensitivityResult[] | null>(null)
  const [showInitOptions, setShowInitOptions] = useState(false)
  const queryClient = useQueryClient()

  const { data: summary } = useQuery<ModelSummary>({
    queryKey: ['modelSummary', scenario],
    queryFn: () => modellingApi.getSummary(scenario),
    retry: false,
    staleTime: 5000,
  })

  const handleInit = async () => {
    setInitialising(true)
    try {
      const result = await modellingApi.init({
        period_type: periodType,
        forecast_periods: forecastPeriods,
        scenario,
      })
      toast.success(`Model initialised: ${result.line_items_loaded} line items loaded`)
      queryClient.invalidateQueries({ queryKey: ['modelSummary'] })
      queryClient.invalidateQueries({ queryKey: ['chartData'] })
      queryClient.invalidateQueries({ queryKey: ['scenarios'] })
      setShowInitOptions(false)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Initialisation failed. Upload and process documents first.'
      toast.error(msg)
    } finally {
      setInitialising(false)
    }
  }

  const handleCommandSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['modelSummary', scenario] })
    queryClient.invalidateQueries({ queryKey: ['chartData', scenario] })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* ── Left sidebar ──────────────────────────────────────────────── */}
      <aside className="w-72 bg-white border-r border-slate-200 flex flex-col gap-0 overflow-y-auto scrollbar-thin flex-shrink-0">
        {/* Logo */}
        <div className="px-4 py-3 border-b border-slate-200 flex items-center gap-2">
          <TrendingUp size={20} className="text-blue-600" />
          <div>
            <h1 className="text-sm font-bold text-slate-800">FinModel AI</h1>
            <p className="text-xs text-slate-400">Financial Modelling Platform</p>
          </div>
        </div>

        {/* Documents section */}
        <div className="px-4 py-3 border-b border-slate-200">
          <FileUpload />
        </div>

        {/* Scenarios section */}
        <div className="px-4 py-3 border-b border-slate-200">
          <ScenarioSelector activeScenario={scenario} onScenarioChange={setScenario} />
        </div>

        {/* Export section */}
        <div className="px-4 py-3">
          <ExportPanel scenario={scenario} />
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Toolbar */}
        <header className="bg-white border-b border-slate-200 px-5 py-2.5 flex items-center gap-3 flex-shrink-0">
          {/* Tab navigation */}
          <nav className="flex gap-1 flex-1">
            <TabButton
              active={activeTab === 'table'}
              onClick={() => setActiveTab('table')}
              icon={<Table2 size={14} />}
              label="Model Table"
            />
            <TabButton
              active={activeTab === 'charts'}
              onClick={() => setActiveTab('charts')}
              icon={<BarChart3 size={14} />}
              label="Charts"
            />
          </nav>

          {/* Status indicator */}
          {summary && (
            <div className="text-xs text-slate-500 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              {summary.periods.length} periods
              <span className="text-slate-300">|</span>
              <span className="capitalize">{summary.scenario}</span>
            </div>
          )}

          {/* Initialise button */}
          <div className="relative">
            <div className="flex">
              <button
                onClick={handleInit}
                disabled={initialising}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-l-lg hover:bg-blue-700 transition disabled:opacity-60"
              >
                {initialising ? <Loader size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                {summary ? 'Re-initialise' : 'Initialise Model'}
              </button>
              <button
                onClick={() => setShowInitOptions(!showInitOptions)}
                className="px-2 py-1.5 bg-blue-700 text-white text-xs rounded-r-lg hover:bg-blue-800 border-l border-blue-500 transition"
              >
                <ChevronDown size={12} />
              </button>
            </div>

            {showInitOptions && (
              <div className="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg p-3 z-50 min-w-48">
                <p className="text-xs font-semibold text-slate-700 mb-2">Model Settings</p>
                <label className="block text-xs text-slate-600 mb-1">Period Type</label>
                <select
                  value={periodType}
                  onChange={(e) => setPeriodType(e.target.value)}
                  className="w-full text-xs border border-slate-200 rounded px-2 py-1 mb-2"
                >
                  <option value="annual">Annual</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="monthly">Monthly</option>
                </select>
                <label className="block text-xs text-slate-600 mb-1">Forecast Periods</label>
                <input
                  type="number"
                  value={forecastPeriods}
                  onChange={(e) => setForecastPeriods(Number(e.target.value))}
                  min={1}
                  max={60}
                  className="w-full text-xs border border-slate-200 rounded px-2 py-1"
                />
              </div>
            )}
          </div>
        </header>

        {/* Content area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main view */}
          <main className="flex-1 overflow-auto p-4 scrollbar-thin">
            {activeTab === 'table' && <FinancialTable scenario={scenario} />}
            {activeTab === 'charts' && (
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <ChartViewer
                  scenario={scenario}
                  forecastStart={summary?.forecast_start}
                  sensitivityData={sensitivityData}
                />
              </div>
            )}
          </main>

          {/* ── Right sidebar: Instruction console ────────────────────── */}
          <aside className="w-80 bg-white border-l border-slate-200 flex flex-col flex-shrink-0 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-200 flex items-center gap-2">
              <Settings size={14} className="text-slate-400" />
              <h2 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Instruction Console
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
              <InstructionConsole
                scenario={scenario}
                onCommandSuccess={handleCommandSuccess}
              />

              {/* Assumptions summary */}
              {summary?.assumptions && Object.keys(summary.assumptions).length > 0 && (
                <div className="mt-4">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                    Assumptions
                  </h3>
                  <div className="flex flex-col gap-1">
                    {Object.entries(summary.assumptions)
                      .filter(([, v]) => v !== null)
                      .map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                          <span className="text-slate-600 capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-slate-800 font-medium font-mono">
                            {typeof value === 'number'
                              ? key.includes('rate') || key.includes('margin') || key.includes('pct')
                                ? `${(value * 100).toFixed(1)}%`
                                : value.toLocaleString()
                              : String(value)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition',
        active
          ? 'bg-slate-800 text-white'
          : 'text-slate-600 hover:bg-slate-100'
      )}
    >
      {icon}
      {label}
    </button>
  )
}

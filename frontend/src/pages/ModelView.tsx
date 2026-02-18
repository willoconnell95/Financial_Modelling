import React, { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, Loader2, AlertCircle } from 'lucide-react'
import { modelsApi } from '../services/api'
import { useAppStore } from '../store/appStore'
import { InstructionConsole } from '../components/InstructionConsole'
import { FinancialTable } from '../components/FinancialTable'
import { ChartPanel } from '../components/Charts'
import { ScenarioSelector } from '../components/ScenarioSelector'
import { ExportButtons } from '../components/ExportButtons'
import { ModelSetup } from '../components/ModelSetup'

export function ModelView() {
  const { activeModelId, activeScenarioId, modelOutput, setModelOutput, activeModel, setActiveModel } =
    useAppStore()

  // Load existing models on mount
  const { data: models = [], isLoading: modelsLoading } = useQuery({
    queryKey: ['models'],
    queryFn: modelsApi.list,
  })

  // Auto-select first model
  useEffect(() => {
    if (!activeModelId && models.length > 0) {
      setActiveModel(models[0])
    }
  }, [models, activeModelId, setActiveModel])

  // Load output for active model
  const { data: output, isLoading: outputLoading } = useQuery({
    queryKey: ['model-output', activeModelId, activeScenarioId],
    queryFn: () => modelsApi.getOutput(activeModelId!, activeScenarioId ?? undefined),
    enabled: !!activeModelId,
  })

  useEffect(() => {
    if (output) setModelOutput(output)
  }, [output, setModelOutput])

  const displayOutput = modelOutput || output

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <BarChart2 className="h-5 w-5 text-brand-500" />
          <h2 className="text-base font-semibold text-gray-900">
            {activeModel ? activeModel.name : 'Financial Model'}
          </h2>
          {activeModel && (
            <span className="badge badge-blue text-xs">
              {activeModel.forecast_start} → {activeModel.forecast_end}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ExportButtons />
          <ModelSetup />
        </div>
      </div>

      {/* Model selector chips */}
      {models.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {models.map((m) => (
            <button
              key={m.id}
              onClick={() => setActiveModel(m)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                activeModelId === m.id
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-white text-gray-700 border-gray-200 hover:border-brand-300'
              }`}
            >
              {m.name}
            </button>
          ))}
        </div>
      )}

      {/* No model yet */}
      {!activeModelId && !modelsLoading && (
        <div className="card text-center py-16">
          <BarChart2 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm mb-1">No model created yet.</p>
          <p className="text-gray-400 text-xs mb-4">
            Click "New Model" to configure your financial model, then issue commands.
          </p>
          <div className="flex justify-center">
            <ModelSetup />
          </div>
        </div>
      )}

      {activeModelId && (
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
          {/* Left panel: scenarios + console */}
          <div className="xl:col-span-1 space-y-4">
            <ScenarioSelector />
          </div>

          {/* Main content */}
          <div className="xl:col-span-3 space-y-4">
            {/* Console */}
            <div className="card p-0 overflow-hidden">
              <InstructionConsole />
            </div>

            {/* Loading */}
            {outputLoading && (
              <div className="flex items-center justify-center py-8 gap-2 text-brand-500">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Loading model output…</span>
              </div>
            )}

            {/* Charts */}
            {displayOutput && displayOutput.charts.length > 0 && (
              <ChartPanel charts={displayOutput.charts} />
            )}

            {/* Tables */}
            {displayOutput ? (
              <>
                <FinancialTable
                  title="Income Statement"
                  periods={displayOutput.periods}
                  data={displayOutput.income_statement}
                  currency={activeModel?.currency}
                  unitScale={activeModel?.unit_scale}
                />
                <FinancialTable
                  title="Balance Sheet"
                  periods={displayOutput.periods}
                  data={displayOutput.balance_sheet}
                  currency={activeModel?.currency}
                  unitScale={activeModel?.unit_scale}
                />
                <FinancialTable
                  title="Cash Flow Statement"
                  periods={displayOutput.periods}
                  data={displayOutput.cashflow}
                  currency={activeModel?.currency}
                  unitScale={activeModel?.unit_scale}
                />
                {Object.keys(displayOutput.kpis).length > 0 && (
                  <FinancialTable
                    title="KPIs & Operational Metrics"
                    periods={displayOutput.periods}
                    data={displayOutput.kpis}
                    currency={activeModel?.currency}
                    unitScale={activeModel?.unit_scale}
                  />
                )}
              </>
            ) : (
              !outputLoading && (
                <div className="card text-center py-12 text-gray-400 text-sm">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  Upload documents and issue commands to populate the model.
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}

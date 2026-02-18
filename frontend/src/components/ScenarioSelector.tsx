import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, CheckCircle, Layers } from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { modelsApi } from '../services/api'
import { useAppStore } from '../store/appStore'
import type { Scenario } from '../types'

export function ScenarioSelector() {
  const { activeModelId, activeScenarioId, setActiveScenario, setModelOutput } = useAppStore()
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const queryClient = useQueryClient()

  const { data: scenarios = [] } = useQuery({
    queryKey: ['scenarios', activeModelId],
    queryFn: () => modelsApi.listScenarios(activeModelId!),
    enabled: !!activeModelId,
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      modelsApi.createScenario(activeModelId!, { name: data.name, description: data.description }),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios', activeModelId] })
      toast.success(`Scenario "${scenario.name}" created`)
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
    },
    onError: () => toast.error('Failed to create scenario'),
  })

  const selectScenario = async (scenario: Scenario | null) => {
    const id = scenario?.id ?? null
    setActiveScenario(id)
    if (id && activeModelId) {
      try {
        const output = await modelsApi.getOutput(activeModelId, id)
        setModelOutput(output)
      } catch {
        // ignore
      }
    }
  }

  if (!activeModelId) return null

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="h-4 w-4 text-brand-500" />
        <h3 className="text-sm font-semibold text-gray-800">Scenarios</h3>
      </div>

      <div className="space-y-1.5">
        {/* All scenarios */}
        {[{ id: null, name: 'Base Case', is_base: true } as Partial<Scenario>, ...scenarios].map(
          (s, idx) => (
            <ScenarioItem
              key={s.id ?? 'base'}
              scenario={s}
              isActive={activeScenarioId === (s.id ?? null)}
              onClick={() => selectScenario(s.id ? s as Scenario : null)}
            />
          )
        )}
      </div>

      {/* Create scenario */}
      {!showCreate ? (
        <button
          onClick={() => setShowCreate(true)}
          className="mt-3 w-full flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 font-medium"
        >
          <Plus className="h-3.5 w-3.5" />
          New Scenario
        </button>
      ) : (
        <div className="mt-3 space-y-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Scenario name (e.g. Bear Case)"
            className="input text-xs"
          />
          <input
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Description (optional)"
            className="input text-xs"
          />
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate({ name: newName, description: newDesc })}
              disabled={!newName.trim() || createMutation.isPending}
              className="btn-primary text-xs py-1.5 flex-1"
            >
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="btn-secondary text-xs py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ScenarioItem({
  scenario,
  isActive,
  onClick,
}: {
  scenario: Partial<Scenario>
  isActive: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-xs transition-colors',
        isActive
          ? 'bg-brand-50 text-brand-700 border border-brand-200'
          : 'hover:bg-gray-50 text-gray-700 border border-transparent'
      )}
    >
      {isActive ? (
        <CheckCircle className="h-3.5 w-3.5 text-brand-500 shrink-0" />
      ) : (
        <div className="h-3.5 w-3.5 rounded-full border-2 border-gray-300 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{scenario.name}</p>
        {scenario.description && (
          <p className="text-gray-400 truncate">{scenario.description}</p>
        )}
      </div>
      {scenario.is_base && (
        <span className="badge badge-blue shrink-0">Base</span>
      )}
    </button>
  )
}

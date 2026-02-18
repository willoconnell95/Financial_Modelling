import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Plus, GitBranch } from 'lucide-react'
import { modellingApi } from '../services/api'
import type { Scenario } from '../types'
import clsx from 'clsx'

interface Props {
  activeScenario: string
  onScenarioChange: (scenario: string) => void
}

export default function ScenarioSelector({ activeScenario, onScenarioChange }: Props) {
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const queryClient = useQueryClient()

  const { data: scenarios = [] } = useQuery<Scenario[]>({
    queryKey: ['scenarios'],
    queryFn: modellingApi.listScenarios,
  })

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    try {
      await modellingApi.createScenario(name, activeScenario, name)
      queryClient.invalidateQueries({ queryKey: ['scenarios'] })
      onScenarioChange(name)
      toast.success(`Scenario "${name}" created`)
      setNewName('')
      setCreating(false)
    } catch {
      toast.error('Failed to create scenario')
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <GitBranch size={12} />
          Scenarios
        </h3>
        <button
          onClick={() => setCreating(!creating)}
          className="p-1 text-slate-400 hover:text-blue-500 rounded transition"
          title="New scenario"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Create new scenario form */}
      {creating && (
        <div className="flex gap-1">
          <input
            autoFocus
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="Scenario name..."
            className="flex-1 text-xs border border-slate-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim()}
            className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition disabled:opacity-50"
          >
            Create
          </button>
        </div>
      )}

      {/* Scenario list */}
      <div className="flex flex-col gap-1">
        {scenarios.length === 0 && (
          <p className="text-xs text-slate-400">No scenarios. Initialise the model first.</p>
        )}
        {scenarios.map((sc) => (
          <button
            key={sc.id}
            onClick={() => onScenarioChange(sc.scenario)}
            className={clsx(
              'flex items-center justify-between w-full px-2 py-1.5 rounded-md text-left text-xs transition',
              activeScenario === sc.scenario
                ? 'bg-blue-600 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:border-blue-300'
            )}
          >
            <span className="font-medium capitalize">{sc.scenario}</span>
            {activeScenario === sc.scenario && (
              <span className="text-blue-200 text-xs">active</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

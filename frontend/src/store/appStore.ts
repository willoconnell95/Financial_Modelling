import { create } from 'zustand'
import type { ModelState, Scenario, ModelOutput } from '../types'

interface AppState {
  activeModelId: number | null
  activeScenarioId: number | null
  activeModel: ModelState | null
  scenarios: Scenario[]
  modelOutput: ModelOutput | null
  commandHistory: string[]

  setActiveModel: (model: ModelState | null) => void
  setActiveScenario: (id: number | null) => void
  setScenarios: (scenarios: Scenario[]) => void
  setModelOutput: (output: ModelOutput | null) => void
  addCommandToHistory: (cmd: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeModelId: null,
  activeScenarioId: null,
  activeModel: null,
  scenarios: [],
  modelOutput: null,
  commandHistory: [],

  setActiveModel: (model) =>
    set({ activeModel: model, activeModelId: model?.id ?? null }),

  setActiveScenario: (id) => set({ activeScenarioId: id }),

  setScenarios: (scenarios) => set({ scenarios }),

  setModelOutput: (output) => set({ modelOutput: output }),

  addCommandToHistory: (cmd) =>
    set((state) => ({
      commandHistory: [cmd, ...state.commandHistory].slice(0, 50),
    })),
}))

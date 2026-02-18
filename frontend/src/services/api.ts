import axios from 'axios'
import type {
  Document,
  DocumentListResponse,
  FinancialSummary,
  ModelState,
  ModelOutput,
  Scenario,
  CommandResult,
  SensitivityResult,
} from '../types'

const BASE = '/api/v1'

const client = axios.create({ baseURL: BASE })

// ── Documents ───────────────────────────────────────────────────────────────

export const documentsApi = {
  upload: async (file: File): Promise<Document> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await client.post<Document>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  list: async (): Promise<DocumentListResponse> => {
    const { data } = await client.get<DocumentListResponse>('/documents')
    return data
  },

  get: async (id: number): Promise<Document> => {
    const { data } = await client.get<Document>(`/documents/${id}`)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/documents/${id}`)
  },

  getStatus: async (id: number) => {
    const { data } = await client.get(`/documents/${id}/extraction-status`)
    return data
  },
}

// ── Financial data ──────────────────────────────────────────────────────────

export const financialApi = {
  getSummary: async (documentId?: number): Promise<FinancialSummary> => {
    const params = documentId ? { document_id: documentId } : {}
    const { data } = await client.get<FinancialSummary>('/financial-data/summary', { params })
    return data
  },

  getPeriods: async () => {
    const { data } = await client.get('/financial-data/periods')
    return data
  },

  getRecords: async (params?: { document_id?: number; category?: string }) => {
    const { data } = await client.get('/financial-data/records', { params })
    return data
  },
}

// ── Models ──────────────────────────────────────────────────────────────────

export const modelsApi = {
  list: async (): Promise<ModelState[]> => {
    const { data } = await client.get<ModelState[]>('/models')
    return data
  },

  create: async (payload: {
    name: string
    description?: string
    forecast_start?: string
    forecast_end?: string
    forecast_frequency?: string
    currency?: string
    unit_scale?: string
  }): Promise<ModelState> => {
    const { data } = await client.post<ModelState>('/models', payload)
    return data
  },

  get: async (id: number): Promise<ModelState> => {
    const { data } = await client.get<ModelState>(`/models/${id}`)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/models/${id}`)
  },

  getOutput: async (id: number, scenarioId?: number): Promise<ModelOutput> => {
    const params = scenarioId ? { scenario_id: scenarioId } : {}
    const { data } = await client.get<ModelOutput>(`/models/${id}/output`, { params })
    return data
  },

  executeCommand: async (payload: {
    command: string
    model_state_id: number
    scenario_id?: number
  }): Promise<CommandResult> => {
    const { data } = await client.post<CommandResult>('/models/command', payload)
    return data
  },

  listScenarios: async (modelId: number): Promise<Scenario[]> => {
    const { data } = await client.get<Scenario[]>(`/models/${modelId}/scenarios`)
    return data
  },

  createScenario: async (
    modelId: number,
    payload: { name: string; description?: string; is_base?: boolean; overrides?: Record<string, unknown> }
  ): Promise<Scenario> => {
    const { data } = await client.post<Scenario>(`/models/${modelId}/scenarios`, payload)
    return data
  },

  runSensitivity: async (payload: {
    model_state_id: number
    scenario_id?: number
    variable_key: string
    range_pct?: number
    steps?: number
    output_metric?: string
  }): Promise<SensitivityResult> => {
    const { data } = await client.post<SensitivityResult>('/models/sensitivity', payload)
    return data
  },
}

// ── Export ──────────────────────────────────────────────────────────────────

export const exportApi = {
  excel: (modelId: number, scenarioId?: number): string => {
    const params = scenarioId ? `?scenario_id=${scenarioId}` : ''
    return `${BASE}/export/excel/${modelId}${params}`
  },

  csv: (modelId: number, section: string, scenarioId?: number): string => {
    const params = new URLSearchParams({ section })
    if (scenarioId) params.set('scenario_id', String(scenarioId))
    return `${BASE}/export/csv/${modelId}?${params}`
  },
}

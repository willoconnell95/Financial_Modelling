import axios from 'axios'
import type {
  Document,
  LineItem,
  ModelSummary,
  Scenario,
  CommandResult,
  CommandHistory,
  ChartDataPoint,
  SensitivityResult,
} from '../types'

const BASE_URL = '/api'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
})

// ── Documents ────────────────────────────────────────────────────────────────

export const documentsApi = {
  upload: async (files: File[]): Promise<{ uploaded: Array<{ id?: number; filename: string; status: string; error?: string }> }> => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    const resp = await client.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return resp.data
  },

  list: async (): Promise<Document[]> => {
    const resp = await client.get('/documents')
    return resp.data.documents
  },

  get: async (id: number): Promise<Document> => {
    const resp = await client.get(`/documents/${id}`)
    return resp.data
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/documents/${id}`)
  },

  reparse: async (id: number): Promise<void> => {
    await client.post(`/documents/${id}/parse`)
  },

  getTables: async (id: number) => {
    const resp = await client.get(`/documents/${id}/tables`)
    return resp.data.tables
  },
}

// ── Extraction ───────────────────────────────────────────────────────────────

export const extractionApi = {
  listLineItems: async (filters?: { category?: string; normalized_name?: string }): Promise<LineItem[]> => {
    const resp = await client.get('/extraction/line-items', { params: filters })
    return resp.data.line_items
  },

  getSummary: async () => {
    const resp = await client.get('/extraction/line-items/summary')
    return resp.data.summary
  },

  getByDocument: async (docId: number): Promise<LineItem[]> => {
    const resp = await client.get(`/extraction/by-document/${docId}`)
    return resp.data.line_items
  },

  updateLineItem: async (id: number, updates: Partial<LineItem>): Promise<LineItem> => {
    const resp = await client.patch(`/extraction/line-items/${id}`, updates)
    return resp.data
  },

  deleteLineItem: async (id: number): Promise<void> => {
    await client.delete(`/extraction/line-items/${id}`)
  },
}

// ── Modelling ────────────────────────────────────────────────────────────────

export const modellingApi = {
  init: async (params: {
    period_type?: string
    forecast_periods?: number
    scenario?: string
    document_ids?: number[]
  }) => {
    const resp = await client.post('/modelling/init', params)
    return resp.data
  },

  getState: async (scenario = 'base') => {
    const resp = await client.get('/modelling/state', { params: { scenario } })
    return resp.data
  },

  getSummary: async (scenario = 'base'): Promise<ModelSummary> => {
    const resp = await client.get('/modelling/summary', { params: { scenario } })
    return resp.data
  },

  getChartData: async (metrics: string[], scenario = 'base'): Promise<ChartDataPoint[]> => {
    const resp = await client.get('/modelling/chart-data', {
      params: { metrics: metrics.join(','), scenario },
    })
    return resp.data.chart_data
  },

  executeCommand: async (command: string, scenario = 'base'): Promise<CommandResult> => {
    const resp = await client.post('/modelling/command', { command, scenario })
    return resp.data
  },

  listScenarios: async (): Promise<Scenario[]> => {
    const resp = await client.get('/modelling/scenarios')
    return resp.data.scenarios
  },

  createScenario: async (name: string, base_scenario = 'base', description?: string) => {
    const resp = await client.post('/modelling/scenarios', { name, base_scenario, description })
    return resp.data
  },

  getCommandHistory: async (): Promise<CommandHistory[]> => {
    const resp = await client.get('/modelling/commands')
    return resp.data.commands
  },

  runSensitivity: async (params: {
    variable: string
    output_metric: string
    range_pct?: number
    steps?: number
    scenario?: string
  }): Promise<SensitivityResult[]> => {
    const resp = await client.post('/modelling/sensitivity', params)
    return resp.data.results
  },
}

// ── Export ───────────────────────────────────────────────────────────────────

export const exportApi = {
  downloadExcel: async (scenario = 'base') => {
    const resp = await client.get('/export/excel', {
      params: { scenario },
      responseType: 'blob',
    })
    return resp.data
  },

  downloadCsv: async (scenario = 'base') => {
    const resp = await client.get('/export/csv', {
      params: { scenario },
      responseType: 'blob',
    })
    return resp.data
  },

  downloadRawData: async () => {
    const resp = await client.get('/export/raw-data/csv', { responseType: 'blob' })
    return resp.data
  },
}

// ── Utility ──────────────────────────────────────────────────────────────────

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

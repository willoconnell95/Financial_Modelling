export interface Document {
  id: number
  filename: string
  original_filename: string
  file_size: number
  mime_type: string | null
  document_type: string
  status: 'uploaded' | 'processing' | 'processed' | 'failed'
  page_count: number | null
  extraction_confidence: number | null
  extraction_errors: { errors: string[]; warnings: string[] } | null
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  total: number
  documents: Document[]
}

export interface ExtractedTable {
  id: number
  document_id: number
  page_number: number | null
  table_index: number
  headers: string[] | null
  data: { columns: string[]; rows: (string | null)[][] }
  confidence: number | null
  table_type: string | null
  created_at: string
}

export interface FinancialRecord {
  id: number
  document_id: number | null
  period_id: number | null
  category: string
  subcategory: string | null
  line_item: string
  value: number | null
  currency: string
  unit: string | null
  is_calculated: boolean
  confidence: number | null
  created_at: string
}

export interface FinancialSummary {
  periods: string[]
  income_statement: Record<string, Record<string, number | null>>
  balance_sheet: Record<string, Record<string, number | null>>
  cashflow: Record<string, Record<string, number | null>>
  kpis: Record<string, Record<string, number | null>>
}

export interface ModelState {
  id: number
  name: string
  description: string | null
  status: string
  currency: string
  unit_scale: string
  forecast_start: string | null
  forecast_end: string | null
  forecast_frequency: string
  assumptions: Record<string, unknown> | null
  command_history: { command: string; interpreted_as: string }[] | null
  created_at: string
  updated_at: string
}

export interface Scenario {
  id: number
  model_state_id: number
  name: string
  description: string | null
  is_base: boolean
  overrides: Record<string, unknown> | null
  computed_data: ModelOutput | null
  created_at: string
  updated_at: string
}

export interface ModelOutput {
  model_state_id: number
  scenario_id: number | null
  periods: string[]
  income_statement: Record<string, Record<string, number | null>>
  balance_sheet: Record<string, Record<string, number | null>>
  cashflow: Record<string, Record<string, number | null>>
  kpis: Record<string, Record<string, number | null>>
  assumptions: Record<string, unknown>
  charts: ChartSpec[]
}

export interface ChartSpec {
  id: string
  title: string
  type: 'bar' | 'line' | 'area'
  data: { period: string; value: number | null }[]
  xKey: string
  yKey: string
  color: string
}

export interface CommandResult {
  success: boolean
  command: string
  interpreted_as: string
  operations_performed: string[]
  updated_variables: string[]
  message: string
  model_output: ModelOutput | null
  errors: string[]
}

export interface SensitivityResult {
  variable_key: string
  variable_label: string
  output_metric: string
  data_points: { input_pct_change: number; input_value: number; output_value: number }[]
}

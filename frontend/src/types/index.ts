// ── Document types ─────────────────────────────────────────────────────────

export interface Document {
  id: number
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  status: DocumentStatus
  extraction_confidence: number | null
  error_message: string | null
  page_count: number | null
  doc_metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type DocumentStatus =
  | 'uploaded'
  | 'parsing'
  | 'parsed'
  | 'extracting'
  | 'extracted'
  | 'failed'

// ── Financial data types ───────────────────────────────────────────────────

export interface LineItem {
  id: number
  document_id: number
  category: string
  subcategory: string | null
  line_item_name: string
  normalized_name: string
  period: string
  period_type: string
  value: number
  unit: string
  is_forecast: boolean
  confidence_score: number
}

export interface ExtractedTable {
  id: number
  document_id: number
  table_index: number
  page_number: number | null
  headers: string[]
  raw_data: Record<string, unknown>[]
  table_type: string | null
  confidence_score: number
}

// ── Model types ────────────────────────────────────────────────────────────

export interface ModelState {
  id: number
  scenario: string
  time_config: TimeConfig
  assumptions: Record<string, number | null>
  line_items: Record<string, Record<string, number | null>>
  formulas: Record<string, string>
}

export interface TimeConfig {
  period_type: 'monthly' | 'quarterly' | 'annual'
  historical_periods: string[]
  forecast_periods: string[]
  all_periods: string[]
  forecast_start: string | null
}

// ── Summary table types ────────────────────────────────────────────────────

export interface ModelSummary {
  periods: string[]
  forecast_start: string | null
  sections: SummarySection[]
  assumptions: Record<string, number | null>
  scenario: string
}

export interface SummarySection {
  name: string
  rows: SummaryRow[]
}

export interface SummaryRow {
  key: string
  label: string
  values: Record<string, number | null>
  is_percentage: boolean
}

// ── Chart types ────────────────────────────────────────────────────────────

export interface ChartDataPoint {
  period: string
  [metric: string]: number | null | string
}

// ── Scenario types ─────────────────────────────────────────────────────────

export interface Scenario {
  id: number
  name: string
  scenario: string
  updated_at: string
}

// ── Command types ──────────────────────────────────────────────────────────

export interface CommandResult {
  status: 'success' | 'failed' | 'partial'
  operation?: string
  explanation: string
  model_id?: number
  summary?: ModelSummary
  results?: SensitivityResult[]
  suggestion?: string
  scenario_created?: string
}

export interface CommandHistory {
  id: number
  command: string
  parsed_intent: Record<string, unknown> | null
  result_summary: string | null
  status: string
  scenario: string | null
  created_at: string
}

// ── Sensitivity ────────────────────────────────────────────────────────────

export interface SensitivityResult {
  assumption: string
  assumption_value: number
  change_pct: number
  output_metric: string
  output_values: Record<string, number | null>
}

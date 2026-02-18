import { useState } from 'react'
import toast from 'react-hot-toast'
import { Download, FileSpreadsheet, FileText, Database } from 'lucide-react'
import { exportApi, downloadBlob } from '../services/api'

interface Props {
  scenario: string
}

export default function ExportPanel({ scenario }: Props) {
  const [downloading, setDownloading] = useState<string | null>(null)

  const handleExport = async (type: 'excel' | 'csv' | 'raw') => {
    setDownloading(type)
    try {
      let blob: Blob
      let filename: string

      if (type === 'excel') {
        blob = await exportApi.downloadExcel(scenario)
        filename = `financial_model_${scenario}.xlsx`
      } else if (type === 'csv') {
        blob = await exportApi.downloadCsv(scenario)
        filename = `financial_model_${scenario}.csv`
      } else {
        blob = await exportApi.downloadRawData()
        filename = 'extracted_data.csv'
      }

      downloadBlob(blob, filename)
      toast.success(`${filename} downloaded`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Export failed'
      toast.error(msg)
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
        <Download size={12} />
        Export
      </h3>

      <div className="flex flex-col gap-1.5">
        <ExportButton
          icon={<FileSpreadsheet size={14} />}
          label="Excel Workbook"
          description="Full model with charts"
          onClick={() => handleExport('excel')}
          loading={downloading === 'excel'}
        />
        <ExportButton
          icon={<FileText size={14} />}
          label="CSV (Model)"
          description="Flat format"
          onClick={() => handleExport('csv')}
          loading={downloading === 'csv'}
        />
        <ExportButton
          icon={<Database size={14} />}
          label="Raw Extracted Data"
          description="All extracted line items"
          onClick={() => handleExport('raw')}
          loading={downloading === 'raw'}
        />
      </div>
    </div>
  )
}

function ExportButton({
  icon,
  label,
  description,
  onClick,
  loading,
}: {
  icon: React.ReactNode
  label: string
  description: string
  onClick: () => void
  loading: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-2 w-full px-3 py-2 rounded-lg border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50 transition text-left disabled:opacity-60"
    >
      <span className="text-slate-500">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700">{label}</p>
        <p className="text-xs text-slate-400">{description}</p>
      </div>
      {loading ? (
        <div className="w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin" />
      ) : (
        <Download size={13} className="text-slate-400" />
      )}
    </button>
  )
}

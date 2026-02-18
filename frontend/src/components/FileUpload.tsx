import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Upload, FileText, Trash2, RefreshCw, CheckCircle, AlertCircle, Clock, Loader } from 'lucide-react'
import { documentsApi } from '../services/api'
import type { Document, DocumentStatus } from '../types'
import clsx from 'clsx'

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'text/csv': ['.csv'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/tiff': ['.tiff', '.tif'],
}

function StatusBadge({ status }: { status: DocumentStatus }) {
  const configs: Record<DocumentStatus, { icon: React.ReactNode; label: string; className: string }> = {
    uploaded: { icon: <Clock size={12} />, label: 'Queued', className: 'bg-yellow-100 text-yellow-800' },
    parsing: { icon: <Loader size={12} className="animate-spin" />, label: 'Parsing', className: 'bg-blue-100 text-blue-800' },
    parsed: { icon: <Loader size={12} className="animate-spin" />, label: 'Parsed', className: 'bg-blue-100 text-blue-800' },
    extracting: { icon: <Loader size={12} className="animate-spin" />, label: 'Extracting', className: 'bg-indigo-100 text-indigo-800' },
    extracted: { icon: <CheckCircle size={12} />, label: 'Ready', className: 'bg-green-100 text-green-800' },
    failed: { icon: <AlertCircle size={12} />, label: 'Failed', className: 'bg-red-100 text-red-800' },
  }
  const cfg = configs[status] || configs.uploaded
  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', cfg.className)}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function FileUpload() {
  const [uploading, setUploading] = useState(false)
  const queryClient = useQueryClient()

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
    refetchInterval: (data) => {
      const active = (data as Document[] | undefined)?.some(
        (d) => ['uploaded', 'parsing', 'parsed', 'extracting'].includes(d.status)
      )
      return active ? 3000 : false
    },
  })

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!acceptedFiles.length) return
      setUploading(true)
      try {
        const result = await documentsApi.upload(acceptedFiles)
        const succeeded = result.uploaded.filter((u) => u.status === 'uploaded').length
        const failed = result.uploaded.filter((u) => u.status === 'rejected').length
        if (succeeded > 0) toast.success(`${succeeded} file(s) uploaded successfully`)
        if (failed > 0) toast.error(`${failed} file(s) rejected`)
        queryClient.invalidateQueries({ queryKey: ['documents'] })
      } catch {
        toast.error('Upload failed. Please try again.')
      } finally {
        setUploading(false)
      }
    },
    [queryClient]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  })

  const handleDelete = async (id: number) => {
    try {
      await documentsApi.delete(id)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Document deleted')
    } catch {
      toast.error('Failed to delete document')
    }
  }

  const handleReparse = async (id: number) => {
    try {
      await documentsApi.reparse(id)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Reprocessing started')
    } catch {
      toast.error('Failed to restart processing')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all',
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50',
          uploading && 'opacity-50 cursor-not-allowed'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2">
          {uploading ? (
            <Loader size={32} className="animate-spin text-blue-500" />
          ) : (
            <Upload size={32} className={isDragActive ? 'text-blue-500' : 'text-slate-400'} />
          )}
          <p className="text-sm font-medium text-slate-700">
            {uploading ? 'Uploading...' : isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-xs text-slate-500">
            PDF, Excel, CSV, Word, Images — up to 50MB each
          </p>
          {!uploading && (
            <button
              type="button"
              className="mt-1 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition"
            >
              Browse Files
            </button>
          )}
        </div>
      </div>

      {/* Document list */}
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Documents ({documents.length})
        </h3>
        {isLoading && (
          <p className="text-xs text-slate-400 py-2">Loading...</p>
        )}
        {!isLoading && documents.length === 0 && (
          <p className="text-xs text-slate-400 py-2">No documents uploaded yet.</p>
        )}
        <div className="flex flex-col gap-1 max-h-96 overflow-y-auto scrollbar-thin">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-start gap-2 p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300 transition"
            >
              <FileText size={16} className="text-slate-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-800 truncate" title={doc.original_filename}>
                  {doc.original_filename}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <StatusBadge status={doc.status} />
                  <span className="text-xs text-slate-400">{formatBytes(doc.file_size)}</span>
                  {doc.extraction_confidence != null && (
                    <span className="text-xs text-slate-400">
                      {(doc.extraction_confidence * 100).toFixed(0)}% conf.
                    </span>
                  )}
                </div>
                {doc.error_message && (
                  <p className="text-xs text-red-500 mt-0.5 truncate" title={doc.error_message}>
                    {doc.error_message}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {doc.status === 'failed' && (
                  <button
                    onClick={() => handleReparse(doc.id)}
                    className="p-1 text-slate-400 hover:text-blue-500 rounded transition"
                    title="Reprocess"
                  >
                    <RefreshCw size={13} />
                  </button>
                )}
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-1 text-slate-400 hover:text-red-500 rounded transition"
                  title="Delete"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

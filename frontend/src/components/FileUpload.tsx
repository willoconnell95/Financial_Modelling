import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { documentsApi } from '../services/api'
import type { Document } from '../types'

interface UploadedFile {
  file: File
  status: 'uploading' | 'processing' | 'done' | 'error'
  document?: Document
  error?: string
  progress: number
}

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

export function FileUpload() {
  const [uploads, setUploads] = useState<UploadedFile[]>([])
  const queryClient = useQueryClient()

  const updateUpload = (index: number, updates: Partial<UploadedFile>) => {
    setUploads((prev) => prev.map((u, i) => (i === index ? { ...u, ...updates } : u)))
  }

  const onDrop = useCallback(
    async (accepted: File[]) => {
      const startIdx = uploads.length
      const newUploads: UploadedFile[] = accepted.map((f) => ({
        file: f,
        status: 'uploading',
        progress: 0,
      }))
      setUploads((prev) => [...prev, ...newUploads])

      for (let i = 0; i < accepted.length; i++) {
        const file = accepted[i]
        const idx = startIdx + i
        try {
          const doc = await documentsApi.upload(file)
          updateUpload(idx, { status: 'processing', document: doc, progress: 60 })
          toast.success(`${file.name} uploaded – extracting data...`)

          // Poll for completion
          pollStatus(doc.id, idx)
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : 'Upload failed'
          updateUpload(idx, { status: 'error', error: message, progress: 0 })
          toast.error(`Failed to upload ${file.name}`)
        }
      }
    },
    [uploads.length]
  )

  const pollStatus = async (docId: number, uploadIdx: number) => {
    const MAX_POLLS = 60
    let polls = 0
    const interval = setInterval(async () => {
      polls++
      try {
        const status = await documentsApi.getStatus(docId)
        const progress = Math.min(60 + polls * 2, 95)
        updateUpload(uploadIdx, { progress })

        if (status.status === 'processed') {
          clearInterval(interval)
          updateUpload(uploadIdx, { status: 'done', progress: 100 })
          queryClient.invalidateQueries({ queryKey: ['documents'] })
          queryClient.invalidateQueries({ queryKey: ['financial-summary'] })
          toast.success(`Extraction complete – ${status.financial_records} records found`)
        } else if (status.status === 'failed' || polls >= MAX_POLLS) {
          clearInterval(interval)
          updateUpload(uploadIdx, {
            status: 'error',
            error: status.errors?.[0] || 'Processing failed',
            progress: 0,
          })
        }
      } catch {
        clearInterval(interval)
      }
    }, 2000)
  }

  const removeUpload = (idx: number) => {
    setUploads((prev) => prev.filter((_, i) => i !== idx))
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 100 * 1024 * 1024,
  })

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-brand-500 bg-brand-50'
            : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-10 w-10 text-gray-400 mb-3" />
        <p className="text-sm font-medium text-gray-700">
          {isDragActive ? 'Drop files here' : 'Drag & drop files, or click to browse'}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          PDF, Excel (.xlsx/.xls), CSV, DOCX, PNG, JPG, TIFF — up to 100 MB each
        </p>
      </div>

      {/* Upload list */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((u, idx) => (
            <UploadItem key={idx} item={u} onRemove={() => removeUpload(idx)} />
          ))}
        </div>
      )}
    </div>
  )
}

function UploadItem({ item, onRemove }: { item: UploadedFile; onRemove: () => void }) {
  const icons = {
    uploading: <Loader2 className="h-4 w-4 text-brand-500 animate-spin" />,
    processing: <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />,
    done: <CheckCircle className="h-4 w-4 text-green-500" />,
    error: <AlertCircle className="h-4 w-4 text-red-500" />,
  }

  const statusText = {
    uploading: 'Uploading…',
    processing: 'Extracting data…',
    done: 'Ready',
    error: item.error || 'Error',
  }

  return (
    <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3">
      <File className="h-5 w-5 text-gray-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{item.file.name}</p>
        <div className="flex items-center gap-2 mt-1">
          {icons[item.status]}
          <span
            className={clsx('text-xs', {
              'text-brand-600': item.status === 'uploading',
              'text-yellow-600': item.status === 'processing',
              'text-green-600': item.status === 'done',
              'text-red-600': item.status === 'error',
            })}
          >
            {statusText[item.status]}
          </span>
        </div>
        {(item.status === 'uploading' || item.status === 'processing') && (
          <div className="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 rounded-full transition-all duration-300"
              style={{ width: `${item.progress}%` }}
            />
          </div>
        )}
      </div>
      {(item.status === 'done' || item.status === 'error') && (
        <button onClick={onRemove} className="text-gray-400 hover:text-gray-600">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

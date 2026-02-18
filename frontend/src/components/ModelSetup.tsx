import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { modelsApi } from '../services/api'
import { useAppStore } from '../store/appStore'

export function ModelSetup() {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    name: 'Base Model',
    description: '',
    forecast_start: 'FY2022',
    forecast_end: 'FY2028',
    forecast_frequency: 'annual',
    currency: 'USD',
    unit_scale: 'thousands',
  })
  const queryClient = useQueryClient()
  const { setActiveModel } = useAppStore()

  const mutation = useMutation({
    mutationFn: modelsApi.create,
    onSuccess: (model) => {
      queryClient.invalidateQueries({ queryKey: ['models'] })
      setActiveModel(model)
      toast.success(`Model "${model.name}" created`)
      setOpen(false)
    },
    onError: () => toast.error('Failed to create model'),
  })

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="btn-primary">
        <Plus className="h-4 w-4" />
        New Model
      </button>
    )
  }

  return (
    <div className="card border-brand-200 bg-brand-50">
      <div className="flex items-center gap-2 mb-4">
        <Settings className="h-4 w-4 text-brand-600" />
        <h3 className="text-sm font-semibold text-brand-900">Create Financial Model</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-700 mb-1">Model Name</label>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="input"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Forecast Start</label>
          <input
            value={form.forecast_start}
            onChange={(e) => setForm({ ...form, forecast_start: e.target.value })}
            placeholder="FY2022"
            className="input"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Forecast End</label>
          <input
            value={form.forecast_end}
            onChange={(e) => setForm({ ...form, forecast_end: e.target.value })}
            placeholder="FY2028"
            className="input"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Frequency</label>
          <select
            value={form.forecast_frequency}
            onChange={(e) => setForm({ ...form, forecast_frequency: e.target.value })}
            className="input"
          >
            <option value="annual">Annual</option>
            <option value="quarterly">Quarterly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Currency</label>
          <select
            value={form.currency}
            onChange={(e) => setForm({ ...form, currency: e.target.value })}
            className="input"
          >
            <option value="USD">USD ($)</option>
            <option value="GBP">GBP (£)</option>
            <option value="EUR">EUR (€)</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Unit Scale</label>
          <select
            value={form.unit_scale}
            onChange={(e) => setForm({ ...form, unit_scale: e.target.value })}
            className="input"
          >
            <option value="units">Units</option>
            <option value="thousands">Thousands</option>
            <option value="millions">Millions</option>
          </select>
        </div>
      </div>

      <div className="flex gap-2 mt-4">
        <button
          onClick={() => mutation.mutate(form)}
          disabled={!form.name.trim() || mutation.isPending}
          className="btn-primary flex-1"
        >
          {mutation.isPending ? 'Creating…' : 'Create Model'}
        </button>
        <button onClick={() => setOpen(false)} className="btn-secondary">
          Cancel
        </button>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { SchemaField } from '@/types'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { Badge } from '../ui/Badge'
import { Search, Eye, EyeOff, Lock, Edit2, Check, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface SchemaTableProps {
  fields: SchemaField[]
  columnVisibility: Record<string, boolean>
  onToggleColumnVisibility: (column: string) => void
  onUpdateField: (fieldId: string, updates: Partial<SchemaField>) => void
  searchQuery: string
  onSearchChange: (query: string) => void
}

export function SchemaTable({
  fields,
  columnVisibility,
  onToggleColumnVisibility,
  onUpdateField,
  searchQuery,
  onSearchChange,
}: SchemaTableProps) {
  const [editingFieldId, setEditingFieldId] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<Partial<SchemaField>>({})

  const startEdit = (field: SchemaField) => {
    setEditingFieldId(field.id)
    setEditValues({
      piiMaskingStrategy: field.piiMaskingStrategy,
      generatorType: field.generatorType,
      distribution: field.distribution,
    })
  }

  const saveEdit = (fieldId: string) => {
    onUpdateField(fieldId, {
      ...editValues,
      isConfigured: editValues.piiMaskingStrategy ? true : false,
      configurationStatus: editValues.piiMaskingStrategy ? 'complete' : 'blocked',
      blockReason: editValues.piiMaskingStrategy ? undefined : 'Missing PII masking strategy',
    })
    setEditingFieldId(null)
    setEditValues({})
  }

  const cancelEdit = () => {
    setEditingFieldId(null)
    setEditValues({})
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="p-4 border-b border-slate-200 bg-white space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search fields..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Column visibility toggle */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-slate-600 uppercase">Columns</span>
          {Object.entries(columnVisibility).map(([column, visible]) => (
            <button
              key={column}
              onClick={() => onToggleColumnVisibility(column)}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors',
                visible
                  ? 'bg-accent-100 text-accent-700'
                  : 'bg-slate-200 text-slate-600',
              )}
            >
              {visible ? (
                <Eye className="h-3.5 w-3.5" />
              ) : (
                <EyeOff className="h-3.5 w-3.5" />
              )}
              {column.replace(/([A-Z])/g, ' $1').trim()}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto bg-white">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-900 w-40">Field Name</th>
              {columnVisibility.dataType && (
                <th className="px-4 py-3 text-left font-semibold text-slate-900 w-24">Type</th>
              )}
              {columnVisibility.generatorType && (
                <th className="px-4 py-3 text-left font-semibold text-slate-900 w-32">Generator</th>
              )}
              {columnVisibility.piiLabel && (
                <th className="px-4 py-3 text-left font-semibold text-slate-900 w-24">PII</th>
              )}
              {columnVisibility.nullable && (
                <th className="px-4 py-3 text-left font-semibold text-slate-900 w-20">Null?</th>
              )}
              {columnVisibility.relationshipTarget && (
                <th className="px-4 py-3 text-left font-semibold text-slate-900 w-40">Relationship</th>
              )}
              <th className="px-4 py-3 text-left font-semibold text-slate-900 w-24">Status</th>
              <th className="px-4 py-3 text-center font-semibold text-slate-900 w-16">Action</th>
            </tr>
          </thead>
          <tbody>
            {fields.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                  No fields found
                </td>
              </tr>
            ) : (
              fields.map((field) => (
                <tr key={field.id} className={cn(
                  'border-b border-slate-100 hover:bg-slate-50 transition-colors',
                  editingFieldId === field.id && 'bg-accent-50',
                )}>
                  <td className="px-4 py-3 font-mono text-slate-900">{field.fieldName}</td>
                  {columnVisibility.dataType && (
                    <td className="px-4 py-3 text-slate-600">
                      <Badge variant="default">{field.dataType}</Badge>
                    </td>
                  )}
                  {columnVisibility.generatorType && (
                    <td className="px-4 py-3">
                      {editingFieldId === field.id ? (
                        <Select
                          options={[
                            { value: 'sequential', label: 'Sequential' },
                            { value: 'faker', label: 'Faker' },
                            { value: 'numeric', label: 'Numeric' },
                            { value: 'categorical', label: 'Categorical' },
                            { value: 'foreign_key', label: 'Foreign Key' },
                            { value: 'timestamp', label: 'Timestamp' },
                          ]}
                          value={editValues.generatorType || field.generatorType}
                          onChange={(e) => setEditValues({ ...editValues, generatorType: e.target.value })}
                          className="text-xs"
                        />
                      ) : (
                        <span className="text-slate-600 text-xs">{field.generatorType}</span>
                      )}
                    </td>
                  )}
                  {columnVisibility.piiLabel && (
                    <td className="px-4 py-3">
                      {field.piiLabel && field.piiLabel !== 'none' ? (
                        <Badge variant="warning">{field.piiLabel}</Badge>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  )}
                  {columnVisibility.nullable && (
                    <td className="px-4 py-3">
                      {field.nullable ? (
                        <Badge variant="info">nullable</Badge>
                      ) : (
                        <span className="text-xs text-slate-400">required</span>
                      )}
                    </td>
                  )}
                  {columnVisibility.relationshipTarget && (
                    <td className="px-4 py-3">
                      {field.relationshipTarget ? (
                        <span className="text-xs text-slate-600 font-mono">{field.relationshipTarget}</span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  )}
                  <td className="px-4 py-3">
                    {field.configurationStatus === 'blocked' ? (
                      <Badge variant="error">blocked</Badge>
                    ) : field.configurationStatus === 'partial' ? (
                      <Badge variant="warning">partial</Badge>
                    ) : (
                      <Badge variant="success">complete</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {editingFieldId === field.id ? (
                      <div className="flex justify-center gap-2">
                        <button
                          onClick={() => saveEdit(field.id)}
                          className="p-1 hover:bg-slate-200 rounded transition-colors"
                        >
                          <Check className="h-4 w-4 text-green-600" />
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="p-1 hover:bg-slate-200 rounded transition-colors"
                        >
                          <X className="h-4 w-4 text-red-600" />
                        </button>
                      </div>
                    ) : field.piiLabel && field.piiLabel !== 'none' ? (
                      <button
                        onClick={() => startEdit(field)}
                        className="p-1 hover:bg-slate-200 rounded transition-colors"
                        title={`Configure ${field.fieldName}`}
                      >
                        <Edit2 className="h-4 w-4 text-slate-600" />
                      </button>
                    ) : (
                      <Lock className="h-4 w-4 text-slate-300" />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer stats */}
      <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 text-xs text-slate-600 flex justify-between">
        <span>{fields.length} fields</span>
        <span>
          {fields.filter((f) => f.configurationStatus === 'complete').length} configured
        </span>
      </div>
    </div>
  )
}

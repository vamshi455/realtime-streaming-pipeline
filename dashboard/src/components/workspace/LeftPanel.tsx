import { Dataset } from '@/types'
import { Badge } from '../ui/Badge'
import { Database, Calendar, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'

interface LeftPanelProps {
  dataset: Dataset
  selectedTable: string
  onSelectTable: (tableName: string) => void
}

export function LeftPanel({ dataset, selectedTable, onSelectTable }: LeftPanelProps) {
  return (
    <div className="w-56 border-r border-slate-200 bg-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-900 mb-1">{dataset.name}</h3>
        <p className="text-xs text-slate-500 leading-relaxed">{dataset.description}</p>
      </div>

      {/* Metadata */}
      <div className="px-4 py-3 border-b border-slate-200 text-xs space-y-2">
        <div className="flex items-center gap-2 text-slate-600">
          <Database className="h-4 w-4" />
          <span>{dataset.source}</span>
        </div>
        <div className="flex items-center gap-2 text-slate-600">
          <Calendar className="h-4 w-4" />
          <span>{new Date(dataset.modified).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Tables section */}
      <div className="flex-1 overflow-auto">
        <div className="p-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">Tables</div>
        <div className="space-y-1 px-2">
          {dataset.tables.map((table) => (
            <button
              key={table.name}
              onClick={() => onSelectTable(table.name)}
              className={cn(
                'w-full text-left px-3 py-2 rounded text-sm transition-colors',
                selectedTable === table.name
                  ? 'bg-accent-50 text-accent-700 font-medium'
                  : 'text-slate-600 hover:bg-slate-50',
              )}
            >
              <div className="font-medium">{table.displayName}</div>
              <div className="text-xs text-slate-500 mt-0.5">{table.fields.length} fields</div>
            </button>
          ))}
        </div>
      </div>

      {/* Status footer */}
      <div className="p-3 border-t border-slate-200 text-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-slate-600">Configuration</span>
          <Badge variant="success">{dataset.configurationComplete}%</Badge>
        </div>
        {dataset.privacyIssues.length > 0 && (
          <div className="flex items-start gap-2 text-red-700 bg-red-50 p-2 rounded">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span>{dataset.privacyIssues.length} issues</span>
          </div>
        )}
      </div>
    </div>
  )
}

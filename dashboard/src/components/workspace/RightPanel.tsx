import { Dataset } from '@/types'
import { Badge } from '../ui/Badge'
import { AlertCircle, Check, Clock, Zap } from 'lucide-react'
import { cn } from '@/utils/cn'

interface RightPanelProps {
  dataset: Dataset
  blockingIssuesCount: number
}

export function RightPanel({ dataset, blockingIssuesCount }: RightPanelProps) {
  const canGenerate = blockingIssuesCount === 0

  return (
    <div className="w-72 border-l border-slate-200 bg-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-900">Generation Config</h3>
      </div>

      {/* Configuration items */}
      <div className="flex-1 overflow-auto space-y-4 p-4">
        {/* Target rows */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-600 uppercase">Target Rows</span>
            <span className="text-sm font-mono text-slate-900">{dataset.targetRows.toLocaleString()}</span>
          </div>
          <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div className="h-full bg-accent-600 w-full" />
          </div>
        </div>

        {/* Seed */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-600 uppercase">Deterministic Seed</label>
          <div className="flex items-center gap-2 px-3 py-2 rounded border border-slate-300 bg-slate-50 font-mono text-sm text-slate-900">
            <Zap className="h-4 w-4 text-amber-500" />
            {dataset.seed}
          </div>
          <p className="text-xs text-slate-500">Same seed = reproducible results</p>
        </div>

        {/* Runtime */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-600 uppercase">Estimated Runtime</span>
            <Badge variant="info">{dataset.estimatedRuntime} min</Badge>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <Clock className="h-4 w-4" />
            <span>~{Math.ceil(dataset.targetRows / 1000000 * 60)} minutes at 1M rows/min</span>
          </div>
        </div>

        {/* Configuration progress */}
        <div className="space-y-3 pt-2 border-t border-slate-200">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600 uppercase">Configuration Status</span>
              <Badge variant="warning">{dataset.configurationComplete}%</Badge>
            </div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent-600 transition-all"
                style={{ width: `${dataset.configurationComplete}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-slate-500">
            {dataset.configurationComplete === 100
              ? '✓ All fields configured'
              : `${100 - dataset.configurationComplete}% incomplete`}
          </p>
        </div>

        {/* Issues summary */}
        {blockingIssuesCount > 0 && (
          <div className={cn(
            'p-3 rounded-lg border-2 space-y-2',
            canGenerate
              ? 'border-amber-200 bg-amber-50'
              : 'border-red-200 bg-red-50',
          )}>
            <div className="flex items-start gap-2">
              <AlertCircle className={cn(
                'h-5 w-5 flex-shrink-0 mt-0.5',
                canGenerate ? 'text-amber-600' : 'text-red-600',
              )} />
              <div>
                <p className={cn(
                  'text-sm font-semibold',
                  canGenerate ? 'text-amber-900' : 'text-red-900',
                )}>
                  {blockingIssuesCount} {blockingIssuesCount === 1 ? 'issue' : 'issues'} blocking generation
                </p>
                <p className={cn(
                  'text-xs mt-1',
                  canGenerate ? 'text-amber-700' : 'text-red-700',
                )}>
                  PII fields require masking strategy. Update in Schema tab.
                </p>
              </div>
            </div>
          </div>
        )}

        {canGenerate && (
          <div className="p-3 rounded-lg border-2 border-green-200 bg-green-50 flex items-start gap-2">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-green-900">Ready to generate</p>
              <p className="text-xs text-green-700 mt-1">All configuration requirements met</p>
            </div>
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div className="p-4 border-t border-slate-200 bg-slate-50 text-xs text-slate-600">
        <p>Click "Run generation" in the top bar to start the job.</p>
      </div>
    </div>
  )
}

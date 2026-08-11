import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ChevronRight, Play } from 'lucide-react'
import { Dataset } from '@/types'

interface TopBarProps {
  dataset: Dataset
  blockingIssuesCount: number
  isGenerating: boolean
  onGenerate: () => void
}

export function TopBar({ dataset, blockingIssuesCount, isGenerating, onGenerate }: TopBarProps) {
  const canGenerate = blockingIssuesCount === 0

  return (
    <div className="h-14 border-b border-slate-200 bg-white px-6 flex items-center justify-between">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-600">Workspace</span>
        <ChevronRight className="h-4 w-4 text-slate-400" />
        <span className="text-slate-900 font-medium">{dataset.name}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Environment badge */}
        <Badge variant="info">development</Badge>

        {/* Generate button */}
        <Button
          variant="primary"
          size="md"
          onClick={onGenerate}
          disabled={!canGenerate || isGenerating}
          isLoading={isGenerating}
          className="gap-2"
        >
          <Play className="h-4 w-4" />
          Run generation
        </Button>
      </div>
    </div>
  )
}

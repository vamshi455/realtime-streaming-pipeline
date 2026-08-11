import { PrivacyIssue } from '@/types'
import { AlertCircle, ArrowRight } from 'lucide-react'
import { Button } from '../ui/Button'

interface PrivacyWarningProps {
  issues: PrivacyIssue[]
  onResolveClick: (fieldId: string) => void
}

export function PrivacyWarning({ issues, onResolveClick }: PrivacyWarningProps) {
  if (issues.length === 0) return null

  const criticalIssues = issues.filter((i) => i.severity === 'error')

  return (
    <div className="p-4 bg-red-50 border-l-4 border-red-500 space-y-3">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-red-900">
            {criticalIssues.length} {criticalIssues.length === 1 ? 'issue' : 'issues'} blocking generation
          </h3>
          <p className="text-sm text-red-700 mt-1">
            PII fields must have a masking strategy configured before data can be generated.
          </p>
        </div>
      </div>

      {/* Issues list */}
      <div className="space-y-2 ml-8">
        {criticalIssues.map((issue) => (
          <div key={issue.id} className="text-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-red-900">{issue.fieldName}</p>
                <p className="text-red-700 text-xs mt-1">{issue.remediation}</p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onResolveClick(issue.fieldId)}
                className="flex-shrink-0 gap-1.5"
              >
                Configure <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

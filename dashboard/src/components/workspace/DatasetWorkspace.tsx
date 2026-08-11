import { useState } from 'react'
import { useDataset } from '@/hooks/useDataset'
import { TopBar } from './TopBar'
import { LeftPanel } from './LeftPanel'
import { RightPanel } from './RightPanel'
import { SchemaTable } from './SchemaTable'
import { PrivacyWarning } from './PrivacyWarning'

export function DatasetWorkspace() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationError, setGenerationError] = useState<string | null>(null)
  const {
    dataset,
    selectedTable,
    setSelectedTable,
    searchQuery,
    setSearchQuery,
    columnVisibility,
    setColumnVisibility,
    currentTable,
    filteredFields,
    updateField,
    blockingIssuesCount,
    isLoading,
    apiError,
    emitBatch,
  } = useDataset()

  const handleGenerate = async () => {
    setIsGenerating(true)
    setGenerationError(null)
    try {
      await emitBatch('customer')
      console.log('Generation completed successfully')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Generation failed'
      setGenerationError(message)
      console.error('Generation error:', message)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleResolveIssue = (fieldId: string) => {
    console.log('Scroll to field:', fieldId)
  }

  const toggleColumnVisibility = (column: string) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [column]: !prev[column],
    }))
  }

  if (isLoading) {
    return (
      <div className="flex flex-col h-screen bg-slate-50 items-center justify-center">
        <div className="space-y-4">
          <svg className="animate-spin h-10 w-10 mx-auto text-accent-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-slate-600 text-center">Loading dataset...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top bar */}
      <TopBar
        dataset={dataset}
        blockingIssuesCount={blockingIssuesCount}
        isGenerating={isGenerating}
        onGenerate={handleGenerate}
      />

      {/* Error notification */}
      {(apiError || generationError) && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="text-red-600 text-lg">⚠️</div>
            <div>
              <h3 className="font-semibold text-red-900">
                {generationError ? 'Generation Error' : 'API Connection Warning'}
              </h3>
              <p className="text-sm text-red-700 mt-1">
                {generationError || apiError}
              </p>
              {apiError && <p className="text-xs text-red-600 mt-2">Using mock data. Connect to Producer at http://localhost:8000</p>}
            </div>
          </div>
          <button
            onClick={() => {
              setGenerationError(null)
            }}
            className="text-red-600 hover:text-red-700 text-lg"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel */}
        <LeftPanel
          dataset={dataset}
          selectedTable={selectedTable}
          onSelectTable={setSelectedTable}
        />

        {/* Center panel */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          {/* Privacy warning */}
          {blockingIssuesCount > 0 && (
            <PrivacyWarning
              issues={dataset.privacyIssues}
              onResolveClick={handleResolveIssue}
            />
          )}

          {/* Schema table */}
          {currentTable && (
            <SchemaTable
              fields={filteredFields}
              columnVisibility={columnVisibility}
              onToggleColumnVisibility={toggleColumnVisibility}
              onUpdateField={updateField}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          )}

          {!currentTable && (
            <div className="flex-1 flex items-center justify-center text-slate-500">
              <p>Select a table to view its schema</p>
            </div>
          )}
        </div>

        {/* Right panel */}
        <RightPanel
          dataset={dataset}
          blockingIssuesCount={blockingIssuesCount}
        />
      </div>
    </div>
  )
}

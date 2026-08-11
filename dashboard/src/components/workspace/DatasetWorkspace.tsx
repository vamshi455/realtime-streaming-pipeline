import { useState } from 'react'
import { useDataset } from '@/hooks/useDataset'
import { TopBar } from './TopBar'
import { LeftPanel } from './LeftPanel'
import { RightPanel } from './RightPanel'
import { SchemaTable } from './SchemaTable'
import { PrivacyWarning } from './PrivacyWarning'

export function DatasetWorkspace() {
  const [isGenerating, setIsGenerating] = useState(false)
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
  } = useDataset()

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      console.log('Generation started', {
        dataset: dataset.id,
        targetRows: dataset.targetRows,
        seed: dataset.seed,
      })
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

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top bar */}
      <TopBar
        dataset={dataset}
        blockingIssuesCount={blockingIssuesCount}
        isGenerating={isGenerating}
        onGenerate={handleGenerate}
      />

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

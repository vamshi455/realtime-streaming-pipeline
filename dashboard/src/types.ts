export interface SchemaField {
  id: string
  fieldName: string
  dataType: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'timestamp'
  nullable: boolean
  generatorType: string
  distribution?: string
  piiLabel?: 'email' | 'phone' | 'ssn' | 'dob' | 'address' | 'credit_card' | 'none'
  piiMaskingStrategy?: 'hash' | 'redact' | 'encrypt' | 'generalize' | 'synthetic'
  relationshipTarget?: string
  isConfigured: boolean
  configurationStatus: 'complete' | 'partial' | 'blocked'
  blockReason?: string
}

export interface Table {
  name: string
  displayName: string
  description: string
  fields: SchemaField[]
  rowCount: number
  isSelected: boolean
}

export interface Dataset {
  id: string
  name: string
  description: string
  source: string
  created: string
  modified: string
  tables: Table[]
  seed: number
  targetRows: number
  estimatedRuntime: number
  configurationComplete: number
  privacyIssues: PrivacyIssue[]
  status: 'ready' | 'generating' | 'completed' | 'failed'
}

export interface PrivacyIssue {
  id: string
  fieldName: string
  tableName: string
  severity: 'info' | 'warning' | 'error'
  message: string
  remediation: string
  fieldId: string
}

export interface GenerationConfig {
  targetRows: number
  seed: number
  preserveNulls: boolean
  deterministicId: boolean
  maxRuntime: number
}

export interface ColumnVisibility {
  [key: string]: boolean
}

export interface PreviewRow {
  [key: string]: any
}

export type ViewMode = 'schema' | 'preview' | 'quality' | 'privacy' | 'lineage'

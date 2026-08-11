# Synthetic Data Studio

A production-grade React + TypeScript UI for configuring and generating privacy-safe synthetic data at scale.

## Overview

Synthetic Data Studio is a data-engineering workspace where technical users can:
1. **Define schemas**: Multi-table relational datasets with field-level PII classification
2. **Configure generation**: Deterministic seeding, nullability, generator rules, and relationships
3. **Validate privacy**: Masking strategies for PII fields block generation until configured
4. **Monitor generation**: Real-time progress, estimated runtime, and configuration completeness
5. **Export results**: Generated datasets partitioned and optimized for downstream use

## Architecture

### Stack

- **React 18** + **TypeScript** for type-safe UI
- **Vite** for fast builds and HMR
- **Tailwind CSS** for utility-first styling
- **TanStack Table** for dense, high-volume data grids
- **TanStack Query** for server state management
- **React Hook Form** + **Zod** for validation
- **Lucide React** for icons

### Design Principles

- **Enterprise aesthetic**: Calm, neutral palette with minimal visual noise
- **Data-first layout**: Dense information hierarchy, tabular figures, monospaced IDs
- **Accessibility**: Semantic HTML, keyboard navigation, visible focus states
- **No magic**: Explicit configuration, clear error messaging, reproducible results

## Features

### Dataset Workspace

Three-panel desktop layout:
- **Left**: Dataset metadata, table selector, configuration progress, privacy issues summary
- **Center**: Schema editor with dense, searchable table; column visibility controls; inline PII masking configuration
- **Right**: Generation config summary, deterministic seed, estimated runtime, blocking issue checklist, ready/blocked state

### Schema Editor

Dense editable table with columns:
- **Field Name** (monospaced)
- **Data Type** (tagged: string, integer, float, boolean, date, timestamp)
- **Generator Type** (sequential, faker, numeric, categorical, foreign_key, timestamp)
- **Distribution** (configurable constraints, ranges, rules)
- **PII Label** (tagged: email, phone, ssn, dob, address, credit_card, none)
- **Nullable** (boolean, tagged)
- **Relationship Target** (foreign keys, monospaced)
- **Status** (complete, partial, blocked)
- **Action** (edit/save for PII fields, read-only for others)

### Privacy Management

- Scans all fields for PII labels
- Blocks generation if any PII field lacks a masking strategy
- Shows warning panel with blocking fields and remediation guidance
- Inline editing of masking strategies (hash, redact, encrypt, generalize, synthetic)
- Real-time configuration status

### Generation Config

Summary panel shows:
- Target row count (formatted with thousand separators)
- Deterministic seed (with copy-to-clipboard)
- Estimated runtime (calculated from row count)
- Configuration progress bar (0–100%)
- Blocking issues count and details
- "Run generation" button (disabled if blocking issues exist)

### Multiple Data Domains

Sample data supports:
- **Power Trading**: LMP ticks, deals, nominations (delivery nodes, volumes, statuses)
- **E-commerce**: Customers, orders, order items (relationships, derived fields)
- **IoT**: Sensor readings (temperature, humidity, pressure)
- **Finance**: Price ticks (bid/ask, volume, symbols)

## Usage

### Development

```bash
npm install
npm run dev
# App runs at http://localhost:5173
```

### Build

```bash
npm run build
npm run preview
```

### Docker

```bash
docker build -t synthetic-data-studio .
docker run -p 5173:5173 synthetic-data-studio
```

## Component Structure

```
src/
├── App.tsx                           # Main app
├── main.tsx                          # Entry point
├── index.css                         # Global styles
├── types.ts                          # TypeScript interfaces
├── components/
│   ├── ui/                           # Primitive components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Badge.tsx
│   └── workspace/                    # Workspace components
│       ├── TopBar.tsx                # Breadcrumb + environment + generate button
│       ├── LeftPanel.tsx             # Dataset metadata + table selector
│       ├── RightPanel.tsx            # Generation config summary
│       ├── SchemaTable.tsx           # Dense schema editor grid
│       ├── PrivacyWarning.tsx        # PII issue panel
│       └── DatasetWorkspace.tsx      # Main layout orchestrator
├── hooks/
│   └── useDataset.ts                 # Dataset state + mock data
└── utils/
    └── cn.ts                         # Tailwind class merger
```

## Styling

### Tokens

- **Palette**: Slate (neutral), Indigo/Accent (primary), Amber (warning), Green (success), Red (error)
- **Typography**: System font stack, tabular figures in tables and metrics
- **Spacing**: 8px grid (gutter)
- **No gradients, shadows, rounded corners, or glassmorphism**

### Tailwind Config

Custom extensions:
- Accent color set (50–700)
- Tabular figures for `<table>` elements
- Extended type scale (xs–2xl)

## Data Model

### Dataset

```typescript
interface Dataset {
  id: string
  name: string
  description: string
  source: string
  created: string
  modified: string
  tables: Table[]
  seed: number                    // Deterministic seed
  targetRows: number              // 1,000,000
  estimatedRuntime: number        // Minutes
  configurationComplete: number   // 0–100%
  privacyIssues: PrivacyIssue[]  // Blocking issues
  status: 'ready' | 'generating' | 'completed' | 'failed'
}
```

### Table

```typescript
interface Table {
  name: string
  displayName: string
  description: string
  fields: SchemaField[]
  rowCount: number
  isSelected: boolean
}
```

### SchemaField

```typescript
interface SchemaField {
  id: string
  fieldName: string
  dataType: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'timestamp'
  nullable: boolean
  generatorType: string              // 'faker', 'sequential', etc.
  distribution?: string              // 'normal', 'uniform', ranges, etc.
  piiLabel?: 'email' | 'phone' | ... // PII classification
  piiMaskingStrategy?: string        // 'hash', 'encrypt', etc.
  relationshipTarget?: string        // Foreign key reference
  isConfigured: boolean
  configurationStatus: 'complete' | 'partial' | 'blocked'
  blockReason?: string
}
```

### PrivacyIssue

```typescript
interface PrivacyIssue {
  id: string
  fieldName: string
  tableName: string
  severity: 'info' | 'warning' | 'error'
  message: string
  remediation: string
  fieldId: string                    // Link to SchemaField.id
}
```

## Integration

### API Endpoints

Connects to Producer API:

```
POST /emit/batch
{
  event_type: string
  count: number
  events: Array<{...}>
  frequency?: string
  constraints?: Record<string, any>
}
```

### Mock Data

Currently uses mock dataset (`useDataset` hook). Replace with API calls using React Query:

```typescript
const { data: dataset } = useQuery({
  queryKey: ['dataset', datasetId],
  queryFn: () => fetch(`/api/datasets/${datasetId}`).then(r => r.json()),
})
```

## States

### Loading
Shows spinner in "Run generation" button while generating

### Empty
"Select a table to view its schema" when no table selected

### Blocked
- "Run generation" button disabled
- Privacy warning panel visible
- Right panel shows red "Issues blocking generation"

### Ready
- "Run generation" button enabled
- Right panel shows green "Ready to generate"
- All fields configured

### Generating
- "Run generation" button shows spinner and is disabled
- Can cancel (future feature)

### Completed
- Status badge shows "Completed"
- Row count and stats visible
- Export/download options (future feature)

## Best Practices

1. **Dense, not cramped**: Use the 8px grid; 16px minimum tap targets
2. **Monospaced IDs**: Field names, foreign keys, seed values all monospaced
3. **Semantic color**: Green for valid/complete, red for blocking errors, amber for warnings
4. **Tabular numbers**: All metrics, counts, and numeric IDs use `font-variant-numeric: tabular-nums`
5. **Type safety**: All props typed, no `any`
6. **Focus visible**: All interactive elements have `:focus-ring` state

## Future Features

- [ ] Schedule recurring generation (APScheduler)
- [ ] Preview sample data (5–10 rows)
- [ ] Quality metrics (statistical similarity, constraint violations)
- [ ] Data lineage and audit trail
- [ ] Export to Parquet, CSV, Delta Lake
- [ ] Multi-workspace support
- [ ] Team collaboration (comments, approvals)
- [ ] Performance profiling (rows/sec, memory usage)

## Testing

```bash
npm run build    # TypeScript check
npm run lint     # ESLint check
npm run dev      # Manual testing
```

## License

Proprietary. Part of the realtime-streaming-pipeline project.

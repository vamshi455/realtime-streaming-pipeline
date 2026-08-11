# Synthetic Data Studio - React Implementation Guide

## Overview

The dashboard has been upgraded from Streamlit to a production-grade React + TypeScript application. The new implementation provides a superior user experience with enterprise-grade UI patterns, type safety, and performance.

## Key Improvements Over Streamlit

| Aspect | Streamlit | React |
|--------|-----------|-------|
| **Type Safety** | None | Full TypeScript |
| **Performance** | Slower, page reloads | Fast SPA with HMR |
| **UX Pattern** | Generic AI chat | Data-engineering workspace |
| **Dense UIs** | Difficult | Native support (TanStack Table) |
| **Styling** | Limited Markdown | Tailwind + custom components |
| **Accessibility** | Basic | Semantic HTML, ARIA, focus management |
| **Responsiveness** | Mobile-first | Desktop-first (designed for 1440p+) |
| **State Management** | App-level | React Query + local state |

## Architecture

### Three-Panel Desktop Workspace

```
┌─────────────────────────────────────────────────────────────┐
│                         TOP BAR                              │
│  Workspace / Dataset Name  [dev] [Run generation] [Menu]    │
├──────────────┬────────────────────────────────┬──────────────┤
│              │                                │              │
│   LEFT PANEL │      CENTER PANEL             │  RIGHT PANEL │
│              │                                │              │
│  Metadata    │ Schema Table                  │  Gen Config  │
│  Tables      │ - Field Name (monospaced)     │              │
│  Progress    │ - Type                        │ • 1M rows    │
│  Issues      │ - Generator                   │ • Seed: 42   │
│              │ - PII Label                   │ • 4 min      │
│              │ - Status / Edit               │ • 92% done   │
│              │                                │              │
│              │ Privacy Warning Panel         │ • 2 issues   │
│              │ (if blocking issues exist)    │   (red)      │
│              │                                │              │
└──────────────┴────────────────────────────────┴──────────────┘
```

### Component Hierarchy

```
App
└── DatasetWorkspace
    ├── TopBar
    │   └── Generate button (disabled if issues)
    ├── LeftPanel
    │   ├── Dataset metadata
    │   ├── Table selector
    │   └── Status footer
    ├── Center (flex column)
    │   ├── PrivacyWarning (conditional)
    │   └── SchemaTable
    │       ├── Search + filters
    │       ├── Column visibility toggle
    │       └── Dense data grid
    └── RightPanel
        ├── Target rows progress
        ├── Seed display
        ├── Runtime estimate
        ├── Configuration progress
        └── Issue checklist OR Ready badge
```

## Development

### Setup

```bash
cd dashboard
npm install
npm run dev
# App runs at http://localhost:5173
```

### Building

```bash
npm run build      # TypeScript check + Vite build
npm run preview    # Preview production build locally
npm run lint       # ESLint check
```

### File Structure

```
dashboard/
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Root component
│   ├── index.css                   # Global Tailwind + custom CSS
│   ├── types.ts                    # TypeScript interfaces
│   ├── components/
│   │   ├── ui/                     # Primitive UI components
│   │   │   ├── Button.tsx          # Primary, secondary, ghost, danger
│   │   │   ├── Input.tsx           # Text input
│   │   │   ├── Select.tsx          # Dropdown
│   │   │   └── Badge.tsx           # Labeled tags
│   │   └── workspace/              # Feature components
│   │       ├── TopBar.tsx          # Breadcrumb + buttons
│   │       ├── LeftPanel.tsx       # Dataset + table selector
│   │       ├── RightPanel.tsx      # Generation summary
│   │       ├── SchemaTable.tsx     # Dense field editor
│   │       ├── PrivacyWarning.tsx  # PII issue panel
│   │       └── DatasetWorkspace.tsx # Layout orchestrator
│   ├── hooks/
│   │   └── useDataset.ts           # State + mock data
│   └── utils/
│       └── cn.ts                   # Tailwind class merger
├── index.html                      # HTML entry point
├── package.json
├── tsconfig.json                   # TypeScript config
├── vite.config.ts                  # Vite config
├── tailwind.config.js              # Tailwind tokens
├── postcss.config.js               # PostCSS plugins
├── .eslintrc.cjs                   # ESLint rules
├── Dockerfile                      # Production image
└── README.md                        # Feature documentation
```

## UI Components

### Primitives

All primitives in `src/components/ui/` follow shadcn/ui patterns:

- **Button**: `variant` (primary | secondary | ghost | danger), `size` (sm | md | lg), `isLoading`
- **Input**: Standard HTML input with Tailwind styling
- **Select**: Dropdown with options array
- **Badge**: `variant` (default | success | warning | error | info)

### Feature Components

- **TopBar**: Breadcrumb, environment badge, generate button
- **LeftPanel**: Dataset metadata, table selector, status footer
- **RightPanel**: Generation config summary with checklist
- **SchemaTable**: Dense editable grid with search, filters, column visibility
- **PrivacyWarning**: Error panel for blocking PII issues

## State Management

### useDataset Hook

```typescript
const {
  dataset,                   // Dataset object with tables and config
  selectedTable,             // Currently selected table name
  setSelectedTable,          // Switch table
  searchQuery,               // Search filter in schema table
  setSearchQuery,            // Update search
  columnVisibility,          // Which columns are shown
  setColumnVisibility,       // Toggle columns
  currentTable,              // Selected table object
  filteredFields,            // Searched + filtered fields
  updateField,               // Edit field (PII masking, etc)
  updateDatasetConfig,       // Edit dataset (seed, rows, etc)
  blockingIssuesCount,       // Privacy issues blocking generation
} = useDataset()
```

### Mock Data

Currently uses hardcoded mock dataset with:
- 3 tables (Customers, Orders, OrderItems)
- 15 fields total
- 2 PII issues (email, date_of_birth missing masking)
- 1M target rows, seed=42, estimated 4-minute runtime

Replace with API calls using React Query:

```typescript
import { useQuery } from '@tanstack/react-query'

const { data: dataset } = useQuery({
  queryKey: ['dataset', datasetId],
  queryFn: () => fetch(`http://localhost:8000/api/datasets/${datasetId}`).then(r => r.json()),
})
```

## Styling

### Design System

- **Palette**: Slate (neutral) + Accent (indigo/blue)
- **Typography**: System font stack, monospaced for IDs/fields
- **Spacing**: 8px grid (gutter)
- **No gradients, shadows, or glassmorphism**

### Tailwind Configuration

Custom tokens in `tailwind.config.js`:

```javascript
colors: {
  accent: { 50, 100, 400, 500, 600, 700 }
}
fontFamily: {
  mono: 'Fira Code, monospace'
}
fontSize: {
  xs, sm, base, lg, xl, 2xl  // Type scale
}
```

### CSS Custom Properties (Optional)

For dynamic theming later:

```css
:root {
  --color-accent-600: rgb(79 70 229);
  --color-slate-900: rgb(15 23 42);
}
```

## API Integration

### Producer API Endpoints

The app sends batch generation requests to the Producer (FastAPI):

```typescript
// In DatasetWorkspace.tsx
const handleGenerate = async () => {
  const response = await fetch('http://localhost:8000/emit/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_type: 'customer',      // or 'order', 'order_item'
      count: dataset.targetRows,
      events: generateEventsFromSchema(dataset),
      frequency: 'once',
      constraints: {
        seed: dataset.seed,
        preserveNulls: true,
      },
    }),
  })
  const result = await response.json()
  console.log('Generation started:', result)
}
```

### Example: Fetch Dataset from API

Replace `useDataset` hook with:

```typescript
import { useQuery } from '@tanstack/react-query'

export function useDatasetFromAPI(datasetId: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: async () => {
      const res = await fetch(`http://localhost:8000/api/datasets/${datasetId}`)
      if (!res.ok) throw new Error('Failed to fetch dataset')
      return res.json()
    },
  })

  return { dataset: data, isLoading, error }
}
```

## Type System

### Core Types (types.ts)

```typescript
interface Dataset {
  id, name, description, source
  created, modified
  tables: Table[]
  seed: number
  targetRows: number
  estimatedRuntime: number
  configurationComplete: number    // 0-100%
  privacyIssues: PrivacyIssue[]
  status: 'ready' | 'generating' | 'completed' | 'failed'
}

interface SchemaField {
  id, fieldName
  dataType: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'timestamp'
  nullable: boolean
  generatorType: string             // 'faker', 'sequential', 'numeric', etc.
  distribution?: string             // 'normal', 'uniform', ranges
  piiLabel?: 'email' | 'phone' | 'ssn' | 'dob' | ...
  piiMaskingStrategy?: 'hash' | 'encrypt' | 'generalize' | 'synthetic'
  relationshipTarget?: string       // FK reference: 'orders.customer_id'
  isConfigured: boolean
  configurationStatus: 'complete' | 'partial' | 'blocked'
}

interface PrivacyIssue {
  id, fieldName, tableName
  severity: 'info' | 'warning' | 'error'
  message, remediation
  fieldId: string                   // Link to SchemaField.id
}
```

## States & Interactions

### Generation Ready State
- All PII fields have masking strategies
- "Run generation" button **enabled**, primary blue
- Right panel shows green checkmark "Ready to generate"

### Blocked State (PII Issues)
- One or more PII fields missing masking strategy
- "Run generation" button **disabled**, gray
- Privacy warning panel **visible** at top of center
- Right panel shows red **2 issues blocking generation**
- User clicks "Configure" button → scrolls to field in table

### Generating State
- "Run generation" button shows spinner, **disabled**
- Right panel shows progress bar (if real-time updates implemented)
- Can cancel (not yet implemented)

### Completed State
- Status badge: "Completed" (green)
- Row count and stats displayed
- Export/download options (future feature)

## Keyboard & Accessibility

- Tab navigation through all controls
- Focus ring on all interactive elements (blue ring, 2px offset)
- Enter to activate buttons
- Escape to cancel inline editing
- Screen reader support via semantic HTML + `aria-label` where needed

## Performance

### Optimizations

1. **Virtual scrolling**: Dense schema table with 100+ fields
   - Use `react-window` if field count exceeds viewport
   - Currently TanStack Table handles small datasets

2. **Memoization**: Schema table cells are memoized to prevent re-renders on parent updates
   - Use `React.memo()` for table rows if needed

3. **Lazy loading**: 
   - Dataset metadata loads first
   - Schema fields load on table select
   - Preview data loads on demand (future)

4. **Code splitting**:
   - Vite automatically splits chunks for lazy routes (future)
   - Current SPA is small enough for single chunk (~68KB gzipped)

## Testing

### Manual Testing Checklist

- [ ] Load dataset and verify 3 tables display
- [ ] Select each table and verify fields load
- [ ] Search for "customer_id" and verify results filter
- [ ] Toggle column visibility and verify columns hide/show
- [ ] Click edit on email field and change masking strategy
- [ ] Verify configuration status updates to "complete"
- [ ] Verify privacy warning disappears when all PII configured
- [ ] Verify "Run generation" button enables
- [ ] Click "Run generation" and verify POST request sent to Producer

### Unit Testing (Future)

```typescript
// Using Vitest + React Testing Library
import { render, screen } from '@testing-library/react'
import { DatasetWorkspace } from './components/workspace/DatasetWorkspace'

test('disables generate button when PII issues exist', () => {
  render(<DatasetWorkspace />)
  const btn = screen.getByText('Run generation')
  expect(btn).toBeDisabled()
})
```

## Docker

### Build

```bash
docker build -t synthetic-data-studio .
```

### Run

```bash
docker run -p 5173:5173 synthetic-data-studio
# App at http://localhost:5173
```

### In docker-compose.yml

```yaml
generator:
  build:
    context: ./dashboard
    dockerfile: Dockerfile
  container_name: generator
  ports:
    - "5173:5173"
  depends_on:
    - producer
  networks:
    - streaming
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5173/"]
    interval: 10s
    timeout: 5s
    retries: 3
```

## Troubleshooting

### Blank page on http://localhost:5173

1. Check browser console for errors
2. Verify React DevTools extension isn't blocking
3. Clear browser cache: Cmd+Shift+R
4. Rebuild: `npm run build`

### "Cannot find module '@'" errors

Verify `vite.config.ts` has correct alias:
```typescript
alias: {
  '@': path.resolve(__dirname, './src'),
}
```

### Slow hot reload

The development server uses HMR. If slow:
1. Close other dev servers (ports 3000, 5173, 8000, etc.)
2. Increase Node heap: `NODE_OPTIONS=--max_old_space_size=4096 npm run dev`

### Docker build fails

1. Clear node_modules: `rm -rf node_modules`
2. Rebuild: `docker build --no-cache -t synthetic-data-studio .`

## Future Features

- [ ] **Multi-table relationships**: Visual ER diagram with drag-to-connect
- [ ] **Constraint validation**: Uniqueness, foreign key, check constraints
- [ ] **Preview data**: Sample 5–10 generated rows before emission
- [ ] **Quality metrics**: Statistical similarity, referential integrity checks
- [ ] **Data lineage**: Audit trail of transformations and exports
- [ ] **Scheduling**: Recurring generation jobs (APScheduler backend)
- [ ] **Export formats**: Parquet, CSV, Delta Lake, Avro
- [ ] **Collaboration**: Comments on fields, approval workflows
- [ ] **Performance profiling**: Rows/sec, memory usage during generation
- [ ] **Multi-workspace**: Save/load dataset configurations

## Resources

- [React 18 Docs](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com)
- [TanStack Table](https://tanstack.com/table/)
- [Lucide Icons](https://lucide.dev)
- [Vite Guide](https://vitejs.dev)

## Support

For issues or questions:
1. Check this guide and component README.md
2. Review TypeScript errors: `npm run build`
3. Search component code for similar patterns
4. Open an issue on GitHub

---

**Last Updated**: 2024-08-10  
**Maintainer**: Synthetic Data Studio Team

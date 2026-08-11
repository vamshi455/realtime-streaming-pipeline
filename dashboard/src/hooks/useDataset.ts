import { useState } from 'react'
import { Dataset, SchemaField } from '@/types'

const MOCK_DATASET: Dataset = {
  id: 'ds-001',
  name: 'E-commerce Customer Orders',
  description: 'Relational dataset with customer, order, and order item tables for synthetic data generation.',
  source: 'PostgreSQL - production_db',
  created: '2024-08-10T10:30:00Z',
  modified: '2024-08-10T18:45:00Z',
  seed: 42,
  targetRows: 1000000,
  estimatedRuntime: 240,
  configurationComplete: 92,
  status: 'ready',
  privacyIssues: [
    {
      id: 'pi-001',
      fieldName: 'email',
      tableName: 'Customers',
      severity: 'error',
      message: 'PII field requires masking strategy',
      remediation: 'Add PII masking strategy: hash, encrypt, or synthetic',
      fieldId: 'customers-email',
    },
    {
      id: 'pi-002',
      fieldName: 'date_of_birth',
      tableName: 'Customers',
      severity: 'error',
      message: 'PII field requires masking strategy',
      remediation: 'Add PII masking strategy: generalize to age brackets or encrypt',
      fieldId: 'customers-dob',
    },
  ],
  tables: [
    {
      name: 'customers',
      displayName: 'Customers',
      description: 'Customer master data with demographic and contact information',
      isSelected: true,
      rowCount: 500000,
      fields: [
        {
          id: 'customers-customer_id',
          fieldName: 'customer_id',
          dataType: 'integer',
          nullable: false,
          generatorType: 'sequential',
          distribution: '1-1000000',
          piiLabel: 'none',
          relationshipTarget: 'orders.customer_id',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'customers-email',
          fieldName: 'email',
          dataType: 'string',
          nullable: false,
          generatorType: 'faker',
          distribution: 'email',
          piiLabel: 'email',
          piiMaskingStrategy: undefined,
          isConfigured: false,
          configurationStatus: 'blocked',
          blockReason: 'Missing PII masking strategy',
        },
        {
          id: 'customers-date_of_birth',
          fieldName: 'date_of_birth',
          dataType: 'date',
          nullable: true,
          generatorType: 'faker',
          distribution: 'date_of_birth',
          piiLabel: 'dob',
          piiMaskingStrategy: undefined,
          isConfigured: false,
          configurationStatus: 'blocked',
          blockReason: 'Missing PII masking strategy',
        },
        {
          id: 'customers-country',
          fieldName: 'country',
          dataType: 'string',
          nullable: false,
          generatorType: 'faker',
          distribution: 'country',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'customers-created_at',
          fieldName: 'created_at',
          dataType: 'timestamp',
          nullable: false,
          generatorType: 'timestamp',
          distribution: '2020-01-01 to now',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
      ],
    },
    {
      name: 'orders',
      displayName: 'Orders',
      description: 'Order transaction records with customer and temporal information',
      isSelected: true,
      rowCount: 2000000,
      fields: [
        {
          id: 'orders-order_id',
          fieldName: 'order_id',
          dataType: 'integer',
          nullable: false,
          generatorType: 'sequential',
          distribution: '1-10000000',
          piiLabel: 'none',
          relationshipTarget: 'order_items.order_id',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'orders-customer_id',
          fieldName: 'customer_id',
          dataType: 'integer',
          nullable: false,
          generatorType: 'foreign_key',
          distribution: 'references customers.customer_id',
          piiLabel: 'none',
          relationshipTarget: 'customers.customer_id',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'orders-purchase_amount',
          fieldName: 'purchase_amount',
          dataType: 'float',
          nullable: false,
          generatorType: 'numeric',
          distribution: '10.0-5000.0 (normal)',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'orders-order_status',
          fieldName: 'order_status',
          dataType: 'string',
          nullable: false,
          generatorType: 'categorical',
          distribution: 'pending,confirmed,shipped,delivered,cancelled',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'orders-order_date',
          fieldName: 'order_date',
          dataType: 'timestamp',
          nullable: false,
          generatorType: 'timestamp',
          distribution: '2020-01-01 to now',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
      ],
    },
    {
      name: 'order_items',
      displayName: 'Order Items',
      description: 'Line-level order items with product and quantity information',
      isSelected: true,
      rowCount: 5000000,
      fields: [
        {
          id: 'order_items-order_item_id',
          fieldName: 'order_item_id',
          dataType: 'integer',
          nullable: false,
          generatorType: 'sequential',
          distribution: '1-50000000',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'order_items-order_id',
          fieldName: 'order_id',
          dataType: 'integer',
          nullable: false,
          generatorType: 'foreign_key',
          distribution: 'references orders.order_id',
          piiLabel: 'none',
          relationshipTarget: 'orders.order_id',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'order_items-product_id',
          fieldName: 'product_id',
          dataType: 'string',
          nullable: false,
          generatorType: 'faker',
          distribution: 'SKU format',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'order_items-quantity',
          fieldName: 'quantity',
          dataType: 'integer',
          nullable: false,
          generatorType: 'numeric',
          distribution: '1-100',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
        {
          id: 'order_items-unit_price',
          fieldName: 'unit_price',
          dataType: 'float',
          nullable: false,
          generatorType: 'numeric',
          distribution: '0.99-999.99',
          piiLabel: 'none',
          isConfigured: true,
          configurationStatus: 'complete',
        },
      ],
    },
  ],
}

export function useDataset() {
  const [dataset, setDataset] = useState<Dataset>(MOCK_DATASET)
  const [selectedTable, setSelectedTable] = useState<string>('customers')
  const [searchQuery, setSearchQuery] = useState('')
  const [columnVisibility, setColumnVisibility] = useState<Record<string, boolean>>({
    fieldName: true,
    dataType: true,
    generatorType: true,
    piiLabel: true,
    nullable: true,
    relationshipTarget: true,
  })

  const currentTable = dataset.tables.find((t) => t.name === selectedTable)

  const filteredFields = currentTable?.fields.filter(
    (field) =>
      field.fieldName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      field.generatorType.toLowerCase().includes(searchQuery.toLowerCase()),
  ) || []

  const updateField = (fieldId: string, updates: Partial<SchemaField>) => {
    setDataset((prev) => ({
      ...prev,
      tables: prev.tables.map((table) => ({
        ...table,
        fields: table.fields.map((field) =>
          field.id === fieldId ? { ...field, ...updates } : field,
        ),
      })),
    }))
  }

  const updateDatasetConfig = (config: Partial<Dataset>) => {
    setDataset((prev) => ({ ...prev, ...config }))
  }

  const blockingIssuesCount = dataset.privacyIssues.filter((i) => i.severity === 'error').length

  return {
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
    updateDatasetConfig,
    blockingIssuesCount,
  }
}

/**
 * Real product lookup via PackScan backend → Open Food/Beauty/Products Facts.
 */

import type { BarcodeDetection } from './types'

export interface ProductDetailRow {
  group: string
  label: string
  value: string
}

export interface NutritionRow {
  label: string
  value: string
  key?: string
}

export interface ProductLookupResult {
  found: boolean
  code: string
  gtin: string | null
  name?: string | null
  brand?: string | null
  quantity?: string | null
  countries?: string | null
  categories?: string | null
  packaging?: string | null
  image_url?: string | null
  images?: Record<string, string | null | undefined>
  ingredients?: string | null
  allergens?: string | null
  traces?: string | null
  labels?: string | null
  nova_group?: string | null
  nutriscore_grade?: string | null
  ecoscore_grade?: string | null
  details: ProductDetailRow[]
  nutrition: NutritionRow[]
  fields: Record<string, string>
  source?: string | null
  message: string
  missing_legal_metrology_note?: string | null
}

export async function lookupProductByGtin(
  detection: BarcodeDetection,
): Promise<ProductLookupResult> {
  const code = detection.gtin?.replace(/^0/, '') || detection.value
  const res = await fetch(`/api/products/lookup?code=${encodeURIComponent(code)}`)
  if (!res.ok) {
    let detail = 'Product lookup failed'
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      /* ignore */
    }
    return {
      found: false,
      code,
      gtin: detection.gtin,
      fields: {},
      details: [],
      nutrition: [],
      message: detail,
      missing_legal_metrology_note:
        'Lookup failed. Continue with label OCR for Legal Metrology declarations.',
    }
  }
  const data = await res.json()
  return {
    found: Boolean(data.found),
    code: data.code || code,
    gtin: detection.gtin,
    name: data.name,
    brand: data.brand,
    quantity: data.quantity,
    countries: data.countries,
    categories: data.categories,
    packaging: data.packaging,
    image_url: data.image_url,
    images: data.images || {},
    ingredients: data.ingredients,
    allergens: data.allergens,
    traces: data.traces,
    labels: data.labels,
    nova_group: data.nova_group,
    nutriscore_grade: data.nutriscore_grade,
    ecoscore_grade: data.ecoscore_grade,
    details: Array.isArray(data.details) ? data.details : [],
    nutrition: Array.isArray(data.nutrition) ? data.nutrition : [],
    fields: data.fields || {},
    source: data.source,
    message: data.message || '',
    missing_legal_metrology_note: data.missing_legal_metrology_note,
  }
}

export { buildProductLookupRequest } from './decode'

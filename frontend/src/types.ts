export type FieldStatus =
  | 'PASS'
  | 'FAIL'
  | 'WARNING'
  | 'NOT_DETECTED'
  | 'NOT_APPLICABLE'
  | 'DETECTED'
  | 'LOW_CONFIDENCE'
  | string

export type ScanStatus =
  | 'uploaded'
  | 'pending'
  | 'Compliant'
  | 'Partially Compliant'
  | 'Non-Compliant'
  | 'OCR Failed'
  | 'No Text Detected'
  | string

export interface ExtractedField {
  id: number
  field_key: string
  field_label: string
  value: string | null
  confidence: number
  status: FieldStatus | string
}

export interface Violation {
  id: number
  rule_id: string
  severity: string
  status: string
  message: string
  recommendation: string
}

export interface ReportInfo {
  id: number
  scan_id: number
  file_path: string
  created_at: string
  download_url?: string | null
}

export interface ScanDetail {
  id: number
  product_name: string | null
  image_path: string
  image_url?: string | null
  annotated_image_url?: string | null
  status: ScanStatus
  screening_score: number | null
  passed_count: number
  warning_count: number
  failed_count: number
  not_detected_count?: number
  not_applicable_count?: number
  raw_ocr_text: string | null
  ocr_engine?: string | null
  ocr_mean_confidence?: number | null
  error_message?: string | null
  barcode_value?: string | null
  barcode_format?: string | null
  barcode_checksum_valid?: boolean | null
  barcode_gtin?: string | null
  barcode_raw?: string | null
  barcode_source?: string | null
  barcode_product?: Record<string, unknown> | null
  barcode_lookup_source?: string | null
  barcode_lookup_found?: boolean
  created_at: string
  extracted_fields: ExtractedField[]
  violations: Violation[]
  report?: ReportInfo | null
}

export interface ScanSummary {
  id: number
  product_name: string | null
  image_path: string
  status: ScanStatus
  screening_score: number | null
  passed_count: number
  warning_count: number
  failed_count: number
  not_detected_count?: number
  created_at: string
  violation_count: number
  ocr_engine?: string | null
  barcode_value?: string | null
  barcode_format?: string | null
}

export interface DashboardStats {
  total_scans: number
  compliant: number
  partially_compliant: number
  non_compliant: number
  compliance_distribution: { name: string; value: number }[]
  recent_trend: { date: string; scans: number }[]
  common_violations: { message: string; count: number }[]
}

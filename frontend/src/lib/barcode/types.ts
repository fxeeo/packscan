/**
 * Shared barcode types for PackScan.
 * Keep product-lookup ready: gtin can later be sent to an external API.
 */

export type SupportedBarcodeFormat =
  | 'EAN_13'
  | 'GTIN_13'
  | 'EAN_8'
  | 'UPC_A'
  | 'UPC_E'
  | 'CODE_128'
  | 'CODE_39'
  | 'ITF'
  | 'CODABAR'
  | 'RSS_14'
  | 'UNKNOWN'

export interface BarcodeDetection {
  /** Raw symbology text returned by the decoder */
  rawValue: string
  /** Normalized digits / code string used for storage & APIs */
  value: string
  format: SupportedBarcodeFormat
  /** True / false when checksum applies; null for formats without a standard check digit */
  checksumValid: boolean | null
  /** GTIN-14 zero-padded form when applicable (EAN-13 / UPC-A / EAN-8) */
  gtin: string | null
  source: 'camera' | 'image' | 'manual'
  detectedAt: string
}

export interface BarcodeAttachPayload {
  barcode_value: string
  barcode_format: string
  barcode_checksum_valid: boolean | null
  barcode_gtin: string | null
  barcode_raw: string
  barcode_source: 'camera' | 'image' | 'manual'
}

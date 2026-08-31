import type { DashboardStats, ReportInfo, ScanDetail, ScanSummary } from '../types'

const API_BASE = ''

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = 'Request failed'
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function uploadScan(file: File): Promise<ScanDetail> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/scans`, {
    method: 'POST',
    body: form,
  })
  return handle(res)
}

export async function attachBarcode(
  id: number,
  payload: {
    barcode_value: string
    barcode_format: string
    barcode_checksum_valid: boolean | null
    barcode_gtin: string | null
    barcode_raw: string
    barcode_source: 'camera' | 'image' | 'manual'
  },
): Promise<ScanDetail> {
  const res = await fetch(`${API_BASE}/api/scans/${id}/barcode`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handle(res)
}

export async function analyzeScan(id: number): Promise<{ scan: ScanDetail; message: string }> {
  const res = await fetch(`${API_BASE}/api/analyze/${id}`, { method: 'POST' })
  return handle(res)
}

export async function getScan(id: number): Promise<ScanDetail> {
  const res = await fetch(`${API_BASE}/api/scans/${id}`)
  return handle(res)
}

export async function listScans(): Promise<ScanSummary[]> {
  const res = await fetch(`${API_BASE}/api/scans`)
  return handle(res)
}

export async function getDashboard(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/api/dashboard`)
  return handle(res)
}

export async function generateReport(id: number): Promise<ReportInfo> {
  const res = await fetch(`${API_BASE}/api/reports/${id}`, { method: 'POST' })
  return handle(res)
}

export function reportDownloadUrl(id: number): string {
  return `${API_BASE}/api/reports/${id}`
}

export function assetUrl(path?: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_BASE}${path}`
}

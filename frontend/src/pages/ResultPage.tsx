import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, Download, FileText, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { FieldBadge, StatusBadge } from '@/components/ui/Badge'
import { ProductCatalogDetails } from '@/components/ProductCatalogDetails'
import { assetUrl, generateReport, getScan, reportDownloadUrl } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import type { ProductLookupResult } from '@/lib/barcode'
import type { ScanDetail } from '@/types'

export function ResultPage() {
  const { id } = useParams()
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [reportBusy, setReportBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getScan(Number(id))
      .then(setScan)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const onReport = async () => {
    if (!scan) return
    setReportBusy(true)
    try {
      await generateReport(scan.id)
      window.open(reportDownloadUrl(scan.id), '_blank')
      const refreshed = await getScan(scan.id)
      setScan(refreshed)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report generation failed')
    } finally {
      setReportBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading result…
      </div>
    )
  }

  if (!scan) {
    return <div className="text-rose-700">{error || 'Scan not found'}</div>
  }

  const fails = scan.violations.filter((v) => v.status === 'FAIL' || v.status === 'NOT_DETECTED')
  const warns = scan.violations.filter((v) => v.status === 'WARNING' || v.status === 'NOT_APPLICABLE')

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-navy-700">Scan result</p>
          <h1 className="font-display text-3xl font-bold text-navy-900">
            {scan.product_name || 'Product label screening'}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {formatDate(scan.created_at)}
            {scan.ocr_engine ? ` · OCR: ${scan.ocr_engine}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onReport} disabled={reportBusy || scan.screening_score == null}>
            {reportBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Generate PDF Report
          </Button>
          <Link to="/scan">
            <Button variant="outline">
              <RefreshCw className="h-4 w-4" /> Scan Another Product
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      )}
      {scan.error_message && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {scan.error_message}
        </div>
      )}

      {scan.barcode_value && (
        <Card className="border-emerald-200">
          <CardHeader>
            <CardTitle>Detected barcode & catalog info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <div className="text-xs text-slate-500">Value</div>
                <div className="font-mono font-semibold">{scan.barcode_value}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Format</div>
                <div className="font-semibold">{scan.barcode_format || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Checksum</div>
                <div className="font-semibold">
                  {scan.barcode_checksum_valid === null
                    ? 'N/A'
                    : scan.barcode_checksum_valid
                      ? 'Valid'
                      : 'Invalid'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">GTIN</div>
                <div className="font-mono font-semibold">{scan.barcode_gtin || '—'}</div>
              </div>
            </div>
            {scan.barcode_lookup_found && scan.barcode_product ? (
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <ProductCatalogDetails product={toCatalogProduct(scan)} />
              </div>
            ) : scan.barcode_value ? (
              <p className="text-xs text-slate-500">
                No Open*Facts catalog match for this barcode. Label OCR still drives Legal Metrology
                fields (MRP, care, mfg date).
              </p>
            ) : null}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Product evidence</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
              <img
                src={assetUrl(scan.image_url)}
                alt="Uploaded product"
                className="mx-auto max-h-64 object-contain"
              />
            </div>
            {scan.annotated_image_url && (
              <div>
                <p className="mb-1 text-xs font-medium text-slate-500">OCR annotated evidence</p>
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                  <img
                    src={assetUrl(scan.annotated_image_url)}
                    alt="OCR annotated"
                    className="mx-auto max-h-64 object-contain"
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Automated Screening Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-end gap-6">
              <div>
                <div className="font-display text-5xl font-bold text-navy-900">
                  {scan.screening_score == null ? '—' : Math.round(scan.screening_score)}
                  <span className="text-2xl text-slate-400"> / 100</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Dynamic score from this scan only — not a legally binding determination.
                </p>
              </div>
              <StatusBadge status={scan.status} />
            </div>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Metric label="Passed" value={scan.passed_count} tone="text-emerald-700" />
              <Metric label="Warnings" value={scan.warning_count} tone="text-amber-700" />
              <Metric label="Failed" value={scan.failed_count} tone="text-rose-700" />
              <Metric label="Not detected" value={scan.not_detected_count ?? 0} tone="text-rose-700" />
              <Metric label="N/A" value={scan.not_applicable_count ?? 0} tone="text-slate-600" />
            </div>
            {scan.ocr_mean_confidence != null && (
              <p className="mt-3 text-xs text-slate-500">
                Mean OCR confidence: {Math.round(scan.ocr_mean_confidence * 100)}%
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Extracted declarations</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3 font-semibold">Field</th>
                <th className="py-2 pr-3 font-semibold">Value</th>
                <th className="py-2 pr-3 font-semibold">Confidence</th>
                <th className="py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {scan.extracted_fields.map((f) => (
                <tr key={f.id} className="border-b border-slate-100 align-top">
                  <td className="py-3 pr-3 font-medium text-slate-800">{f.field_label}</td>
                  <td className="py-3 pr-3 text-slate-600">{f.value ?? '—'}</td>
                  <td className="py-3 pr-3 text-slate-600">{Math.round(f.confidence * 100)}%</td>
                  <td className="py-3">
                    <FieldBadge status={f.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-600" /> Violations & gaps
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {fails.length === 0 && warns.length === 0 && (
              <p className="text-sm text-slate-500">No warnings or missing mandatory detections.</p>
            )}
            {fails.map((v) => (
              <ViolationItem key={v.id} icon="❌" item={v} />
            ))}
            {warns.map((v) => (
              <ViolationItem key={v.id} icon="⚠️" item={v} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-navy-700" /> Evidence & OCR text
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600">
            <p>
              Results are produced from the uploaded image via OpenCV preprocessing + real OCR + rule
              engine. No predetermined compliance values.
            </p>
            {scan.raw_ocr_text && (
              <details className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <summary className="cursor-pointer font-medium text-slate-800">Raw OCR text</summary>
                <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-600">{scan.raw_ocr_text}</pre>
              </details>
            )}
            <p className="text-xs text-slate-500 border-t border-slate-100 pt-3">
              This system provides automated compliance screening assistance. Final legal/enforcement
              decisions require verification by an authorized officer.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${tone}`}>{value}</div>
    </div>
  )
}

function ViolationItem({
  icon,
  item,
}: {
  icon: string
  item: { severity: string; message: string; recommendation: string; rule_id: string; status: string }
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex items-start gap-2">
        <span>{icon}</span>
        <div>
          <div className="text-sm font-semibold text-slate-900">{item.message}</div>
          <div className="mt-1 flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
              {item.severity}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
              {item.rule_id}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
              {item.status}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            <span className="font-medium text-slate-700">Suggested action: </span>
            {item.recommendation}
          </p>
        </div>
      </div>
    </div>
  )
}

function toCatalogProduct(scan: ScanDetail): ProductLookupResult {
  const raw = (scan.barcode_product || {}) as Record<string, unknown>
  const details = Array.isArray(raw.details) ? (raw.details as ProductLookupResult['details']) : []
  const nutrition = Array.isArray(raw.nutrition)
    ? (raw.nutrition as ProductLookupResult['nutrition'])
    : []
  const images =
    raw.images && typeof raw.images === 'object'
      ? (raw.images as Record<string, string | null | undefined>)
      : {}

  return {
    found: true,
    code: String(raw.code || scan.barcode_value || ''),
    gtin: scan.barcode_gtin,
    name: (raw.name as string) || null,
    brand: (raw.brand as string) || null,
    quantity: (raw.quantity as string) || null,
    countries: (raw.countries as string) || null,
    categories: (raw.categories as string) || null,
    packaging: (raw.packaging as string) || null,
    image_url: (raw.image_url as string) || null,
    images,
    ingredients: (raw.ingredients as string) || null,
    allergens: (raw.allergens as string) || null,
    traces: (raw.traces as string) || null,
    labels: (raw.labels as string) || null,
    nova_group: (raw.nova_group as string) || null,
    nutriscore_grade: (raw.nutriscore_grade as string) || null,
    ecoscore_grade: (raw.ecoscore_grade as string) || null,
    details,
    nutrition,
    fields: (raw.fields as Record<string, string>) || {},
    source: scan.barcode_lookup_source || (raw.source as string) || null,
    message: String(raw.message || 'Catalog product loaded.'),
    missing_legal_metrology_note: (raw.missing_legal_metrology_note as string) || null,
  }
}

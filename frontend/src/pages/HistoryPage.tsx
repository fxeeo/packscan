import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/Badge'
import { listScans, reportDownloadUrl } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import type { ScanSummary } from '@/types'

export function HistoryPage() {
  const [scans, setScans] = useState<ScanSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    listScans()
      .then(setScans)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6 animate-fade-up">
      <div>
        <h1 className="font-display text-3xl font-bold text-navy-900">Scan History</h1>
        <p className="mt-1 text-sm text-slate-500">
          Local demonstration history of previous packaged commodity screenings.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Previous scans</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="flex items-center gap-2 py-10 text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading history…
            </div>
          )}
          {error && <div className="text-sm text-rose-700">{error}</div>}
          {!loading && !error && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3 font-semibold">Product</th>
                    <th className="py-2 pr-3 font-semibold">Date</th>
                    <th className="py-2 pr-3 font-semibold">Score</th>
                    <th className="py-2 pr-3 font-semibold">Barcode</th>
                    <th className="py-2 pr-3 font-semibold">Status</th>
                    <th className="py-2 pr-3 font-semibold">Violations</th>
                    <th className="py-2 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((s) => (
                    <tr key={s.id} className="border-b border-slate-100">
                      <td className="py-3 pr-3">
                        <div className="font-medium text-slate-900">
                          {s.product_name || `Scan #${s.id}`}
                        </div>
                        {s.ocr_engine ? (
                          <span className="text-[11px] font-medium text-navy-700">OCR: {s.ocr_engine}</span>
                        ) : null}
                      </td>
                      <td className="py-3 pr-3 text-slate-600">{formatDate(s.created_at)}</td>
                      <td className="py-3 pr-3 font-semibold text-navy-900">
                        {s.screening_score != null ? Math.round(s.screening_score) : '—'}
                      </td>
                      <td className="py-3 pr-3 font-mono text-xs text-slate-700">
                        {s.barcode_value || '—'}
                      </td>
                      <td className="py-3 pr-3">
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="py-3 pr-3 text-slate-700">{s.violation_count}</td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Link to={`/result/${s.id}`}>
                            <Button size="sm" variant="secondary">
                              <Eye className="h-3.5 w-3.5" /> View
                            </Button>
                          </Link>
                          {s.status !== 'uploaded' && (
                            <a href={reportDownloadUrl(s.id)} target="_blank" rel="noreferrer">
                              <Button size="sm" variant="outline">
                                View Report
                              </Button>
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {scans.length === 0 && (
                <p className="py-8 text-center text-sm text-slate-500">No scans yet.</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

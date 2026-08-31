import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { getDashboard } from '@/lib/api'
import type { DashboardStats } from '@/types'

const PIE_COLORS = ['#059669', '#d97706', '#e11d48']

export function DashboardPage() {
  const [data, setData] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading dashboard…
      </div>
    )
  }

  if (!data) {
    return <div className="text-rose-700">{error || 'Failed to load dashboard'}</div>
  }

  return (
    <div className="space-y-6 animate-fade-up">
      <div>
        <h1 className="font-display text-3xl font-bold text-navy-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Local screening analytics for demonstration (includes demo sample scans).
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Scans" value={data.total_scans} />
        <StatCard label="Compliant" value={data.compliant} accent="text-emerald-700" />
        <StatCard label="Partially Compliant" value={data.partially_compliant} accent="text-amber-700" />
        <StatCard label="Non-Compliant" value={data.non_compliant} accent="text-rose-700" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Compliance distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.compliance_distribution}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                >
                  {data.compliance_distribution.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent scan trend</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.recent_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="scans" stroke="#0b3a6e" strokeWidth={2.5} dot />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Common violations</CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.common_violations.map((v) => ({
                ...v,
                short: v.message.length > 42 ? `${v.message.slice(0, 42)}…` : v.message,
              }))}
              layout="vertical"
              margin={{ left: 20, right: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="short" width={220} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#1d6fbf" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({
  label,
  value,
  accent = 'text-navy-900',
}: {
  label: string
  value: number
  accent?: string
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
        <div className={`mt-2 font-display text-3xl font-bold ${accent}`}>{value}</div>
      </CardContent>
    </Card>
  )
}

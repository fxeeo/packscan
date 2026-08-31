import { Link } from 'react-router-dom'
import {
  Camera,
  FileSearch,
  Scale,
  TriangleAlert,
  FileText,
  ChartColumn,
  ArrowRight,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'

const features = [
  { icon: Camera, title: 'Product Scanning', desc: 'Upload or capture packaged commodity label images.' },
  { icon: FileSearch, title: 'Declaration Extraction', desc: 'Pull MRP, net qty, manufacturer and care details.' },
  { icon: Scale, title: 'Rule-Based Compliance', desc: 'Screen against configurable Legal Metrology rules.' },
  { icon: TriangleAlert, title: 'Violation Detection', desc: 'Flag missing or unclear mandatory declarations.' },
  { icon: FileText, title: 'Inspection Reports', desc: 'Generate downloadable PDF screening reports.' },
  { icon: ChartColumn, title: 'Compliance Analytics', desc: 'Track scan trends and common issues locally.' },
]

const steps = ['Scan', 'Extract', 'Validate', 'Report']

export function HomePage() {
  return (
    <div className="space-y-12 animate-fade-up">
      <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,#0b3a6e_0%,#1d6fbf_48%,#e8f1fb_48%,#ffffff_100%)] opacity-[0.97]" />
        <div className="relative grid gap-8 px-6 py-12 md:grid-cols-2 md:px-10 md:py-16">
          <div className="text-white">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-blue-100">
              SIH26034 · Legal Metrology
            </p>
            <h1 className="font-display text-4xl font-bold leading-tight md:text-5xl">PackScan</h1>
            <p className="mt-3 text-xl font-semibold text-blue-50">
              Smart Packaged Commodity Compliance
            </p>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-blue-100/95">
              Automated screening of packaged commodity labels against Legal Metrology requirements.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/scan">
                <Button size="lg" className="bg-white text-navy-900 hover:bg-blue-50">
                  Scan Product <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/history">
                <Button size="lg" variant="outline" className="border-white/40 bg-white/10 text-white hover:bg-white/20">
                  View Scan History
                </Button>
              </Link>
            </div>
          </div>
          <div className="flex items-end">
            <div className="w-full rounded-2xl border border-white/50 bg-white/95 p-5 text-slate-800 shadow-lg">
              <p className="text-xs font-semibold uppercase tracking-wider text-navy-700">How it works</p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {steps.map((s, i) => (
                  <div key={s} className="flex items-center gap-2">
                    <span className="rounded-xl bg-navy-900 px-3 py-2 text-sm font-semibold text-white">
                      {i + 1}. {s}
                    </span>
                    {i < steps.length - 1 && <ArrowRight className="h-4 w-4 text-slate-400" />}
                  </div>
                ))}
              </div>
              <p className="mt-5 text-xs leading-relaxed text-slate-500 border-t border-slate-100 pt-4">
                This system provides automated compliance screening assistance. Final legal/enforcement
                decisions require verification by an authorized officer.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-5">
          <h2 className="font-display text-2xl font-bold text-navy-900">Platform capabilities</h2>
          <p className="text-sm text-slate-500 mt-1">
            Built for inspector-assisted screening under Packaged Commodities Rules, 2011 (prototype).
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <Card key={f.title} className="transition hover:-translate-y-0.5 hover:shadow-md">
              <CardContent className="pt-5">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-navy-100 text-navy-900">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold text-slate-900">{f.title}</h3>
                <p className="mt-1 text-sm text-slate-500">{f.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  )
}

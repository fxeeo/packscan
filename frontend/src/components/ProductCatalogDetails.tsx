import type { ReactNode } from 'react'
import type { ProductLookupResult } from '@/lib/barcode'

/** Full A–Z catalog display for barcode product lookup results. */
export function ProductCatalogDetails({ product }: { product: ProductLookupResult }) {
  if (!product.found) {
    return (
      <div className="mt-2 space-y-2">
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950">
          {product.message}
        </div>
        {product.missing_legal_metrology_note && (
          <p className="text-xs text-slate-600">{product.missing_legal_metrology_note}</p>
        )}
      </div>
    )
  }

  const groups = groupDetails(product.details || [])
  const images = product.images || {}
  const imageEntries = Object.entries(images).filter(([, url]) => Boolean(url))

  return (
    <div className="mt-3 space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <Info label="Name" value={product.name || '—'} />
        <Info label="Brand" value={product.brand || '—'} />
        <Info label="Quantity" value={product.quantity || '—'} />
        <Info label="Country" value={product.countries || '—'} />
        <Info label="Labels" value={product.labels || '—'} />
        <Info label="Allergens" value={product.allergens || '—'} />
        <Info label="Traces" value={product.traces || '—'} />
        <Info label="NOVA / Nutri / Eco" value={`${product.nova_group || '—'} / ${product.nutriscore_grade || '—'} / ${product.ecoscore_grade || '—'}`} />
        <Info label="Source" value={product.source || '—'} />
        <Info label="Barcode code" value={product.code} mono />
      </div>

      {product.ingredients && (
        <Section title="Full ingredients">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{product.ingredients}</p>
        </Section>
      )}

      {product.categories && (
        <Section title="Categories">
          <p className="text-sm text-slate-800">{product.categories}</p>
        </Section>
      )}

      {product.packaging && (
        <Section title="Packaging">
          <p className="text-sm text-slate-800">{product.packaging}</p>
        </Section>
      )}

      {product.nutrition.length > 0 && (
        <Section title={`Nutrition (${product.nutrition.length} values)`}>
          <div className="max-h-72 overflow-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">Nutrient</th>
                  <th className="px-3 py-2">Value</th>
                </tr>
              </thead>
              <tbody>
                {product.nutrition.map((row) => (
                  <tr key={`${row.key || row.label}-${row.value}`} className="border-t border-slate-100">
                    <td className="px-3 py-1.5 text-slate-700">{row.label}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-900">{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {imageEntries.length > 0 && (
        <Section title="Product images">
          <div className="grid gap-3 sm:grid-cols-2">
            {imageEntries.map(([kind, url]) => (
              <div key={kind} className="rounded-xl border border-slate-200 bg-slate-50 p-2">
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{kind}</div>
                <img src={url!} alt={`${product.name || 'Product'} ${kind}`} className="max-h-48 w-full object-contain" />
              </div>
            ))}
          </div>
        </Section>
      )}

      {Object.keys(groups).length > 0 && (
        <Section title={`Complete catalog details (${product.details.length})`}>
          <div className="space-y-4">
            {Object.entries(groups).map(([group, rows]) => (
              <div key={group}>
                <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-navy-800">{group}</h4>
                <div className="grid gap-2">
                  {rows.map((row) => (
                    <div
                      key={`${group}-${row.label}-${row.value.slice(0, 24)}`}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
                    >
                      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        {row.label}
                      </div>
                      <div className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-900">
                        {row.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {product.missing_legal_metrology_note && (
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          {product.missing_legal_metrology_note}
        </p>
      )}
    </div>
  )
}

function groupDetails(details: ProductLookupResult['details']) {
  const groups: Record<string, ProductLookupResult['details']> = {}
  for (const row of details) {
    const g = row.group || 'Additional'
    if (!groups[g]) groups[g] = []
    groups[g].push(row)
  }
  return groups
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-navy-900">{title}</h3>
      {children}
    </div>
  )
}

function Info({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 break-words text-sm font-semibold text-slate-900 ${mono ? 'font-mono' : ''}`}>
        {value}
      </div>
    </div>
  )
}

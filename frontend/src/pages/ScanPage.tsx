import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Camera, ImagePlus, Loader2, ScanLine, Trash2, Upload } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { analyzeScan, attachBarcode, uploadScan } from '@/lib/api'
import type { BarcodeDetection } from '@/lib/barcode'

const ACCEPT = 'image/jpeg,image/png,image/webp,image/jpg'

export function ScanPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const inputRef = useRef<HTMLInputElement>(null)
  const cameraRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState('')
  const [barcode, setBarcode] = useState<BarcodeDetection | null>(null)

  useEffect(() => {
    const state = location.state as { barcode?: BarcodeDetection } | null
    if (state?.barcode?.value) {
      setBarcode(state.barcode)
    }
  }, [location.state])

  const assignFile = (f: File | null) => {
    setError('')
    if (!f) return
    if (
      !['image/jpeg', 'image/png', 'image/webp', 'image/jpg'].includes(f.type) &&
      !/\.(jpe?g|png|webp)$/i.test(f.name)
    ) {
      setError('Only JPG, JPEG, PNG, or WEBP images are allowed.')
      return
    }
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  const clear = () => {
    setFile(null)
    if (preview) URL.revokeObjectURL(preview)
    setPreview(null)
    setProgress('')
    setError('')
  }

  const onAnalyze = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      setProgress('Uploading product image…')
      const created = await uploadScan(file)
      if (barcode) {
        setProgress('Saving detected barcode with scan…')
        await attachBarcode(created.id, {
          barcode_value: barcode.value,
          barcode_format: barcode.format,
          barcode_checksum_valid: barcode.checksumValid,
          barcode_gtin: barcode.gtin,
          barcode_raw: barcode.rawValue,
          barcode_source: barcode.source,
        })
      }
      setProgress('Running real OCR (PaddleOCR)…')
      setProgress('Extracting declarations & checking rules…')
      const result = await analyzeScan(created.id)
      setProgress('Preparing compliance result…')
      navigate(`/result/${result.scan.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-up">
      <div>
        <h1 className="font-display text-3xl font-bold text-navy-900">Scan Product</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a packaged commodity label image for automated Legal Metrology screening.
        </p>
      </div>

      {barcode ? (
        <Card className="border-emerald-200 bg-emerald-50/50">
          <CardContent className="pt-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                Barcode attached
              </p>
              <p className="mt-1 font-mono text-sm font-semibold text-slate-900">{barcode.value}</p>
              <p className="text-xs text-slate-600">
                {barcode.format}
                {barcode.checksumValid === null
                  ? ''
                  : barcode.checksumValid
                    ? ' · checksum valid'
                    : ' · checksum invalid'}
                {barcode.gtin ? ` · GTIN ${barcode.gtin}` : ''}
              </p>
            </div>
            <div className="flex gap-2">
              <Link to="/barcode">
                <Button size="sm" variant="outline">
                  <ScanLine className="h-3.5 w-3.5" /> Rescan barcode
                </Button>
              </Link>
              <Button size="sm" variant="ghost" onClick={() => setBarcode(null)}>
                Remove
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-600">
              Optional: scan the package barcode first (EAN/UPC/Code128), then continue with label OCR.
            </p>
            <Link to="/barcode">
              <Button size="sm" variant="secondary">
                <ScanLine className="h-3.5 w-3.5" /> Scan barcode
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="pt-5">
          <p className="text-sm text-slate-600">
            <span className="font-semibold text-navy-900">Tip: </span>
            Sirf brand/front photo se MRP, Net Qty, Manufacturer detect nahi hote. Package ke{' '}
            <span className="font-semibold">peeche/side wale Legal Metrology label</span> ki clear,
            seedhi, well-lit photo upload karein.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Product image</CardTitle>
          <CardDescription>
            Supported: JPG, JPEG, PNG, WEBP. Best results: photograph the BACK/SIDE label panel
            where MRP, Net Qty, manufacturer and consumer care are printed (not only the brand front).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!preview ? (
            <div
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                assignFile(e.dataTransfer.files?.[0] ?? null)
              }}
              className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition ${
                dragOver ? 'border-navy-700 bg-navy-50' : 'border-slate-300 bg-slate-50/80'
              }`}
            >
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white border border-slate-200 text-navy-900">
                <Upload className="h-6 w-6" />
              </div>
              <p className="font-medium text-slate-800">Drag & drop label image here</p>
              <p className="mt-1 text-sm text-slate-500">or choose from device / camera</p>
              <div className="mt-5 flex flex-wrap justify-center gap-3">
                <Button type="button" onClick={() => inputRef.current?.click()}>
                  <ImagePlus className="h-4 w-4" /> Choose File
                </Button>
                <Button type="button" variant="outline" onClick={() => cameraRef.current?.click()}>
                  <Camera className="h-4 w-4" /> Capture from Camera
                </Button>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPT}
                className="hidden"
                onChange={(e) => assignFile(e.target.files?.[0] ?? null)}
              />
              <input
                ref={cameraRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => assignFile(e.target.files?.[0] ?? null)}
              />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
                <img src={preview} alt="Product preview" className="mx-auto max-h-[420px] object-contain" />
              </div>
              <div className="flex flex-wrap gap-3">
                <Button onClick={onAnalyze} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearchIcon />}
                  Analyze
                </Button>
                <Button variant="outline" onClick={clear} disabled={loading}>
                  <Trash2 className="h-4 w-4" /> Remove image
                </Button>
              </div>
            </div>
          )}

          {loading && (
            <div className="rounded-xl border border-navy-100 bg-navy-50 px-4 py-3 text-sm text-navy-900">
              <div className="mb-2 flex items-center gap-2 font-medium">
                <Loader2 className="h-4 w-4 animate-spin" /> Processing…
              </div>
              <p>{progress}</p>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white">
                <div className="h-full w-2/3 animate-pulse rounded-full bg-navy-700" />
              </div>
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              {error}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function FileSearchIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <circle cx="11.5" cy="14.5" r="2.5" />
      <path d="M13.3 16.3 15 18" />
    </svg>
  )
}

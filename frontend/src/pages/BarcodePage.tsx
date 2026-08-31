import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Camera,
  ImagePlus,
  Loader2,
  RefreshCw,
  ScanLine,
  StopCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import {
  decodeBarcodeFromImageFile,
  detectionFromManualCode,
  listVideoInputDevices,
  lookupProductByGtin,
  startCameraScan,
  type BarcodeDetection,
  type ProductLookupResult,
} from '@/lib/barcode'
import type { IScannerControls } from '@zxing/browser'
import { ProductCatalogDetails } from '@/components/ProductCatalogDetails'

type Mode = 'idle' | 'camera' | 'result'

export function BarcodePage() {
  const navigate = useNavigate()
  const videoRef = useRef<HTMLVideoElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const controlsRef = useRef<IScannerControls | null>(null)

  const [mode, setMode] = useState<Mode>('idle')
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState<string>('')
  const [detection, setDetection] = useState<BarcodeDetection | null>(null)
  const [product, setProduct] = useState<ProductLookupResult | null>(null)
  const [lookupBusy, setLookupBusy] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [manualCode, setManualCode] = useState('')

  const stopCamera = useCallback(() => {
    try {
      controlsRef.current?.stop()
    } catch {
      /* ignore */
    }
    controlsRef.current = null
    const video = videoRef.current
    if (video?.srcObject) {
      const stream = video.srcObject as MediaStream
      stream.getTracks().forEach((t) => t.stop())
      video.srcObject = null
    }
  }, [])

  useEffect(() => {
    listVideoInputDevices()
      .then((list) => {
        setDevices(list)
        const back = list.find((d) => /back|rear|environment/i.test(d.label))
        setDeviceId(back?.deviceId || list[0]?.deviceId || '')
      })
      .catch(() => setDevices([]))
    return () => stopCamera()
  }, [stopCamera])

  const onDetected = useCallback(
    async (d: BarcodeDetection) => {
      setDetection(d)
      setMode('result')
      setBusy(false)
      setError('')
      stopCamera()
      setLookupBusy(true)
      setProduct(null)
      try {
        const info = await lookupProductByGtin(d)
        setProduct(info)
      } catch (e) {
        setProduct({
          found: false,
          code: d.value,
          gtin: d.gtin,
          fields: {},
          details: [],
          nutrition: [],
          message: e instanceof Error ? e.message : 'Product lookup failed',
        })
      } finally {
        setLookupBusy(false)
      }
    },
    [stopCamera],
  )

  const startCamera = async () => {
    setError('')
    setDetection(null)
    setProduct(null)
    setBusy(true)
    setMode('camera')
    stopCamera()
    await new Promise((r) => setTimeout(r, 50))
    const video = videoRef.current
    if (!video) {
      setError('Video element not ready.')
      setBusy(false)
      setMode('idle')
      return
    }
    try {
      controlsRef.current = await startCameraScan(
        video,
        (d) => {
          void onDetected(d)
        },
        (msg) => setError(msg),
        deviceId || undefined,
      )
      setBusy(false)
    } catch (e) {
      setBusy(false)
      setMode('idle')
      setError(e instanceof Error ? e.message : 'Camera failed to start')
    }
  }

  const onImageSelected = async (file: File | null) => {
    if (!file) return
    setError('')
    setBusy(true)
    stopCamera()
    try {
      const d = await decodeBarcodeFromImageFile(file)
      await onDetected(d)
    } catch (e) {
      setBusy(false)
      setMode('idle')
      setError(e instanceof Error ? e.message : 'Image barcode scan failed')
    }
  }

  const onManualSubmit = async () => {
    setError('')
    setBusy(true)
    stopCamera()
    try {
      const d = detectionFromManualCode(manualCode)
      await onDetected(d)
    } catch (e) {
      setBusy(false)
      setMode('idle')
      setError(e instanceof Error ? e.message : 'Invalid barcode digits')
    }
  }

  const scanAgain = () => {
    setDetection(null)
    setProduct(null)
    setError('')
    setManualCode('')
    setMode('idle')
    stopCamera()
  }

  const continueAnalysis = () => {
    if (!detection) return
    navigate('/scan', {
      state: {
        barcode: detection,
        product,
      },
    })
  }

  const checksumLabel =
    detection?.checksumValid === null
      ? 'N/A (format has no universal check digit)'
      : detection?.checksumValid
        ? 'Valid'
        : 'Invalid'

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <div>
        <h1 className="font-display text-3xl font-bold text-navy-900">Barcode Scanner</h1>
        <p className="mt-1 text-sm text-slate-500">
          ZXing decode + real Open Food/Beauty/Products Facts lookup. MRP / consumer care usually
          still need the package label photo.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ScanLine className="h-5 w-5 text-navy-700" /> Scan barcode
          </CardTitle>
          <CardDescription>
            Point the camera at the bars (fill most of the frame), upload a clear close-up, or type
            the digits under the barcode. Supports EAN-13/8, UPC, Code128/39, ITF.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode !== 'result' && (
            <div className="flex flex-wrap gap-3">
              <Button type="button" onClick={startCamera} disabled={busy && mode === 'camera'}>
                {busy && mode === 'camera' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Camera className="h-4 w-4" />
                )}
                Start camera scan
              </Button>
              <Button type="button" variant="outline" onClick={() => fileRef.current?.click()} disabled={busy}>
                <ImagePlus className="h-4 w-4" /> Upload barcode image
              </Button>
              {mode === 'camera' && (
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => {
                    stopCamera()
                    setMode('idle')
                    setBusy(false)
                  }}
                >
                  <StopCircle className="h-4 w-4" /> Stop
                </Button>
              )}
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => void onImageSelected(e.target.files?.[0] ?? null)}
              />
            </div>
          )}

          {mode !== 'result' && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-2">
              <label className="block text-sm font-medium text-slate-700">
                Or type barcode digits
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="e.g. 8901030976735"
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm"
                  disabled={busy}
                />
              </label>
              <Button
                type="button"
                variant="outline"
                onClick={() => void onManualSubmit()}
                disabled={busy || manualCode.trim().length < 8}
              >
                Lookup typed barcode
              </Button>
            </div>
          )}

          {devices.length > 1 && mode !== 'result' && (
            <label className="block text-sm text-slate-600">
              Camera
              <select
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                disabled={mode === 'camera'}
              >
                {devices.map((d) => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </label>
          )}

          {(mode === 'camera' || mode === 'idle') && (
            <div
              className={`relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 ${
                mode === 'camera' ? 'block' : 'hidden'
              }`}
            >
              <video
                ref={videoRef}
                className="mx-auto max-h-[420px] w-full object-contain"
                muted
                playsInline
                autoPlay
              />
              {mode === 'camera' && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <div className="h-28 w-4/5 max-w-md rounded-lg border-2 border-emerald-400/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]" />
                </div>
              )}
              {mode === 'camera' && (
                <p className="bg-black/60 px-3 py-2 text-center text-xs text-white">
                  Align barcode inside the frame — decoding live with ZXing…
                </p>
              )}
            </div>
          )}

          {mode === 'result' && detection && (
            <div className="space-y-4 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                Barcode detected
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <Info label="Value" value={detection.value} mono />
                <Info label="Format" value={detection.format} />
                <Info label="Checksum" value={checksumLabel} />
                <Info label="GTIN" value={detection.gtin || '—'} mono />
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-navy-800">
                  Catalog product info
                </p>
                {lookupBusy && (
                  <p className="mt-2 flex items-center gap-2 text-sm text-slate-600">
                    <Loader2 className="h-4 w-4 animate-spin" /> Looking up Open Food/Beauty Facts…
                  </p>
                )}
                {!lookupBusy && product && (
                  <div className="mt-3">
                    <ProductCatalogDetails product={product} />
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <Button type="button" variant="outline" onClick={scanAgain}>
                  <RefreshCw className="h-4 w-4" /> Scan Again
                </Button>
                <Button type="button" onClick={continueAnalysis} disabled={lookupBusy}>
                  Continue Analysis
                </Button>
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

function Info({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 break-all text-sm font-semibold text-slate-900 ${mono ? 'font-mono' : ''}`}>
        {value}
      </div>
    </div>
  )
}

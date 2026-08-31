/**
 * Real ZXing-based barcode decoding (camera + image).
 * Multi-pass image preprocess + high-res camera constraints for harder packages.
 */

import {
  BrowserMultiFormatReader,
  BarcodeFormat,
  type IScannerControls,
} from '@zxing/browser'
import { DecodeHintType, type Result } from '@zxing/library'
import {
  toGtin14,
  validateChecksumForFormat,
} from './checksum'
import type { BarcodeDetection, SupportedBarcodeFormat } from './types'

const ALLOWED_FORMATS = [
  BarcodeFormat.EAN_13,
  BarcodeFormat.EAN_8,
  BarcodeFormat.UPC_A,
  BarcodeFormat.UPC_E,
  BarcodeFormat.CODE_128,
  BarcodeFormat.CODE_39,
  BarcodeFormat.ITF,
  BarcodeFormat.CODABAR,
  BarcodeFormat.RSS_14,
]

function createReader(scanDelayMs = 80): BrowserMultiFormatReader {
  const hints = new Map<DecodeHintType, unknown>()
  hints.set(DecodeHintType.POSSIBLE_FORMATS, ALLOWED_FORMATS)
  hints.set(DecodeHintType.TRY_HARDER, true)
  return new BrowserMultiFormatReader(hints, {
    delayBetweenScanAttempts: scanDelayMs,
    delayBetweenScanSuccess: 600,
  })
}

function mapFormat(format: BarcodeFormat | undefined): SupportedBarcodeFormat {
  switch (format) {
    case BarcodeFormat.EAN_13:
      return 'GTIN_13'
    case BarcodeFormat.EAN_8:
      return 'EAN_8'
    case BarcodeFormat.UPC_A:
      return 'UPC_A'
    case BarcodeFormat.UPC_E:
      return 'UPC_E'
    case BarcodeFormat.CODE_128:
      return 'CODE_128'
    case BarcodeFormat.CODE_39:
      return 'CODE_39'
    case BarcodeFormat.ITF:
      return 'ITF'
    case BarcodeFormat.CODABAR:
      return 'CODABAR'
    case BarcodeFormat.RSS_14:
      return 'RSS_14'
    default:
      return 'UNKNOWN'
  }
}

function fromZxingResult(result: Result, source: 'camera' | 'image' | 'manual'): BarcodeDetection {
  const rawValue = result.getText()
  const format = mapFormat(result.getBarcodeFormat())
  const digits = rawValue.replace(/\D/g, '')
  const value =
    format === 'CODE_128' || format === 'CODE_39' || format === 'CODABAR'
      ? rawValue.trim()
      : digits || rawValue.trim()

  const checksumFormat = format === 'GTIN_13' ? 'EAN_13' : format
  const checksumValid = validateChecksumForFormat(value, checksumFormat)
  const gtin = toGtin14(value, checksumFormat)

  return {
    rawValue,
    value,
    format,
    checksumValid,
    gtin,
    source,
    detectedAt: new Date().toISOString(),
  }
}

/** Build a detection from typed digits (fallback when camera/image fails). */
export function detectionFromManualCode(input: string): BarcodeDetection {
  const raw = input.trim()
  const digits = raw.replace(/\D/g, '')
  if (digits.length < 8) {
    throw new Error('Enter at least 8 digits from the barcode.')
  }

  let format: SupportedBarcodeFormat = 'CODE_128'
  let value = digits
  if (digits.length === 13) {
    format = 'GTIN_13'
  } else if (digits.length === 12) {
    format = 'UPC_A'
  } else if (digits.length === 8) {
    format = validateChecksumForFormat(digits, 'EAN_8') ? 'EAN_8' : 'UPC_E'
  } else {
    value = raw
    format = 'CODE_128'
  }

  const checksumFormat = format === 'GTIN_13' ? 'EAN_13' : format
  return {
    rawValue: raw,
    value,
    format,
    checksumValid: validateChecksumForFormat(value, checksumFormat),
    gtin: toGtin14(value, checksumFormat),
    source: 'manual',
    detectedAt: new Date().toISOString(),
  }
}

export async function listVideoInputDevices(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return []
  // Some browsers hide labels until permission is granted once.
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    })
    stream.getTracks().forEach((t) => t.stop())
  } catch {
    /* permission may already exist or user denied — still enumerate */
  }
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.filter((d) => d.kind === 'videoinput')
}

function videoConstraints(deviceId?: string): MediaTrackConstraints {
  const base: MediaTrackConstraints = {
    width: { ideal: 1920 },
    height: { ideal: 1080 },
    // @ts-expect-error focusMode supported on many mobile browsers
    focusMode: 'continuous',
  }
  if (deviceId) {
    return { ...base, deviceId: { exact: deviceId } }
  }
  return { ...base, facingMode: { ideal: 'environment' } }
}

/**
 * Continuous camera decode. Resolves controls; stops after first good decode.
 */
export async function startCameraScan(
  videoElement: HTMLVideoElement,
  onDetected: (detection: BarcodeDetection) => void,
  onError?: (message: string) => void,
  deviceId?: string,
): Promise<IScannerControls> {
  const reader = createReader(60)
  videoElement.setAttribute('playsinline', 'true')
  videoElement.muted = true

  try {
    const controls = await reader.decodeFromConstraints(
      { audio: false, video: videoConstraints(deviceId) },
      videoElement,
      (result, error, ctrl) => {
        if (result) {
          const detection = fromZxingResult(result, 'camera')
          if (detection.format === 'UNKNOWN') return
          // Accept even if checksum invalid — still useful for lookup retry / OCR pairing
          onDetected(detection)
          ctrl.stop()
          return
        }
        if (error && error.name && error.name !== 'NotFoundException') {
          onError?.(error.message || 'Camera decode error')
        }
      },
    )
    return controls
  } catch (e) {
    // Fallback: older path via device id
    try {
      const controls = await reader.decodeFromVideoDevice(
        deviceId || undefined,
        videoElement,
        (result, error, ctrl) => {
          if (result) {
            const detection = fromZxingResult(result, 'camera')
            if (detection.format === 'UNKNOWN') return
            onDetected(detection)
            ctrl.stop()
            return
          }
          if (error && error.name && error.name !== 'NotFoundException') {
            onError?.(error.message || 'Camera decode error')
          }
        },
      )
      return controls
    } catch (inner) {
      const msg =
        inner instanceof Error
          ? inner.message
          : e instanceof Error
            ? e.message
            : 'Unable to access camera. Allow camera permission or use image upload.'
      onError?.(msg)
      throw inner instanceof Error ? inner : e
    }
  }
}

function drawImageToCanvas(
  source: CanvasImageSource,
  width: number,
  height: number,
  opts?: { invert?: boolean; contrast?: number; cropY?: number; cropH?: number },
): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  const sx = 0
  const sy = opts?.cropY ?? 0
  const sw = width
  const sh = opts?.cropH ?? height
  canvas.width = Math.max(1, Math.round(sw))
  canvas.height = Math.max(1, Math.round(sh))
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return canvas

  ctx.drawImage(source, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)

  if (opts?.contrast || opts?.invert) {
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const data = img.data
    const contrast = opts.contrast ?? 1
    const intercept = 128 * (1 - contrast)
    for (let i = 0; i < data.length; i += 4) {
      let r = data[i] * contrast + intercept
      let g = data[i + 1] * contrast + intercept
      let b = data[i + 2] * contrast + intercept
      // grayscale
      const y = 0.299 * r + 0.587 * g + 0.114 * b
      let v = Math.max(0, Math.min(255, y))
      if (opts.invert) v = 255 - v
      data[i] = data[i + 1] = data[i + 2] = v
    }
    ctx.putImageData(img, 0, 0)
  }
  return canvas
}

function buildDecodeCanvases(img: HTMLImageElement): HTMLCanvasElement[] {
  const w = img.naturalWidth || img.width
  const h = img.naturalHeight || img.height
  if (!w || !h) return []

  // Upscale small phone crops — ZXing struggles below ~800px width
  const scale = w < 900 ? 900 / w : w > 2400 ? 2400 / w : 1
  const tw = Math.round(w * scale)
  const th = Math.round(h * scale)

  const base = document.createElement('canvas')
  base.width = tw
  base.height = th
  const bctx = base.getContext('2d')
  if (!bctx) return []
  bctx.imageSmoothingEnabled = true
  bctx.drawImage(img, 0, 0, tw, th)

  const canvases: HTMLCanvasElement[] = [base]

  // High contrast + invert variants
  canvases.push(drawImageToCanvas(base, tw, th, { contrast: 1.6 }))
  canvases.push(drawImageToCanvas(base, tw, th, { contrast: 1.8, invert: true }))

  // Center horizontal bands (barcode often mid-pack)
  const bands = [
    { y: Math.floor(th * 0.15), h: Math.floor(th * 0.7) },
    { y: Math.floor(th * 0.35), h: Math.floor(th * 0.35) },
    { y: Math.floor(th * 0.05), h: Math.floor(th * 0.4) },
    { y: Math.floor(th * 0.55), h: Math.floor(th * 0.4) },
  ]
  for (const band of bands) {
    canvases.push(drawImageToCanvas(base, tw, th, { cropY: band.y, cropH: band.h, contrast: 1.5 }))
    canvases.push(
      drawImageToCanvas(base, tw, th, {
        cropY: band.y,
        cropH: band.h,
        contrast: 1.7,
        invert: true,
      }),
    )
  }

  return canvases
}

export async function decodeBarcodeFromImageFile(file: File): Promise<BarcodeDetection> {
  if (!file.type.startsWith('image/') && !/\.(jpe?g|png|webp|gif|bmp)$/i.test(file.name)) {
    throw new Error('Please upload an image file containing a barcode.')
  }

  const url = URL.createObjectURL(file)
  const reader = createReader(40)

  try {
    // Pass 1: direct URL decode (fast path)
    try {
      const result = await reader.decodeFromImageUrl(url)
      const detection = fromZxingResult(result, 'image')
      if (detection.format !== 'UNKNOWN') return detection
    } catch {
      /* try preprocess path */
    }

    // Pass 2: multi-variant canvas decode
    const img = await loadImage(url)
    const canvases = buildDecodeCanvases(img)
    for (const canvas of canvases) {
      try {
        const result = reader.decodeFromCanvas(canvas)
        const detection = fromZxingResult(result, 'image')
        if (detection.format !== 'UNKNOWN') return detection
      } catch {
        /* next variant */
      }
    }

    throw new Error(
      'No barcode detected. Tips: fill the frame with the bars, avoid glare, try a closer photo, or type the digits below.',
    )
  } finally {
    URL.revokeObjectURL(url)
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('Could not load barcode image.'))
    img.src = url
  })
}

export function buildProductLookupRequest(detection: BarcodeDetection): {
  gtin: string | null
  barcode: string
  format: string
  endpointHint: string
} {
  return {
    gtin: detection.gtin,
    barcode: detection.value,
    format: detection.format,
    endpointHint: 'GET /api/products/lookup?code=...',
  }
}

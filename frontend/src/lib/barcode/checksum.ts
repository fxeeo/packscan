/**
 * Real checksum validators for retail barcodes.
 * No hardcoded product values — only algorithmic check-digit validation.
 */

function onlyDigits(value: string): string {
  return value.replace(/\D/g, '')
}

/** GS1 / EAN/UPC mod-10 check digit over the provided body (without check digit). */
function mod10CheckDigit(body: string): number {
  let sum = 0
  const reversed = body.split('').reverse()
  for (let i = 0; i < reversed.length; i++) {
    const n = Number(reversed[i])
    // From the right: odd positions ×3, even ×1 (1-based from right)
    sum += i % 2 === 0 ? n * 3 : n
  }
  return (10 - (sum % 10)) % 10
}

export function validateEan13(code: string): boolean {
  const d = onlyDigits(code)
  if (d.length !== 13) return false
  return mod10CheckDigit(d.slice(0, 12)) === Number(d[12])
}

export function validateEan8(code: string): boolean {
  const d = onlyDigits(code)
  if (d.length !== 8) return false
  return mod10CheckDigit(d.slice(0, 7)) === Number(d[7])
}

export function validateUpcA(code: string): boolean {
  const d = onlyDigits(code)
  if (d.length !== 12) return false
  return mod10CheckDigit(d.slice(0, 11)) === Number(d[11])
}

/** Expand UPC-E to UPC-A then validate. */
export function expandUpcE(code: string): string | null {
  const d = onlyDigits(code)
  if (d.length !== 8) return null
  // Standard UPC-E expansion uses number system + 6 product digits + check digit.
  const ns = d[0]
  const mid = d.slice(1, 7)
  const last = mid[5]
  let upcABody: string
  if (last >= '0' && last <= '2') {
    upcABody = ns + mid.slice(0, 2) + last + '0000' + mid.slice(2, 5)
  } else if (last === '3') {
    upcABody = ns + mid.slice(0, 3) + '00000' + mid.slice(3, 5)
  } else if (last === '4') {
    upcABody = ns + mid.slice(0, 4) + '00000' + mid[4]
  } else {
    upcABody = ns + mid.slice(0, 5) + '0000' + last
  }
  const check = mod10CheckDigit(upcABody)
  return upcABody + String(check)
}

export function validateUpcE(code: string): boolean {
  const d = onlyDigits(code)
  if (d.length !== 8) return false
  const expanded = expandUpcE(d)
  if (!expanded) return false
  // Expanded check digit must match UPC-E check digit
  return expanded[11] === d[7] && validateUpcA(expanded)
}

export function toGtin14(code: string, format: string): string | null {
  const d = onlyDigits(code)
  if (format === 'EAN_13' || format === 'GTIN_13') {
    if (d.length === 13) return d.padStart(14, '0')
  }
  if (format === 'UPC_A' && d.length === 12) return d.padStart(14, '0')
  if (format === 'EAN_8' && d.length === 8) return d.padStart(14, '0')
  if (format === 'UPC_E') {
    const expanded = expandUpcE(d)
    if (expanded) return expanded.padStart(14, '0')
  }
  return null
}

export function validateChecksumForFormat(
  value: string,
  format: string,
): boolean | null {
  switch (format) {
    case 'EAN_13':
    case 'GTIN_13':
      return validateEan13(value)
    case 'EAN_8':
      return validateEan8(value)
    case 'UPC_A':
      return validateUpcA(value)
    case 'UPC_E':
      return validateUpcE(value)
    case 'CODE_128':
    case 'CODE_39':
    case 'ITF':
    case 'CODABAR':
    case 'RSS_14':
      return null
    default:
      return null
  }
}

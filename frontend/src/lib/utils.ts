import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function statusTone(status: string): string {
  if (status === 'Compliant') return 'bg-emerald-50 text-emerald-800 border-emerald-200'
  if (status === 'Partially Compliant') return 'bg-amber-50 text-amber-900 border-amber-200'
  if (status === 'Non-Compliant') return 'bg-rose-50 text-rose-800 border-rose-200'
  return 'bg-slate-100 text-slate-700 border-slate-200'
}

export function fieldTone(status: string): string {
  if (status === 'PASS' || status === 'DETECTED') return 'bg-emerald-50 text-emerald-800 border-emerald-200'
  if (status === 'WARNING' || status === 'LOW_CONFIDENCE' || status === 'NOT_APPLICABLE')
    return 'bg-amber-50 text-amber-900 border-amber-200'
  if (status === 'NOT_DETECTED' || status === 'FAIL') return 'bg-rose-50 text-rose-800 border-rose-200'
  return 'bg-slate-100 text-slate-700 border-slate-200'
}

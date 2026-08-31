import { cn, statusTone, fieldTone } from '@/lib/utils'

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold',
        statusTone(status),
      )}
    >
      {status}
    </span>
  )
}

export function FieldBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-bold tracking-wide',
        fieldTone(status),
      )}
    >
      {status}
    </span>
  )
}

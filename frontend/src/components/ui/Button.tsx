import type { ButtonHTMLAttributes } from 'react'
import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

const variants: Record<Variant, string> = {
  primary:
    'bg-navy-900 text-white hover:bg-navy-800 shadow-sm shadow-navy-900/10',
  secondary: 'bg-navy-100 text-navy-900 hover:bg-blue-100',
  outline: 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50',
  ghost: 'bg-transparent text-navy-900 hover:bg-navy-100',
  danger: 'bg-rose-600 text-white hover:bg-rose-700',
}

const sizes: Record<Size, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:opacity-50 disabled:pointer-events-none',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'

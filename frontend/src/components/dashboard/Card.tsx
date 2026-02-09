import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
}

export default function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-white/[0.06] bg-white/[0.03] p-6 ${className}`}
    >
      {children}
    </div>
  )
}

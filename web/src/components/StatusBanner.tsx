import type { ReactNode } from 'react'

interface StatusBannerProps {
  tone: 'info' | 'error' | 'loading'
  children: ReactNode
}

export function StatusBanner({ tone, children }: StatusBannerProps) {
  return (
    <div className={`status-banner status-banner--${tone}`} role="status">
      {children}
    </div>
  )
}

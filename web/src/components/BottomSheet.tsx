import type { ReactNode } from 'react'

interface BottomSheetProps {
  variant: 'peek' | 'expanded' | 'nav'
  title: string
  children: ReactNode
}

export function BottomSheet({ variant, title, children }: BottomSheetProps) {
  return (
    <section
      className={`bottom-sheet bottom-sheet--${variant}`}
      aria-label={title}
    >
      <div className="bottom-sheet__handle" aria-hidden="true" />
      <h2 className="bottom-sheet__title">{title}</h2>
      {children}
    </section>
  )
}

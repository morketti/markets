import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Standard shadcn/ui composition: clsx for conditional classes, twMerge for
// Tailwind conflict resolution (e.g. last-write-wins on px-2 px-4 → px-4).
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

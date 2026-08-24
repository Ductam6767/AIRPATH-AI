import { describe, expect, it } from 'vitest'
import { resolveApiBase } from '../constants'

describe('resolveApiBase', () => {
  it('keeps local proxy behavior when VITE_API_URL is unset', () => {
    expect(resolveApiBase(undefined)).toBe('')
    expect(resolveApiBase('')).toBe('')
    expect(resolveApiBase('   ')).toBe('')
  })

  it('uses VITE_API_URL in production without a trailing slash', () => {
    expect(resolveApiBase('https://example.onrender.com')).toBe(
      'https://example.onrender.com',
    )
    expect(resolveApiBase('https://example.onrender.com/')).toBe(
      'https://example.onrender.com',
    )
  })
})

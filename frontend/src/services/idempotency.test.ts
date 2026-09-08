import { webcrypto } from 'node:crypto'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { newIdempotencyKey } from './idempotency'

afterEach(() => vi.unstubAllGlobals())

describe('request IDs on HTTP origins', () => {
  it('produces distinct RFC 4122 version 4 IDs when randomUUID is unavailable', () => {
    vi.stubGlobal('crypto', { getRandomValues: webcrypto.getRandomValues.bind(webcrypto) })
    const keys = Array.from({ length: 50 }, () => newIdempotencyKey())
    for (const key of keys) {
      expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
    }
    expect(new Set(keys).size).toBe(keys.length)
  })
})
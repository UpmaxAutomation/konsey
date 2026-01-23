import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock fetch globally
global.fetch = vi.fn()

// Mock import.meta.env
vi.stubGlobal('import', {
  meta: {
    env: {
      VITE_API_URL: 'http://localhost:8001'
    }
  }
})

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
})

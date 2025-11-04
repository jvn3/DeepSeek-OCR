/**
 * OCR API Client
 * Communicates with DeepSeek-OCR backend
 */

import type { OcrPage, SemanticResults, FormMapping, SemanticField } from '@/store/useAppStore'

const BASE_URL = process.env.NEXT_PUBLIC_OCR_BASE_URL || 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_OCR_API_KEY || ''

interface OcrImageOptions {
  docType?: string
  languageHint?: string
  returnLayout?: boolean
  returnWords?: boolean
  pageIndex?: number
}

interface ParseSemanticPayload {
  docType?: string
  text?: string
  layout?: {
    blocks: any[]
    lines: any[]
    words: any[]
  }
  hints?: {
    country?: string
    dateFormat?: string
  }
}

interface FormsMatchPayload {
  formId: string
  fields: Record<string, SemanticField>
  strict?: boolean
}

interface BatchJobResponse {
  jobId: string
  totalPages: number
  status: string
}

interface StreamPageResult {
  pageIndex: number
  status: 'complete' | 'error'
  result?: OcrPage
  error?: string
}

class OcrApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message)
    this.name = 'OcrApiError'
  }
}

async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers: HeadersInit = {
    ...(options.headers || {}),
  }

  if (API_KEY) {
    headers['x-api-key'] = API_KEY
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorBody = await response.text().catch(() => 'Unknown error')
    throw new OcrApiError(
      `API error: ${response.statusText}`,
      response.status,
      errorBody
    )
  }

  return response
}

/**
 * OCR a single page image
 */
export async function ocrImage(
  pageBlob: Blob,
  options: OcrImageOptions = {}
): Promise<OcrPage> {
  const formData = new FormData()
  formData.append('image', pageBlob, 'page.png')
  
  if (options.docType) formData.append('doc_type', options.docType)
  if (options.languageHint) formData.append('language', options.languageHint)
  if (options.returnLayout !== undefined) {
    formData.append('return_layout', String(options.returnLayout))
  }
  if (options.returnWords !== undefined) {
    formData.append('return_words', String(options.returnWords))
  }

  const response = await fetchWithAuth('/v1/ocr/image', {
    method: 'POST',
    body: formData,
  })

  const result = await response.json()
  
  // Add pageIndex to result
  return {
    ...result,
    pageIndex: options.pageIndex ?? 0,
  }
}

/**
 * Parse semantic content (entities, fields, doc classification)
 */
export async function parseSemantic(
  payload: ParseSemanticPayload
): Promise<SemanticResults> {
  const response = await fetchWithAuth('/v1/parse/semantic', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return response.json()
}

/**
 * Match extracted fields to a form schema
 */
export async function formsMatch(
  payload: FormsMatchPayload
): Promise<FormMapping> {
  const response = await fetchWithAuth('/v1/forms/match', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return response.json()
}

/**
 * Start a batch OCR job for multiple pages
 */
export async function startBatchJob(
  pages: Blob[],
  options: Omit<OcrImageOptions, 'pageIndex'> = {}
): Promise<BatchJobResponse> {
  const formData = new FormData()
  
  pages.forEach((blob, index) => {
    formData.append('images', blob, `page-${index}.png`)
  })
  
  if (options.docType) formData.append('doc_type', options.docType)
  if (options.languageHint) formData.append('language', options.languageHint)
  if (options.returnLayout !== undefined) {
    formData.append('return_layout', String(options.returnLayout))
  }
  if (options.returnWords !== undefined) {
    formData.append('return_words', String(options.returnWords))
  }

  const response = await fetchWithAuth('/v1/ocr/batch', {
    method: 'POST',
    body: formData,
  })

  return response.json()
}

/**
 * Stream OCR results from a batch job via SSE
 */
export function streamBatchResults(
  jobId: string,
  onPage: (result: StreamPageResult) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  const url = `${BASE_URL}/v1/ocr/stream/${jobId}`
  const headers: HeadersInit = {}
  
  if (API_KEY) {
    headers['x-api-key'] = API_KEY
  }

  const eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      if (data.status === 'complete' && data.pageIndex === undefined) {
        // Job complete
        onComplete()
        eventSource.close()
      } else if (data.pageIndex !== undefined) {
        // Page result
        onPage(data)
      }
    } catch (err) {
      onError(err instanceof Error ? err : new Error('Parse error'))
    }
  }

  eventSource.onerror = (err) => {
    onError(new Error('SSE connection failed'))
    eventSource.close()
  }

  // Return cleanup function
  return () => eventSource.close()
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; timestamp: string }> {
  const response = await fetchWithAuth('/v1/health')
  return response.json()
}

export { OcrApiError }

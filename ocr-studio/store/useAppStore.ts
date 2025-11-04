import { create } from 'zustand'

// Core types
export type OcrWord = {
  id: string
  text: string
  bbox: [number, number, number, number] // normalized [x1, y1, x2, y2] 0..1
  conf: number
  page: number
}

export type OcrLine = {
  id: string
  text: string
  bbox: [number, number, number, number]
  conf: number
  wordIds: string[]
  page: number
}

export type OcrBlock = {
  id: string
  text: string
  bbox: [number, number, number, number]
  type?: 'text' | 'title' | 'list' | 'table'
  conf: number
  lineIds: string[]
  page: number
}

export type OcrPage = {
  pageIndex: number
  width: number
  height: number
  words: OcrWord[]
  lines: OcrLine[]
  blocks: OcrBlock[]
  text: string
  language?: string
  timeMs?: number
}

export type OcrResults = {
  pages: OcrPage[]
  language?: string
  engine?: string
  timeMs?: number
}

export type EntityType =
  | 'person'
  | 'organization'
  | 'location'
  | 'date'
  | 'email'
  | 'phone'
  | 'ssn'
  | 'passport'
  | 'money'
  | 'percent'
  | 'url'

export type Entity = {
  type: EntityType
  value: string
  normalized?: string
  conf: number
  source?: {
    page: number
    wordIds: string[]
  }
}

export type SemanticField = {
  key: string
  value: string
  conf: number
  source?: {
    page: number
    wordIds: string[]
  }
}

export type SemanticResults = {
  detectedDocType: {
    type: string
    score: number
  }
  entities: Entity[]
  fields: Record<string, SemanticField>
}

export type FormMapping = {
  formId: string
  mapping: {
    formField: string
    sourceField: string
    confidence: number
  }[]
  unmapped: string[]
}

export type PageImage = {
  pageIndex: number
  blob: Blob
  url: string
  w: number
  h: number
  included: boolean // user can exclude pages
}

export type ProcessingStatus = 
  | 'idle'
  | 'rendering'
  | 'ocr'
  | 'parsing'
  | 'mapping'
  | 'complete'
  | 'error'

export type PageStatus = {
  pageIndex: number
  status: 'pending' | 'processing' | 'complete' | 'error'
  progress: number
  error?: string
  timeMs?: number
}

// Store state interface
interface AppState {
  // Upload state
  files: File[]
  pageImages: PageImage[]
  
  // Processing state
  processingStatus: ProcessingStatus
  pageStatuses: PageStatus[]
  currentJobId: string | null
  
  // Results
  ocr: OcrResults | null
  semantic: SemanticResults | null
  mapping: FormMapping | null
  
  // UI state
  selectedFormId: string | null
  selectedWordIds: string[]
  languageHint: string
  
  // Actions
  setFiles: (files: File[]) => void
  setPageImages: (pages: PageImage[]) => void
  togglePageIncluded: (pageIndex: number) => void
  setProcessingStatus: (status: ProcessingStatus) => void
  setPageStatus: (pageIndex: number, status: Partial<PageStatus>) => void
  setOcr: (ocr: OcrResults) => void
  setSemantic: (semantic: SemanticResults) => void
  setMapping: (mapping: FormMapping | null) => void
  setSelectedFormId: (formId: string | null) => void
  setSelectedWordIds: (wordIds: string[]) => void
  setLanguageHint: (hint: string) => void
  setCurrentJobId: (jobId: string | null) => void
  updateField: (key: string, value: string) => void
  reset: () => void
}

const initialState = {
  files: [],
  pageImages: [],
  processingStatus: 'idle' as ProcessingStatus,
  pageStatuses: [],
  currentJobId: null,
  ocr: null,
  semantic: null,
  mapping: null,
  selectedFormId: null,
  selectedWordIds: [],
  languageHint: 'en',
}

export const useAppStore = create<AppState>((set, get) => ({
  ...initialState,

  setFiles: (files) => set({ files }),
  
  setPageImages: (pages) => 
    set({ 
      pageImages: pages,
      pageStatuses: pages.map(p => ({
        pageIndex: p.pageIndex,
        status: 'pending' as const,
        progress: 0,
      }))
    }),

  togglePageIncluded: (pageIndex) =>
    set((state) => ({
      pageImages: state.pageImages.map((p) =>
        p.pageIndex === pageIndex ? { ...p, included: !p.included } : p
      ),
    })),

  setProcessingStatus: (status) => set({ processingStatus: status }),

  setPageStatus: (pageIndex, statusUpdate) =>
    set((state) => ({
      pageStatuses: state.pageStatuses.map((s) =>
        s.pageIndex === pageIndex ? { ...s, ...statusUpdate } : s
      ),
    })),

  setOcr: (ocr) => set({ ocr }),

  setSemantic: (semantic) => set({ semantic }),

  setMapping: (mapping) => set({ mapping }),

  setSelectedFormId: (formId) => set({ selectedFormId: formId }),

  setSelectedWordIds: (wordIds) => set({ selectedWordIds: wordIds }),

  setLanguageHint: (hint) => set({ languageHint: hint }),

  setCurrentJobId: (jobId) => set({ currentJobId: jobId }),

  updateField: (key, value) =>
    set((state) => {
      if (!state.semantic) return state
      return {
        semantic: {
          ...state.semantic,
          fields: {
            ...state.semantic.fields,
            [key]: {
              ...state.semantic.fields[key],
              value,
            },
          },
        },
      }
    }),

  reset: () => {
    // Revoke object URLs to prevent memory leaks
    const { pageImages } = get()
    pageImages.forEach((p) => URL.revokeObjectURL(p.url))
    set(initialState)
  },
}))

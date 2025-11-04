/**
 * PDF processing utilities using PDF.js
 */

import * as pdfjsLib from 'pdfjs-dist'
import type { PageImage } from '@/store/useAppStore'

// Configure PDF.js worker - use local worker served by Next.js
if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'
}

const PDF_SCALE = parseFloat(process.env.NEXT_PUBLIC_PDF_SCALE || '2.0')
const MAX_PAGE_EDGE = parseInt(process.env.NEXT_PUBLIC_MAX_PAGE_EDGE || '1800', 10)

export interface PdfRenderOptions {
  scale?: number
  maxEdge?: number
}

/**
 * Render a PDF file to page images
 */
export async function renderPdfToImages(
  file: File,
  options: PdfRenderOptions = {},
  onProgress?: (current: number, total: number) => void
): Promise<PageImage[]> {
  const { scale = PDF_SCALE, maxEdge = MAX_PAGE_EDGE } = options

  // Load PDF
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise

  const totalPages = pdf.numPages
  const pageImages: PageImage[] = []

  for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
    const page = await pdf.getPage(pageNum)
    const viewport = page.getViewport({ scale })

    // Calculate scaling to respect max edge
    let finalScale = scale
    const longestEdge = Math.max(viewport.width, viewport.height)
    if (longestEdge > maxEdge) {
      finalScale = (maxEdge / longestEdge) * scale
    }

    const finalViewport = page.getViewport({ scale: finalScale })

    // Create canvas
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Could not get 2D context')

    canvas.width = finalViewport.width
    canvas.height = finalViewport.height

    // Render PDF page to canvas
    const renderContext = {
      canvasContext: context,
      viewport: finalViewport,
    }

    await page.render(renderContext).promise

    // Convert canvas to blob
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (b) => {
          if (b) resolve(b)
          else reject(new Error('Failed to create blob'))
        },
        'image/png',
        0.92
      )
    })

    const url = URL.createObjectURL(blob)

    pageImages.push({
      pageIndex: pageNum - 1,
      blob,
      url,
      w: canvas.width,
      h: canvas.height,
      included: true, // default to included
    })

    // Cleanup
    page.cleanup()

    // Report progress
    if (onProgress) {
      onProgress(pageNum, totalPages)
    }
  }

  return pageImages
}

/**
 * Get PDF metadata
 */
export async function getPdfMetadata(file: File): Promise<{
  numPages: number
  title?: string
  author?: string
  creationDate?: Date
}> {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const metadata = await pdf.getMetadata()

  return {
    numPages: pdf.numPages,
    title: metadata.info?.Title,
    author: metadata.info?.Author,
    creationDate: metadata.info?.CreationDate
      ? new Date(metadata.info.CreationDate)
      : undefined,
  }
}

/**
 * Render a single page to canvas for preview
 */
export async function renderPageToCanvas(
  file: File,
  pageIndex: number,
  canvas: HTMLCanvasElement,
  scale: number = 1.5
): Promise<{ width: number; height: number }> {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const page = await pdf.getPage(pageIndex + 1)
  const viewport = page.getViewport({ scale })

  const context = canvas.getContext('2d')
  if (!context) throw new Error('Could not get 2D context')

  canvas.width = viewport.width
  canvas.height = viewport.height

  await page.render({
    canvasContext: context,
    viewport,
  }).promise

  page.cleanup()

  return {
    width: viewport.width,
    height: viewport.height,
  }
}

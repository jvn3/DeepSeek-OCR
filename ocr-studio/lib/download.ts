/**
 * Download utilities for exporting results
 */

import type { OcrResults, SemanticResults, FormMapping } from '@/store/useAppStore'
import { PDFDocument, rgb } from 'pdf-lib'

/**
 * Download results as JSON
 */
export function downloadJson(
  ocr: OcrResults | null,
  semantic: SemanticResults | null,
  mapping: FormMapping | null,
  filename: string = 'ocr-results.json'
): void {
  const data = {
    timestamp: new Date().toISOString(),
    detectedDocType: semantic?.detectedDocType,
    pages: ocr?.pages,
    entities: semantic?.entities,
    fields: semantic?.fields,
    formMapping: mapping,
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })

  downloadBlob(blob, filename)
}

/**
 * Export fields as CSV
 */
export function downloadCsv(
  semantic: SemanticResults | null,
  filename: string = 'ocr-fields.csv'
): void {
  if (!semantic || !semantic.fields) {
    throw new Error('No fields to export')
  }

  const headers = ['Field', 'Value', 'Confidence', 'Page', 'Word IDs']
  const rows = Object.entries(semantic.fields).map(([key, field]) => [
    key,
    field.value,
    field.conf.toFixed(3),
    field.source?.page?.toString() || '',
    field.source?.wordIds?.join(';') || '',
  ])

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell}"`).join(','))
    .join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv' })
  downloadBlob(blob, filename)
}

/**
 * Copy fields to clipboard as JSON
 */
export async function copyFieldsAsJson(
  semantic: SemanticResults | null
): Promise<void> {
  if (!semantic || !semantic.fields) {
    throw new Error('No fields to copy')
  }

  await navigator.clipboard.writeText(JSON.stringify(semantic.fields, null, 2))
}

/**
 * Copy text content to clipboard
 */
export async function copyTextContent(ocr: OcrResults | null): Promise<void> {
  if (!ocr || !ocr.pages) {
    throw new Error('No text to copy')
  }

  const text = ocr.pages.map((p) => p.text).join('\n\n')
  await navigator.clipboard.writeText(text)
}

/**
 * Generate a filled PDF with field values
 * This is a simplified implementation - production would use form field annotations
 */
export async function generateFilledPdf(
  originalFile: File | null,
  semantic: SemanticResults | null,
  mapping: FormMapping | null
): Promise<Blob> {
  if (!semantic || !mapping) {
    throw new Error('No mapping available')
  }

  // Create a new PDF
  const pdfDoc = await PDFDocument.create()
  
  // If we have an original PDF, we could load and annotate it
  // For now, create a simple text-based PDF
  const page = pdfDoc.addPage([612, 792]) // Letter size
  const { height } = page.getSize()
  
  let y = height - 50

  // Title
  page.drawText(mapping.formId, {
    x: 50,
    y,
    size: 16,
    color: rgb(0, 0, 0),
  })

  y -= 40

  // Draw each mapped field
  for (const mapItem of mapping.mapping) {
    const field = semantic.fields[mapItem.sourceField]
    if (!field) continue

    page.drawText(`${mapItem.formField}:`, {
      x: 50,
      y,
      size: 11,
      color: rgb(0.2, 0.2, 0.2),
    })

    page.drawText(field.value, {
      x: 250,
      y,
      size: 11,
      color: rgb(0, 0, 0),
    })

    y -= 20

    if (y < 50) {
      // Add new page if needed
      const newPage = pdfDoc.addPage([612, 792])
      y = newPage.getSize().height - 50
    }
  }

  const pdfBytes = await pdfDoc.save()
  return new Blob([pdfBytes], { type: 'application/pdf' })
}

/**
 * Download a blob as a file
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

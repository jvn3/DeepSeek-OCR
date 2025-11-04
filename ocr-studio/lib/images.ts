/**
 * Image processing utilities
 */

import type { PageImage } from '@/store/useAppStore'

const MAX_PAGE_EDGE = parseInt(process.env.NEXT_PUBLIC_MAX_PAGE_EDGE || '1800', 10)

export interface ImageProcessOptions {
  maxEdge?: number
  quality?: number
  correctOrientation?: boolean
}

/**
 * Process an image file to a normalized PageImage
 */
export async function processImage(
  file: File,
  pageIndex: number = 0,
  options: ImageProcessOptions = {}
): Promise<PageImage> {
  const { maxEdge = MAX_PAGE_EDGE, quality = 0.92, correctOrientation = true } = options

  // Load image
  const bitmap = await createImageBitmap(file)
  
  // Get EXIF orientation if needed
  let orientation = 1
  if (correctOrientation) {
    orientation = await getImageOrientation(file)
  }

  // Create canvas
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Could not get 2D context')

  // Calculate dimensions respecting orientation
  let { width, height } = bitmap
  
  // Apply orientation transforms
  const needsRotation = orientation >= 5 && orientation <= 8
  if (needsRotation) {
    [width, height] = [height, width]
  }

  // Scale down if needed
  const longestEdge = Math.max(width, height)
  let scale = 1
  if (longestEdge > maxEdge) {
    scale = maxEdge / longestEdge
  }

  const finalWidth = Math.round(width * scale)
  const finalHeight = Math.round(height * scale)

  canvas.width = finalWidth
  canvas.height = finalHeight

  // Apply orientation transformation
  ctx.save()
  applyOrientation(ctx, orientation, finalWidth, finalHeight)
  ctx.drawImage(bitmap, 0, 0, finalWidth, finalHeight)
  ctx.restore()

  // Convert to blob
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (b) => {
        if (b) resolve(b)
        else reject(new Error('Failed to create blob'))
      },
      'image/png',
      quality
    )
  })

  const url = URL.createObjectURL(blob)

  bitmap.close()

  return {
    pageIndex,
    blob,
    url,
    w: finalWidth,
    h: finalHeight,
    included: true,
  }
}

/**
 * Process multiple images
 */
export async function processImages(
  files: File[],
  options: ImageProcessOptions = {},
  onProgress?: (current: number, total: number) => void
): Promise<PageImage[]> {
  const results: PageImage[] = []

  for (let i = 0; i < files.length; i++) {
    const pageImage = await processImage(files[i], i, options)
    results.push(pageImage)
    
    if (onProgress) {
      onProgress(i + 1, files.length)
    }
  }

  return results
}

/**
 * Get EXIF orientation from image file
 */
async function getImageOrientation(file: File): Promise<number> {
  return new Promise((resolve) => {
    const reader = new FileReader()
    
    reader.onload = (e) => {
      const view = new DataView(e.target?.result as ArrayBuffer)
      
      if (view.getUint16(0, false) !== 0xffd8) {
        resolve(1) // Not a JPEG
        return
      }

      const length = view.byteLength
      let offset = 2

      while (offset < length) {
        const marker = view.getUint16(offset, false)
        offset += 2

        if (marker === 0xffe1) {
          // EXIF marker
          offset += 2
          if (view.getUint32(offset, false) !== 0x45786966) {
            resolve(1)
            return
          }

          const little = view.getUint16((offset += 6), false) === 0x4949
          offset += view.getUint32(offset + 4, little)
          const tags = view.getUint16(offset, little)
          offset += 2

          for (let i = 0; i < tags; i++) {
            if (view.getUint16(offset + i * 12, little) === 0x0112) {
              const orientation = view.getUint16(offset + i * 12 + 8, little)
              resolve(orientation)
              return
            }
          }
        } else if ((marker & 0xff00) !== 0xff00) {
          break
        } else {
          offset += view.getUint16(offset, false)
        }
      }

      resolve(1)
    }

    reader.readAsArrayBuffer(file.slice(0, 64 * 1024))
  })
}

/**
 * Apply EXIF orientation transformation to canvas context
 */
function applyOrientation(
  ctx: CanvasRenderingContext2D,
  orientation: number,
  width: number,
  height: number
): void {
  switch (orientation) {
    case 2:
      ctx.transform(-1, 0, 0, 1, width, 0)
      break
    case 3:
      ctx.transform(-1, 0, 0, -1, width, height)
      break
    case 4:
      ctx.transform(1, 0, 0, -1, 0, height)
      break
    case 5:
      ctx.transform(0, 1, 1, 0, 0, 0)
      break
    case 6:
      ctx.transform(0, 1, -1, 0, height, 0)
      break
    case 7:
      ctx.transform(0, -1, -1, 0, height, width)
      break
    case 8:
      ctx.transform(0, -1, 1, 0, 0, width)
      break
    default:
      break
  }
}

/**
 * Create thumbnail from PageImage
 */
export async function createThumbnail(
  pageImage: PageImage,
  maxSize: number = 200
): Promise<string> {
  const bitmap = await createImageBitmap(pageImage.blob)
  
  const scale = Math.min(maxSize / pageImage.w, maxSize / pageImage.h)
  const thumbWidth = Math.round(pageImage.w * scale)
  const thumbHeight = Math.round(pageImage.h * scale)

  const canvas = document.createElement('canvas')
  canvas.width = thumbWidth
  canvas.height = thumbHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Could not get 2D context')

  ctx.drawImage(bitmap, 0, 0, thumbWidth, thumbHeight)
  bitmap.close()

  return canvas.toDataURL('image/jpeg', 0.8)
}

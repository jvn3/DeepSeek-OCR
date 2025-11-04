/**
 * Utilities for working with bounding boxes
 */

export type BBox = [number, number, number, number] // [x1, y1, x2, y2]

/**
 * Convert normalized bbox (0..1) to pixel coordinates
 */
export function bboxToPixels(
  bbox: BBox,
  pageWidth: number,
  pageHeight: number
): BBox {
  const [x1, y1, x2, y2] = bbox
  return [
    x1 * pageWidth,
    y1 * pageHeight,
    x2 * pageWidth,
    y2 * pageHeight,
  ]
}

/**
 * Convert pixel bbox to normalized (0..1)
 */
export function bboxToNormalized(
  bbox: BBox,
  pageWidth: number,
  pageHeight: number
): BBox {
  const [x1, y1, x2, y2] = bbox
  return [
    x1 / pageWidth,
    y1 / pageHeight,
    x2 / pageWidth,
    y2 / pageHeight,
  ]
}

/**
 * Check if a point is inside a bounding box
 */
export function isPointInBBox(
  x: number,
  y: number,
  bbox: BBox
): boolean {
  const [x1, y1, x2, y2] = bbox
  return x >= x1 && x <= x2 && y >= y1 && y <= y2
}

/**
 * Calculate IoU (Intersection over Union) between two bboxes
 */
export function calculateIoU(bbox1: BBox, bbox2: BBox): number {
  const [x1a, y1a, x2a, y2a] = bbox1
  const [x1b, y1b, x2b, y2b] = bbox2

  const xLeft = Math.max(x1a, x1b)
  const yTop = Math.max(y1a, y1b)
  const xRight = Math.min(x2a, x2b)
  const yBottom = Math.min(y2a, y2b)

  if (xRight < xLeft || yBottom < yTop) {
    return 0
  }

  const intersectionArea = (xRight - xLeft) * (yBottom - yTop)
  const bbox1Area = (x2a - x1a) * (y2a - y1a)
  const bbox2Area = (x2b - x1b) * (y2b - y1b)
  const unionArea = bbox1Area + bbox2Area - intersectionArea

  return intersectionArea / unionArea
}

/**
 * Merge multiple bboxes into one
 */
export function mergeBBoxes(bboxes: BBox[]): BBox {
  if (bboxes.length === 0) {
    return [0, 0, 0, 0]
  }

  const x1 = Math.min(...bboxes.map((b) => b[0]))
  const y1 = Math.min(...bboxes.map((b) => b[1]))
  const x2 = Math.max(...bboxes.map((b) => b[2]))
  const y2 = Math.max(...bboxes.map((b) => b[3]))

  return [x1, y1, x2, y2]
}

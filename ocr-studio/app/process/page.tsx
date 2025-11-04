'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ProgressBar } from '@/components/ProgressBar'
import { useAppStore } from '@/store/useAppStore'
import { ocrImage, parseSemantic } from '@/lib/ocrClient'
import { useToast } from '@/hooks/use-toast'

const CONCURRENCY = parseInt(process.env.NEXT_PUBLIC_CONCURRENCY || '3', 10)

export default function ProcessPage() {
  const router = useRouter()
  const { toast } = useToast()
  const {
    pageImages,
    setProcessingStatus,
    setPageStatus,
    setOcr,
    setSemantic,
    languageHint,
  } = useAppStore()
  const [isProcessing, setIsProcessing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    const includedPages = pageImages.filter(p => p.included)
    
    if (includedPages.length === 0) {
      router.push('/import')
      return
    }

    // Auto-start processing
    startProcessing()
  }, [])

  const startProcessing = async () => {
    setIsProcessing(true)
    setProcessingStatus('ocr')

    const includedPages = pageImages.filter(p => p.included)
    const allOcrPages: any[] = []

    try {
      // Process pages with concurrency limit
      for (let i = 0; i < includedPages.length; i += CONCURRENCY) {
        const batch = includedPages.slice(i, i + CONCURRENCY)
        
        const batchPromises = batch.map(async (page) => {
          setPageStatus(page.pageIndex, { status: 'processing', progress: 0 })
          
          const startTime = Date.now()
          
          try {
            const ocrResult = await ocrImage(page.blob, {
              languageHint,
              returnLayout: true,
              returnWords: true,
              pageIndex: page.pageIndex,
            })

            const timeMs = Date.now() - startTime

            setPageStatus(page.pageIndex, {
              status: 'complete',
              progress: 100,
              timeMs,
            })

            return {
              ...ocrResult,
              pageIndex: page.pageIndex,
              width: page.w,
              height: page.h,
            }
          } catch (error) {
            console.error(`Failed to OCR page ${page.pageIndex}:`, error)
            
            setPageStatus(page.pageIndex, {
              status: 'error',
              progress: 0,
              error: error instanceof Error ? error.message : 'OCR failed',
            })

            return null
          }
        })

        const batchResults = await Promise.all(batchPromises)
        allOcrPages.push(...batchResults.filter(Boolean))
      }

      // Store OCR results
      const ocrResults = {
        pages: allOcrPages,
        language: languageHint,
        engine: 'deepseek-ocr',
        timeMs: allOcrPages.reduce((sum, p) => sum + (p.timeMs || 0), 0),
      }

      setOcr(ocrResults)

      // Parse semantic content
      setProcessingStatus('parsing')
      
      const combinedText = allOcrPages.map(p => p.text).join('\n\n')
      const combinedLayout = {
        blocks: allOcrPages.flatMap(p => p.blocks || []),
        lines: allOcrPages.flatMap(p => p.lines || []),
        words: allOcrPages.flatMap(p => p.words || []),
      }

      const semanticResults = await parseSemantic({
        text: combinedText,
        layout: combinedLayout,
        hints: {
          country: 'US',
          dateFormat: 'YYYY-MM-DD',
        },
      })

      setSemantic(semanticResults)
      setProcessingStatus('complete')
      setIsComplete(true)

      toast({
        title: 'Processing complete!',
        description: `Successfully processed ${allOcrPages.length} page${allOcrPages.length !== 1 ? 's' : ''}`,
      })

      // Auto-navigate to review after 2 seconds
      setTimeout(() => {
        router.push('/review')
      }, 2000)

    } catch (error) {
      console.error('Processing failed:', error)
      
      toast({
        title: 'Processing failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })

      setProcessingStatus('error')
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Button variant="ghost" asChild disabled={isProcessing}>
              <Link href="/import">
                <ArrowLeft className="mr-2 w-4 h-4" />
                Back
              </Link>
            </Button>
            <h1 className="text-xl font-semibold">Processing OCR</h1>
            <div className="w-24" /> {/* Spacer */}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>
                {isProcessing ? 'Processing...' : isComplete ? 'Complete!' : 'Ready'}
              </CardTitle>
              <CardDescription>
                {isProcessing
                  ? 'Running OCR and extracting text, layout, and entities'
                  : isComplete
                  ? 'All pages processed successfully'
                  : 'Preparing to process'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ProgressBar />
            </CardContent>
          </Card>

          {/* Complete Actions */}
          {isComplete && (
            <Card className="border-green-500 bg-green-50 dark:bg-green-950">
              <CardHeader>
                <div className="flex items-center">
                  <CheckCircle2 className="w-6 h-6 text-green-500 mr-2" />
                  <CardTitle>Processing Complete</CardTitle>
                </div>
                <CardDescription className="text-green-700 dark:text-green-300">
                  Your documents have been processed. Review the results to verify accuracy.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild>
                  <Link href="/review">
                    View Results
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Processing Info */}
          <Card>
            <CardHeader>
              <CardTitle>Processing Steps</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-3 text-sm">
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs mr-3">
                    1
                  </span>
                  <div>
                    <div className="font-medium">OCR Processing</div>
                    <div className="text-muted-foreground">
                      Extract text, words, lines, and blocks from each page
                    </div>
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs mr-3">
                    2
                  </span>
                  <div>
                    <div className="font-medium">Semantic Analysis</div>
                    <div className="text-muted-foreground">
                      Detect document type and extract entities (names, dates, emails, etc.)
                    </div>
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs mr-3">
                    3
                  </span>
                  <div>
                    <div className="font-medium">Field Extraction</div>
                    <div className="text-muted-foreground">
                      Extract structured fields with confidence scores and provenance
                    </div>
                  </div>
                </li>
              </ol>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

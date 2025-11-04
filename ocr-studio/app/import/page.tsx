'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, ArrowRight, Settings2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAppStore } from '@/store/useAppStore'
import { renderPdfToImages } from '@/lib/pdf'
import { processImages } from '@/lib/images'
import { useToast } from '@/hooks/use-toast'

export default function ImportPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { files, pageImages, setPageImages, togglePageIncluded, languageHint, setLanguageHint, setProcessingStatus } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (files.length === 0) {
      router.push('/')
      return
    }

    // Process files on mount
    processFiles()
  }, [files])

  const processFiles = async () => {
    if (pageImages.length > 0) return // Already processed

    setLoading(true)
    setProcessingStatus('rendering')

    try {
      const allPageImages = []

      for (const file of files) {
        if (file.type === 'application/pdf') {
          // Render PDF to images
          const pdfImages = await renderPdfToImages(
            file,
            {},
            (current, total) => {
              setProgress(Math.round((current / total) * 100))
            }
          )
          allPageImages.push(...pdfImages)
        } else {
          // Process image files
          const imagePages = await processImages(
            [file],
            {},
            (current, total) => {
              setProgress(Math.round((current / total) * 100))
            }
          )
          allPageImages.push(...imagePages)
        }
      }

      setPageImages(allPageImages)
      setProcessingStatus('idle')
      
      toast({
        title: 'Pages loaded',
        description: `${allPageImages.length} page${allPageImages.length !== 1 ? 's' : ''} ready to process`,
      })
    } catch (error) {
      console.error('Failed to process files:', error)
      toast({
        title: 'Processing failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
      setProcessingStatus('idle')
    } finally {
      setLoading(false)
    }
  }

  const handleProcess = () => {
    const includedPages = pageImages.filter(p => p.included)
    
    if (includedPages.length === 0) {
      toast({
        title: 'No pages selected',
        description: 'Please include at least one page to process',
        variant: 'destructive',
      })
      return
    }

    router.push('/process')
  }

  const includedCount = pageImages.filter(p => p.included).length

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Button variant="ghost" asChild>
              <Link href="/">
                <ArrowLeft className="mr-2 w-4 h-4" />
                Back
              </Link>
            </Button>
            <h1 className="text-xl font-semibold">Import & Preview</h1>
            <div className="w-24" /> {/* Spacer */}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {loading ? (
          <Card>
            <CardHeader>
              <CardTitle>Processing Files...</CardTitle>
              <CardDescription>
                Rendering pages and preparing for OCR
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between text-sm">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Settings2 className="w-5 h-5 mr-2" />
                  Processing Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Language Hint</label>
                    <Input
                      value={languageHint}
                      onChange={(e) => setLanguageHint(e.target.value)}
                      placeholder="en"
                      className="max-w-xs"
                    />
                    <p className="text-xs text-muted-foreground">
                      ISO 639-1 code (en, es, fr, etc.)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Page Grid */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Pages</CardTitle>
                    <CardDescription>
                      {includedCount} of {pageImages.length} page{pageImages.length !== 1 ? 's' : ''} selected for processing
                    </CardDescription>
                  </div>
                  <Button
                    onClick={handleProcess}
                    disabled={includedCount === 0}
                  >
                    Process {includedCount} Page{includedCount !== 1 ? 's' : ''}
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {pageImages.map((page, index) => (
                    <div
                      key={page.pageIndex}
                      className={`relative group border-2 rounded-lg overflow-hidden transition-all ${
                        page.included
                          ? 'border-primary shadow-md'
                          : 'border-muted opacity-50'
                      }`}
                    >
                      {/* Thumbnail */}
                      <div className="aspect-[3/4] bg-muted relative">
                        <img
                          src={page.url}
                          alt={`Page ${page.pageIndex + 1}`}
                          className="w-full h-full object-contain"
                        />
                        {!page.included && (
                          <div className="absolute inset-0 bg-background/50 flex items-center justify-center">
                            <span className="text-sm font-medium text-muted-foreground">
                              Excluded
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Controls */}
                      <div className="p-2 bg-background border-t">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium">
                            Page {page.pageIndex + 1}
                          </span>
                          <button
                            onClick={() => togglePageIncluded(page.pageIndex)}
                            className={`text-xs px-2 py-1 rounded ${
                              page.included
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted text-muted-foreground'
                            }`}
                          >
                            {page.included ? 'Included' : 'Excluded'}
                          </button>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {page.w} × {page.h}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  )
}

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Download, FileJson, FileSpreadsheet, FileText, Copy, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAppStore } from '@/store/useAppStore'
import { downloadJson, downloadCsv, copyFieldsAsJson, copyTextContent } from '@/lib/download'
import { useToast } from '@/hooks/use-toast'

export default function ExportPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { ocr, semantic, mapping, reset } = useAppStore()

  useEffect(() => {
    if (!ocr || !semantic) {
      router.push('/import')
    }
  }, [ocr, semantic])

  if (!ocr || !semantic) {
    return null
  }

  const handleDownloadJson = () => {
    try {
      downloadJson(ocr, semantic, mapping)
      toast({
        title: 'Downloaded',
        description: 'Results saved as JSON',
      })
    } catch (error) {
      toast({
        title: 'Export failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    }
  }

  const handleDownloadCsv = () => {
    try {
      downloadCsv(semantic)
      toast({
        title: 'Downloaded',
        description: 'Fields saved as CSV',
      })
    } catch (error) {
      toast({
        title: 'Export failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    }
  }

  const handleCopyJson = async () => {
    try {
      await copyFieldsAsJson(semantic)
      toast({
        title: 'Copied',
        description: 'Fields copied to clipboard as JSON',
      })
    } catch (error) {
      toast({
        title: 'Copy failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    }
  }

  const handleCopyText = async () => {
    try {
      await copyTextContent(ocr)
      toast({
        title: 'Copied',
        description: 'Text content copied to clipboard',
      })
    } catch (error) {
      toast({
        title: 'Copy failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    }
  }

  const handleStartOver = () => {
    reset()
    router.push('/')
  }

  const fieldCount = Object.keys(semantic.fields).length
  const entityCount = semantic.entities.length
  const pageCount = ocr.pages.length

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Button variant="ghost" asChild>
              <Link href="/review">
                <ArrowLeft className="mr-2 w-4 h-4" />
                Back to Review
              </Link>
            </Button>
            <h1 className="text-xl font-semibold">Export Results</h1>
            <div className="w-32" /> {/* Spacer */}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="space-y-6">
          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Processing Summary</CardTitle>
              <CardDescription>
                Overview of extracted data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">{pageCount}</div>
                  <div className="text-sm text-muted-foreground">
                    Page{pageCount !== 1 ? 's' : ''}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">{fieldCount}</div>
                  <div className="text-sm text-muted-foreground">
                    Field{fieldCount !== 1 ? 's' : ''}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">{entityCount}</div>
                  <div className="text-sm text-muted-foreground">
                    Entit{entityCount !== 1 ? 'ies' : 'y'}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">{semantic.detectedDocType.type}</div>
                  <div className="text-sm text-muted-foreground">
                    Doc Type
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Download Options */}
          <Card>
            <CardHeader>
              <CardTitle>Download Files</CardTitle>
              <CardDescription>
                Export your results in various formats
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={handleDownloadJson}
                variant="outline"
                className="w-full justify-start"
              >
                <FileJson className="mr-2 w-5 h-5" />
                <div className="flex-1 text-left">
                  <div className="font-medium">Download JSON</div>
                  <div className="text-xs text-muted-foreground">
                    Complete results with pages, fields, and entities
                  </div>
                </div>
              </Button>

              <Button
                onClick={handleDownloadCsv}
                variant="outline"
                className="w-full justify-start"
              >
                <FileSpreadsheet className="mr-2 w-5 h-5" />
                <div className="flex-1 text-left">
                  <div className="font-medium">Download CSV</div>
                  <div className="text-xs text-muted-foreground">
                    Fields only in spreadsheet format
                  </div>
                </div>
              </Button>

              {mapping && (
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  disabled
                >
                  <FileText className="mr-2 w-5 h-5" />
                  <div className="flex-1 text-left">
                    <div className="font-medium">Download Filled PDF</div>
                    <div className="text-xs text-muted-foreground">
                      Form with mapped fields (coming soon)
                    </div>
                  </div>
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Copy Options */}
          <Card>
            <CardHeader>
              <CardTitle>Copy to Clipboard</CardTitle>
              <CardDescription>
                Quick copy for pasting elsewhere
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={handleCopyJson}
                variant="outline"
                className="w-full justify-start"
              >
                <Copy className="mr-2 w-5 h-5" />
                <div className="flex-1 text-left">
                  <div className="font-medium">Copy Fields as JSON</div>
                  <div className="text-xs text-muted-foreground">
                    Structured field data
                  </div>
                </div>
              </Button>

              <Button
                onClick={handleCopyText}
                variant="outline"
                className="w-full justify-start"
              >
                <Copy className="mr-2 w-5 h-5" />
                <div className="flex-1 text-left">
                  <div className="font-medium">Copy Text Content</div>
                  <div className="text-xs text-muted-foreground">
                    Plain text from all pages
                  </div>
                </div>
              </Button>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>What's Next?</CardTitle>
              <CardDescription>
                Process another document or return home
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={handleStartOver}
                className="w-full"
              >
                <Home className="mr-2 w-4 h-4" />
                Process Another Document
              </Button>

              <Button variant="outline" asChild className="w-full">
                <Link href="/review">
                  Back to Review
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

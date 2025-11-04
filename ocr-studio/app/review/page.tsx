'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, ArrowRight, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { useAppStore } from '@/store/useAppStore'
import { useToast } from '@/hooks/use-toast'

export default function ReviewPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { ocr, semantic, updateField } = useAppStore()

  useEffect(() => {
    if (!ocr || !semantic) {
      router.push('/import')
    }
  }, [ocr, semantic])

  if (!ocr || !semantic) {
    return null
  }

  const sortedFields = Object.entries(semantic.fields).sort((a, b) => {
    return b[1].conf - a[1].conf
  })

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Button variant="ghost" asChild>
              <Link href="/process">
                <ArrowLeft className="mr-2 w-4 h-4" />
                Back
              </Link>
            </Button>
            <h1 className="text-xl font-semibold">Review Results</h1>
            <Button asChild>
              <Link href="/export">
                Export
                <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Document Info */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Document Classification</CardTitle>
                <CardDescription>
                  Detected document type and confidence
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-lg">
                      {semantic.detectedDocType.type}
                    </span>
                    <span className="text-sm px-2 py-1 rounded bg-primary/10 text-primary">
                      {(semantic.detectedDocType.score * 100).toFixed(1)}% confidence
                    </span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {ocr.pages.length} page{ocr.pages.length !== 1 ? 's' : ''} • {ocr.timeMs}ms
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Extracted Text</CardTitle>
                <CardDescription>
                  Full text content from all pages
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="max-h-96 overflow-y-auto custom-scrollbar">
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {ocr.pages.map(p => p.text).join('\n\n')}
                  </pre>
                </div>
              </CardContent>
            </Card>

            {semantic.entities.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Entities ({semantic.entities.length})</CardTitle>
                  <CardDescription>
                    Detected people, dates, organizations, etc.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {semantic.entities.slice(0, 10).map((entity, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 rounded border"
                      >
                        <div className="flex-1">
                          <div className="text-sm font-medium">{entity.value}</div>
                          <div className="text-xs text-muted-foreground">
                            {entity.type}
                            {entity.normalized && ` → ${entity.normalized}`}
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {(entity.conf * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                    {semantic.entities.length > 10 && (
                      <div className="text-sm text-muted-foreground text-center">
                        + {semantic.entities.length - 10} more entities
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right: Fields Editor */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Extracted Fields ({sortedFields.length})</CardTitle>
                <CardDescription>
                  Edit values and review confidence scores
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-[600px] overflow-y-auto custom-scrollbar">
                  {sortedFields.map(([key, field]) => (
                    <div key={key} className="space-y-2 p-3 rounded border">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium capitalize">
                          {key.replace(/_/g, ' ')}
                        </label>
                        <div className="flex items-center space-x-2">
                          <div className="text-xs text-muted-foreground">
                            {(field.conf * 100).toFixed(0)}%
                          </div>
                          <div
                            className="w-16 h-2 bg-secondary rounded-full overflow-hidden"
                            title={`Confidence: ${(field.conf * 100).toFixed(1)}%`}
                          >
                            <div
                              className={`h-full ${
                                field.conf >= 0.8
                                  ? 'bg-green-500'
                                  : field.conf >= 0.5
                                  ? 'bg-yellow-500'
                                  : 'bg-red-500'
                              }`}
                              style={{ width: `${field.conf * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                      <Input
                        value={field.value}
                        onChange={(e) => updateField(key, e.target.value)}
                        className="font-mono text-sm"
                      />
                      {field.source && (
                        <div className="text-xs text-muted-foreground">
                          Page {field.source.page + 1}
                          {field.source.wordIds && field.source.wordIds.length > 0 && (
                            <> • {field.source.wordIds.length} word{field.source.wordIds.length !== 1 ? 's' : ''}</>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
                <CardDescription>
                  Export or continue editing
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button asChild className="w-full">
                  <Link href="/export">
                    <Download className="mr-2 w-4 h-4" />
                    Export Results
                  </Link>
                </Button>
                <Button variant="outline" asChild className="w-full">
                  <Link href="/import">
                    Start Over
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}

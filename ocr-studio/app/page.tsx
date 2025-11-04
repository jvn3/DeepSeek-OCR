'use client'

import Link from 'next/link'
import { useState } from 'react'
import { FileText, Zap, Shield, Download, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Uploader } from '@/components/Uploader'
import { useAppStore } from '@/store/useAppStore'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  const { files } = useAppStore()

  const handleFilesSelected = (selectedFiles: File[]) => {
    if (selectedFiles.length > 0) {
      // Auto-navigate to import page
      setTimeout(() => router.push('/import'), 500)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="w-8 h-8 text-primary" />
              <h1 className="text-2xl font-bold">DeepSeek OCR Studio</h1>
            </div>
            <nav className="flex items-center space-x-4">
              <Button variant="ghost" asChild>
                <Link href="/import">Import</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/process">Process</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/review">Review</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/export">Export</Link>
              </Button>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-16 md:py-24">
        <div className="max-w-4xl mx-auto text-center space-y-6">
          <h2 className="text-4xl md:text-6xl font-bold tracking-tight">
            Production-Ready OCR
            <br />
            <span className="text-primary">Document Understanding</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Extract text, layout, entities, and structured fields from PDFs and images.
            Auto-map to forms. All processing client-side.
          </p>

          <div className="pt-8">
            <Uploader onFilesSelected={handleFilesSelected} />
          </div>

          <div className="flex items-center justify-center space-x-4 pt-4">
            <Button size="lg" asChild>
              <Link href="/import">
                Get Started <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" onClick={() => loadSamplePdf()}>
              Try Sample PDF
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          <Card>
            <CardHeader>
              <Zap className="w-10 h-10 text-primary mb-2" />
              <CardTitle>Lightning Fast</CardTitle>
              <CardDescription>
                Real-time OCR with SSE streaming. Process 100+ pages in minutes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2 text-muted-foreground">
                <li>• Parallel processing</li>
                <li>• Web Worker offloading</li>
                <li>• Progress tracking</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Shield className="w-10 h-10 text-primary mb-2" />
              <CardTitle>Zero Persistence</CardTitle>
              <CardDescription>
                All processing in-browser. No cloud storage. No data retention.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2 text-muted-foreground">
                <li>• Client-side only</li>
                <li>• Optional downloads</li>
                <li>• Full privacy</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Download className="w-10 h-10 text-primary mb-2" />
              <CardTitle>Smart Export</CardTitle>
              <CardDescription>
                Download as JSON, CSV, or filled PDF. Copy to clipboard with one click.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2 text-muted-foreground">
                <li>• Multiple formats</li>
                <li>• Form mapping</li>
                <li>• Structured data</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Use Cases */}
      <section className="container mx-auto px-4 py-16 bg-muted/30">
        <div className="max-w-3xl mx-auto">
          <h3 className="text-3xl font-bold text-center mb-12">Use Cases</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <UseCaseCard
              title="Immigration Forms"
              description="Auto-fill DS-160, I-9, and visa applications from passport scans"
              icon="🛂"
            />
            <UseCaseCard
              title="Tax Documents"
              description="Extract W-2, 1099, and invoice data with field validation"
              icon="💰"
            />
            <UseCaseCard
              title="Resume Parsing"
              description="Pull contact info, skills, and experience into structured JSON"
              icon="📄"
            />
            <UseCaseCard
              title="Medical Records"
              description="Digitize patient forms with HIPAA-compliant processing"
              icon="🏥"
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 py-16">
        <Card className="max-w-2xl mx-auto text-center p-8">
          <CardHeader>
            <CardTitle className="text-3xl">Ready to Process Documents?</CardTitle>
            <CardDescription className="text-lg">
              Drop a PDF above or browse your files to get started
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Supports PDF, PNG, JPEG, TIFF • Max 50MB per file • Up to 100 pages
            </p>
            <Button size="lg" asChild>
              <Link href="/import">Start Processing</Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t mt-16">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <p>© 2025 DeepSeek OCR Studio</p>
            <div className="flex space-x-4">
              <Link href="/import" className="hover:text-foreground">
                Import
              </Link>
              <Link href="/process" className="hover:text-foreground">
                Process
              </Link>
              <Link href="/review" className="hover:text-foreground">
                Review
              </Link>
              <Link href="/export" className="hover:text-foreground">
                Export
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function UseCaseCard({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <Card>
      <CardHeader>
        <div className="text-4xl mb-2">{icon}</div>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

async function loadSamplePdf() {
  try {
    const response = await fetch('/samples/sample-passport.pdf')
    const blob = await response.blob()
    const file = new File([blob], 'sample-passport.pdf', { type: 'application/pdf' })
    
    // Set in store and navigate
    const { setFiles } = useAppStore.getState()
    setFiles([file])
    window.location.href = '/import'
  } catch (err) {
    console.error('Failed to load sample:', err)
  }
}

'use client'

import { useEffect, useState } from 'react'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { useAppStore, type PageStatus } from '@/store/useAppStore'
import { CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react'

export function ProgressBar() {
  const { pageStatuses, processingStatus } = useAppStore()
  const [overallProgress, setOverallProgress] = useState(0)

  useEffect(() => {
    if (pageStatuses.length === 0) {
      setOverallProgress(0)
      return
    }

    const total = pageStatuses.reduce((sum, s) => sum + s.progress, 0)
    setOverallProgress(Math.round(total / pageStatuses.length))
  }, [pageStatuses])

  if (pageStatuses.length === 0) return null

  const completedPages = pageStatuses.filter((s) => s.status === 'complete').length
  const errorPages = pageStatuses.filter((s) => s.status === 'error').length
  const processingPages = pageStatuses.filter((s) => s.status === 'processing').length

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex justify-between text-sm">
            <span className="font-medium">
              Processing {pageStatuses.length} page{pageStatuses.length !== 1 ? 's' : ''}
            </span>
            <span className="text-muted-foreground">{overallProgress}%</span>
          </div>

          <Progress value={overallProgress} className="h-2" />

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span>{completedPages} completed</span>
              </div>
              {processingPages > 0 && (
                <div className="flex items-center space-x-1">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  <span>{processingPages} processing</span>
                </div>
              )}
              {errorPages > 0 && (
                <div className="flex items-center space-x-1">
                  <XCircle className="w-4 h-4 text-red-500" />
                  <span>{errorPages} failed</span>
                </div>
              )}
            </div>
          </div>

          {/* Per-page status indicators */}
          <div className="grid grid-cols-10 gap-1">
            {pageStatuses.map((status) => (
              <PageStatusIndicator key={status.pageIndex} status={status} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function PageStatusIndicator({ status }: { status: PageStatus }) {
  const getColor = () => {
    switch (status.status) {
      case 'complete':
        return 'bg-green-500'
      case 'error':
        return 'bg-red-500'
      case 'processing':
        return 'bg-blue-500 animate-pulse'
      default:
        return 'bg-gray-300'
    }
  }

  const getTitle = () => {
    const base = `Page ${status.pageIndex + 1}`
    if (status.error) return `${base}: ${status.error}`
    if (status.timeMs) return `${base}: ${status.timeMs}ms`
    return base
  }

  return (
    <div
      className={`h-2 rounded-full ${getColor()}`}
      title={getTitle()}
      style={{ width: '100%' }}
    />
  )
}

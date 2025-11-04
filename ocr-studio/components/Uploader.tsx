'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, FileImage, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAppStore } from '@/store/useAppStore'
import { useToast } from '@/hooks/use-toast'

const MAX_FILE_SIZE_MB = parseInt(process.env.NEXT_PUBLIC_MAX_FILE_SIZE_MB || '50', 10)
const MAX_FILES = 50
const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/tiff': ['.tiff', '.tif'],
}

interface UploaderProps {
  onFilesSelected?: (files: File[]) => void
}

export function Uploader({ onFilesSelected }: UploaderProps) {
  const { files, setFiles } = useAppStore()
  const { toast } = useToast()
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Validate file sizes
    const oversizedFiles = acceptedFiles.filter(
      (f) => f.size > MAX_FILE_SIZE_MB * 1024 * 1024
    )

    if (oversizedFiles.length > 0) {
      toast({
        title: 'Files too large',
        description: `Maximum file size is ${MAX_FILE_SIZE_MB}MB`,
        variant: 'destructive',
      })
      return
    }

    if (acceptedFiles.length + uploadedFiles.length > MAX_FILES) {
      toast({
        title: 'Too many files',
        description: `Maximum ${MAX_FILES} files allowed`,
        variant: 'destructive',
      })
      return
    }

    if (rejectedFiles.length > 0) {
      toast({
        title: 'Invalid files',
        description: 'Only PDF, PNG, JPEG, and TIFF files are supported',
        variant: 'destructive',
      })
    }

    const newFiles = [...uploadedFiles, ...acceptedFiles]
    setUploadedFiles(newFiles)
    setFiles(newFiles)
    onFilesSelected?.(newFiles)
  }, [uploadedFiles, setFiles, toast, onFilesSelected])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: MAX_FILES,
    multiple: true,
  })

  const removeFile = (index: number) => {
    const newFiles = uploadedFiles.filter((_, i) => i !== index)
    setUploadedFiles(newFiles)
    setFiles(newFiles)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="space-y-4">
      <Card
        {...getRootProps()}
        className={`p-8 border-2 border-dashed cursor-pointer transition-colors ${
          isDragActive ? 'dropzone-active border-primary' : 'hover:border-primary/50'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center justify-center text-center space-y-4">
          <div className="rounded-full bg-primary/10 p-6">
            <Upload className="w-12 h-12 text-primary" />
          </div>
          <div>
            <p className="text-lg font-semibold">
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              or click to browse
            </p>
          </div>
          <div className="text-xs text-muted-foreground">
            Supports PDF, PNG, JPEG, TIFF • Max {MAX_FILE_SIZE_MB}MB per file •
            Up to {MAX_FILES} files
          </div>
        </div>
      </Card>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">
            Uploaded Files ({uploadedFiles.length})
          </h3>
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-3 border rounded-md"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    {file.type === 'application/pdf' ? (
                      <File className="w-5 h-5 text-red-500" />
                    ) : (
                      <FileImage className="w-5 h-5 text-blue-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFile(index)}
                  className="flex-shrink-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

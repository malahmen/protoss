"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Upload, X } from "lucide-react"
import { toast } from "@/components/ui/use-toast"

export default function FileUploader() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setProgress(0)

    // Simulate upload progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + 10
      })
    }, 300)

    // Simulate upload completion
    setTimeout(() => {
      clearInterval(interval)
      setProgress(100)
      setUploading(false)
      setFile(null)
      toast({
        title: "File uploaded",
        description: `${file.name} has been uploaded successfully.`,
      })
    }, 3000)
  }

  const handleClearFile = () => {
    setFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium">Upload File</div>
      <div className="flex items-center space-x-2">
        <Button variant="outline" size="sm" className="flex-1 truncate" onClick={() => fileInputRef.current?.click()}>
          <Upload className="h-4 w-4 mr-2" />
          {file ? file.name : "Choose file"}
        </Button>
        {file && (
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleClearFile}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" />
      {file && (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
          {uploading ? (
            <Progress value={progress} className="h-2" />
          ) : (
            <Button size="sm" className="w-full" onClick={handleUpload} disabled={uploading}>
              Upload
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

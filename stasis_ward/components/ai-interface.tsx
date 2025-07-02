"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Globe, FileText, X, Volume2, VolumeX } from "lucide-react"
import FileUploader from "@/components/file-uploader"
import ChatMessage from "@/components/chat-message"
import ProcessedItems from "@/components/processed-items"
import SpeechToText from "@/components/speech-to-text"
import { speakText } from "@/lib/utils"
import { toast } from "@/components/ui/use-toast"

// Mock data for demonstration
const mockProcessedFiles = [
  { name: "annual-report-2023.pdf", date: "2023-05-20T14:30:00Z" },
  { name: "product-specs.docx", date: "2023-05-18T09:15:00Z" },
  { name: "meeting-notes.txt", date: "2023-05-15T16:45:00Z" },
]

const mockGatheredSites = [
  { url: "https://example.com/docs", date: "2023-05-19T11:20:00Z" },
  { url: "https://knowledge-base.org/articles", date: "2023-05-17T13:10:00Z" },
  { url: "https://research-papers.net/ai", date: "2023-05-14T10:05:00Z" },
]

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
}

type ProcessedItem = {
  name: string
  date: string
}

type GatheredSite = {
  url: string
  date: string
}

// Environment variables
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const collection = process.env.NEXT_PUBLIC_DEFAULT_COLLECTION || 'acknowledged'
const maxChunks = Number(process.env.NEXT_PUBLIC_MAX_CONTEXT_CHUNKS || 5)
const strictContext = process.env.NEXT_PUBLIC_STRICT_CONTEXT !== 'false'

export default function AIInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! How can I assist you today?",
      timestamp: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [websiteUrl, setWebsiteUrl] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [processedFiles, setProcessedFiles] = useState<ProcessedItem[]>([])
  const [gatheredSites, setGatheredSites] = useState<GatheredSite[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const [isSpeaking, setIsSpeaking] = useState(true)

  // Fetch processed files and gathered sites
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [filesResponse, sitesResponse] = await Promise.all([
          fetch(`${apiUrl}/files`),
          fetch(`${apiUrl}/sites`)
        ])

        if (filesResponse.ok) {
          const files = await filesResponse.json()
          setProcessedFiles(files)
        }

        if (sitesResponse.ok) {
          const sites = await sitesResponse.json()
          setGatheredSites(sites)
        }
      } catch (error) {
        console.error('Error fetching data:', error)
        toast({
          title: "Error",
          description: "Failed to load processed files and sites.",
          variant: "destructive",
        })
      }
    }

    fetchData()
  }, [])

  // Scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim() && !websiteUrl.trim() && !attachedFile) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content:
        input +
        (websiteUrl ? `\n\nContext from: ${websiteUrl}` : "") +
        (attachedFile ? `\n\nAttached file: ${attachedFile.name}` : ""),
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setWebsiteUrl("")
    setIsLoading(true)

    try {
      // Handle file upload if present
      let fileData = null
      if (attachedFile) {
        const formData = new FormData()
        formData.append('file', attachedFile)
        
        const uploadResponse = await fetch(`${apiUrl}/upload`, {
          method: 'POST',
          body: formData,
        })
        
        if (!uploadResponse.ok) {
          throw new Error('File upload failed')
        }
        
        fileData = await uploadResponse.json()
        toast({
          title: "File uploaded",
          description: `${attachedFile.name} has been uploaded successfully.`,
          variant: `default`,
        })
        const fileId = fileData.id

        // Poll for file readiness
        let status = "processing"
        let attempts = 0
        while (status !== "ready" && status !== "processed" && attempts < 1800) { // e.g., 1800 attempts = half an hour
          await new Promise(res => setTimeout(res, 1000))
          const statusResponse = await fetch(`${apiUrl}/file_status?id=${fileId}`)
          const statusData = await statusResponse.json()
          status = statusData.status
          attempts++
        }
        if (status !== "processing") {
          setIsLoading(false)
        }
        if (status !== "ready" &&  status !== "processed") {
          toast({ title: "Timeout", description: `${attachedFile.name} processing took too long.`, variant: "destructive",})
          return
        }
        if (status == "ready" || status == "processed") {
          toast({ title: "File processed", description: `${attachedFile.name} has been processed successfully.` })
          // call endpoint to clear fileid status file - ones shot
          try {
            const statusResponse = await fetch(`${apiUrl}/file_status?id=${fileId}`, {
              method: 'DELETE',
            })
            const statusData = await statusResponse.json()
            if (statusData.status === "removed") {
              toast({
                title: "File status cleared",
                description: `${attachedFile.name} had its status cleared successfully.`,
              })
            } else {
              toast({
                title: "File status not found",
                description: `No status file was found for ${attachedFile.name}.`,
                variant: "destructive",
              })
            }
          } catch (err) {
            toast({
              title: "Error",
              description: `Failed to clear status for ${attachedFile.name}.`,
              variant: "destructive",
            })
          }
        }

        setAttachedFile(null)
        const fileInput = document.getElementById("chat-file-input") as HTMLInputElement | null
        if (fileInput) {
          fileInput.value = ""
        }
      }

      // Send message to API
      const history = messages
        .filter((msg) => (msg.role === "user" || msg.role === "assistant") && msg.id !== "welcome")
        .map(({ role, content }) => ({ role, content }))
      const response = await fetch(`${apiUrl}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: input,
          collection,
          max_context_chunks: maxChunks,
          strict_context: strictContext,
          websiteUrl: websiteUrl || undefined,
          fileId: fileData?.id,
          history,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response from AI')
      }

      const data = await response.json()
      console.log(data)
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        timestamp: new Date().toISOString(),
      }
      
      setMessages((prev) => [...prev, assistantMessage])
      speakText(data.answer, isSpeaking)
    } catch (error) {
      console.error('Error:', error)
      toast({
        title: "Error",
        description: "Failed to get response from AI. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleSpeechResult = (transcript: string) => {
    setInput(transcript)
    setIsRecording(false)
  }

  return (
    <div className="flex h-screen w-full">
      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 p-4 overflow-hidden">
        <Card className="flex flex-col flex-1 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">AI Assistant</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col flex-1 p-4 space-y-4 overflow-hidden">
            {/* Messages Area */}
            <ScrollArea className="flex-1 pr-4">
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="flex flex-col space-y-2">
              <div className="flex items-center space-x-2">
                <Input
                  type="text"
                  placeholder="Enter website URL for context"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  className="flex-1"
                />
                <Button variant="outline" size="icon">
                  <Globe className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex items-start space-x-2">
                <Textarea
                  placeholder="Type your message here..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="flex-1 min-h-[80px]"
                />
                <div className="flex flex-col space-y-2">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => {
                      const fileInput = document.getElementById("chat-file-input")
                      if (fileInput) {
                        fileInput.click()
                      }
                    }}
                    title="Attach file"
                  >
                    <FileText className="h-8 w-8" />
                  </Button>
                  <SpeechToText
                    isRecording={isRecording}
                    setIsRecording={setIsRecording}
                    onResult={handleSpeechResult}
                  />
                    <Button
                    variant={isSpeaking ? "secondary" : "outline"}
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => setIsSpeaking((prev) => !prev)}
                    title={isSpeaking ? "Mute voice" : "Unmute voice"}
                  >
                    {isSpeaking ? (
                      <Volume2 className="h-8 w-8" />
                    ) : (
                      <VolumeX className="h-8 w-8" />
                    )}
                  </Button>
                  <Button
                    onClick={handleSendMessage}
                    disabled={isLoading || (!input.trim() && !websiteUrl.trim())}
                    size="icon"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {attachedFile && (
                <div className="flex items-center mt-2 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4 mr-1" />
                  <span className="truncate">{attachedFile.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 ml-2"
                    onClick={() => {
                      setAttachedFile(null)
                      if (document.getElementById("chat-file-input")) {
                        ;(document.getElementById("chat-file-input") as HTMLInputElement).value = ""
                      }
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        <input
          type="file"
          id="chat-file-input"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              setAttachedFile(e.target.files[0])
              toast({
                title: "File attached",
                description: `${e.target.files[0].name} will be uploaded with your message.`,
              })
            }
          }}
        />
      </div>

      {/* Sidebar */}
      <div className="w-80 border-l p-4 overflow-hidden hidden md:block">
        <Tabs defaultValue="files" className="h-full flex flex-col">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="files">
              <FileText className="h-4 w-4 mr-2" />
              Files
            </TabsTrigger>
            <TabsTrigger value="sites">
              <Globe className="h-4 w-4 mr-2" />
              Sites
            </TabsTrigger>
          </TabsList>
          <div className="mt-4 flex-1 overflow-hidden">
            <TabsContent value="files" className="h-full flex flex-col">
              <FileUploader />
              <div className="mt-4 flex-1 overflow-hidden">
                <ProcessedItems
                  title="Processed Files"
                  items={processedFiles}
                  icon={<FileText className="h-4 w-4" />}
                  keyField="name"
                />
              </div>
            </TabsContent>
            <TabsContent value="sites" className="h-full flex flex-col">
              <ProcessedItems
                title="Gathered Sites"
                items={gatheredSites}
                icon={<Globe className="h-4 w-4" />}
                keyField="url"
              />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  )
}

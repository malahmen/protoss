"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Mic, MicOff } from "lucide-react"
import { toast } from "@/components/ui/use-toast"

interface SpeechToTextProps {
  isRecording: boolean
  setIsRecording: (isRecording: boolean) => void
  onResult: (transcript: string) => void
}

export default function SpeechToText({ isRecording, setIsRecording, onResult }: SpeechToTextProps) {
  const [recognition, setRecognition] = useState<any | null>(null)

  useEffect(() => {
    if (typeof window !== "undefined") {
      // Check if browser supports SpeechRecognition
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

      if (SpeechRecognition) {
        const recognitionInstance = new SpeechRecognition()
        recognitionInstance.continuous = true
        recognitionInstance.interimResults = true

        recognitionInstance.onresult = (event) => {
          const transcript = Array.from(event.results)
            .map((result) => result[0].transcript)
            .join("")

          if (event.results[0].isFinal) {
            onResult(transcript)
          }
        }

        recognitionInstance.onerror = (event) => {
          console.error("Speech recognition error", event.error)
          setIsRecording(false)
          toast({
            title: "Speech recognition error",
            description: `Error: ${event.error}`,
            variant: "destructive",
          })
        }

        setRecognition(recognitionInstance)
      }
    }

    return () => {
      if (recognition) {
        recognition.abort()
      }
    }
  }, [onResult, setIsRecording])

  const toggleRecording = () => {
    if (!recognition) {
      toast({
        title: "Speech recognition not supported",
        description: "Your browser does not support speech recognition.",
        variant: "destructive",
      })
      return
    }

    if (isRecording) {
      recognition.stop()
      setIsRecording(false)
    } else {
      try {
        recognition.start()
        setIsRecording(true)
      } catch (error) {
        console.error("Error starting speech recognition:", error)
        toast({
          title: "Error",
          description: "Could not start speech recognition.",
          variant: "destructive",
        })
      }
    }
  }

  return (
    <Button
      onClick={toggleRecording}
      variant={isRecording ? "destructive" : "outline"}
      size="icon"
      title={isRecording ? "Stop recording" : "Start recording"}
    >
      {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
    </Button>
  )
}

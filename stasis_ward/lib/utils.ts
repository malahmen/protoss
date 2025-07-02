import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function speakText(text: string, enabled = true) {
  if (!enabled || typeof window === 'undefined' || !('speechSynthesis' in window)) return

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'en-US' // You can customize this
  window.speechSynthesis.cancel() // Cancel any current speech
  window.speechSynthesis.speak(utterance)
}

// Add any other utility functions here

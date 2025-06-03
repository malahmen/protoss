import { formatDistanceToNow } from "date-fns"
import { User, Bot } from "lucide-react"

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
}

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const formattedTime = formatDistanceToNow(new Date(message.timestamp), {
    addSuffix: true,
  })

  return (
    <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[80%] ${message.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
        <div
          className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full ${
            message.role === "user" ? "bg-primary ml-2" : "bg-muted mr-2"
          }`}
        >
          {message.role === "user" ? <User className="h-4 w-4 text-primary-foreground" /> : <Bot className="h-4 w-4" />}
        </div>
        <div
          className={`rounded-lg p-3 ${message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
          <div
            className={`mt-1 text-xs ${
              message.role === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
            }`}
          >
            {formattedTime}
          </div>
        </div>
      </div>
    </div>
  )
}

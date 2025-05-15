// src/components/Chat.tsx
import { useState, useRef, useEffect } from 'react';

interface Message {
  sender: 'user' | 'model';
  text: string;
}

interface APIResponse {
  answer: string;
  context_chunks: string[];
  model: string;
  timestamp: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Environment variable fallbacks
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const collection = import.meta.env.VITE_DEFAULT_COLLECTION || 'acknowledged';
  const maxChunks = Number(import.meta.env.VITE_MAX_CONTEXT_CHUNKS || 5);
  const strictContext = import.meta.env.VITE_STRICT_CONTEXT !== 'false';

  // Warn if VITE_API_URL is not set
  if (!import.meta.env.VITE_API_URL) {
    console.warn("⚠️ VITE_API_URL is not set in your .env file.");
  }

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    setMessages(prev => [...prev, { sender: 'user', text: input }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/ask`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: input,
          collection: collection,
          max_context_chunks: maxChunks,
          strict_context: strictContext,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data: APIResponse = await response.json();
      
      if (!data.answer) {
        throw new Error('Empty response from AI model');
      }

      // Add model response
      setMessages(prev => [...prev, { 
        sender: 'model', 
        text: data.answer 
      }]);

    } catch (error) {
      console.error('Error:', error);
      // Show error message to user
      setMessages(prev => [...prev, { 
        sender: 'model', 
        text: "Sorry, I'm having trouble responding right now. Please try again later."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <header className="text-center text-xl font-semibold p-4 border-b border-gray-700">
        Document QA Chat
      </header>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-xl px-4 py-2 rounded-lg whitespace-pre-wrap ${
              msg.sender === 'user'
                ? 'ml-auto bg-blue-600'
                : 'mr-auto bg-gray-700'
            }`}
          >
            {msg.text}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="p-4 border-t border-gray-700 bg-gray-800">
        <div className="flex gap-2">
          <textarea
            rows={2}
            className="flex-1 p-2 rounded bg-gray-700 text-white border border-gray-600 resize-none focus:outline-none focus:ring focus:ring-blue-500"
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading}
            className="self-end bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Processing...' : 'Ask'}
          </button>
        </div>
        <p className="mt-2 text-sm text-gray-400">
          Questions are answered using context from uploaded documents
        </p>
      </div>
    </div>
  );
}
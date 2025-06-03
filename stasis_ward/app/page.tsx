import { Suspense } from "react"
import AIInterface from "@/components/ai-interface"
import { Skeleton } from "@/components/ui/skeleton"

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      <div className="flex flex-1 overflow-hidden">
        <Suspense fallback={<Skeleton className="w-full h-screen" />}>
          <AIInterface />
        </Suspense>
      </div>
    </main>
  )
}

import { ScrollArea } from "@/components/ui/scroll-area"
import { formatDistanceToNow } from "date-fns"
import type { ReactNode } from "react"

interface ProcessedItemsProps {
  title: string
  items: Array<{ [key: string]: string }>
  icon: ReactNode
  keyField: string
}

export default function ProcessedItems({ title, items, icon, keyField }: ProcessedItemsProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="text-sm font-medium mb-2">{title}</div>
      <ScrollArea className="flex-1">
        <div className="space-y-2">
          {items.length > 0 ? (
            items.map((item, index) => (
              <div key={index} className="p-2 rounded-md border text-sm hover:bg-muted transition-colors">
                <div className="flex items-center">
                  <span className="mr-2">{icon}</span>
                  <span className="truncate flex-1">{item[keyField]}</span>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {formatDistanceToNow(new Date(item.date), {
                    addSuffix: true,
                  })}
                </div>
              </div>
            ))
          ) : (
            <div className="text-sm text-muted-foreground text-center py-4">No items yet</div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

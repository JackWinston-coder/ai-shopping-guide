'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowLeft,
  Search,
  Calendar,
  MessageSquare,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ensureToken, fetchChatSessions } from '@/lib/api'
import type { ChatSession } from '@/lib/types'
import { toast } from 'sonner'

function HistoryCardItem({ session, onClick }: { session: ChatSession; onClick: () => void }) {
  const firstUserMessage = session.messages.find((message) => message.role === 'user')
  const firstAssistantMessage = session.messages.find((message) => message.role === 'assistant')
  const productCount = session.messages.reduce((count, message) => count + (message.products?.length || 0), 0)

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-border overflow-hidden hover:shadow-md transition-shadow bg-card"
    >
      <div className="h-1 bg-gradient-to-r from-purple-500 to-indigo-500" />
      <div className="p-4 space-y-3">
        <h3 className="text-sm font-medium line-clamp-2 text-foreground">
          {firstUserMessage?.content || session.title}
        </h3>
        <p className="text-xs text-muted-foreground line-clamp-1">
          {firstAssistantMessage?.content || session.preview}
        </p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="size-3" />
              {session.timestamp}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="size-3" />
              {session.messages.length} 条消息
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {productCount > 0 ? `${productCount} 件商品` : '未推荐商品'}
          </span>
        </div>
      </div>
    </button>
  )
}

export default function HistoryPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = React.useState('')
  const [sessions, setSessions] = React.useState<ChatSession[]>([])
  const [isLoading, setIsLoading] = React.useState(true)

  React.useEffect(() => {
    ensureToken()
      .then(fetchChatSessions)
      .then(setSessions)
      .catch((error) => toast.error(error instanceof Error ? error.message : '历史会话加载失败'))
      .finally(() => setIsLoading(false))
  }, [])

  const filteredSessions = sessions.filter((session) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      session.title.toLowerCase().includes(q) ||
      session.preview.toLowerCase().includes(q) ||
      session.messages.some((message) => message.content.toLowerCase().includes(q))
    )
  })

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Button variant="ghost" size="icon" onClick={() => router.push('/chat')}>
            <ArrowLeft className="size-5" />
            <span className="sr-only">返回</span>
          </Button>
          <h1 className="text-lg font-semibold text-foreground">历史对话</h1>
        </div>

        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索历史对话..."
            className="pl-9 h-10"
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <MessageSquare className="size-12 text-muted-foreground/50 mb-4 animate-pulse" />
            <p className="text-muted-foreground">正在加载历史对话...</p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Search className="size-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">没有找到匹配的对话</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredSessions.map((session) => (
              <HistoryCardItem
                key={session.id}
                session={session}
                onClick={() => router.push(`/chat?session=${session.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

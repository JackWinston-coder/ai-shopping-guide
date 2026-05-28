'use client'

import * as React from 'react'
import { 
  Plus, 
  MessageSquare, 
  Settings, 
  Sparkles, 
  ShoppingCart,
  Sun,
  Moon,
  History,
} from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import type { ChatSession } from '@/lib/types'

interface ChatSidebarProps {
  sessions: ChatSession[]
  activeSessionId: string
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onCategoryClick: (category: string) => void
  onCartClick: () => void
  onHistoryClick: () => void
  cartItemCount: number
}

const categories = [
  { emoji: '💄', label: '美妆护肤' },
  { emoji: '📱', label: '数码电子' },
  { emoji: '👗', label: '服饰运动' },
  { emoji: '🍜', label: '食品饮料' },
]

export function ChatSidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  onCategoryClick,
  onCartClick,
  onHistoryClick,
  cartItemCount,
}: ChatSidebarProps) {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div className="flex flex-col h-full w-[280px] bg-card">
      {/* Top section - User info */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="size-10">
              <AvatarFallback className="bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-300 font-medium">
                U
              </AvatarFallback>
            </Avatar>
            <span className="font-medium text-foreground">用户</span>
          </div>
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
            <Settings className="size-5" />
            <span className="sr-only">设置</span>
          </Button>
        </div>
      </div>

      {/* New chat button */}
      <div className="p-4">
        <Button
          variant="outline"
          className="w-full justify-start gap-2 border-purple-300 text-purple-600 hover:bg-purple-50 hover:text-purple-700 dark:border-purple-700 dark:text-purple-400 dark:hover:bg-purple-900/30 dark:hover:text-purple-300"
          onClick={onNewChat}
        >
          <Plus className="size-4" />
          新建对话
        </Button>
      </div>

      {/* Chat session list */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="space-y-1">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={cn(
                "w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors",
                session.id === activeSessionId
                  ? "bg-purple-50 dark:bg-purple-900/30 border-l-2 border-purple-500"
                  : "hover:bg-purple-50/50 dark:hover:bg-purple-900/20"
              )}
            >
              <MessageSquare className="size-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-muted-foreground truncate">
                  {session.preview}
                </p>
              </div>
              <span className="text-xs text-muted-foreground shrink-0">
                {session.timestamp}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Category quick-access section */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="size-4 text-purple-500" />
          <span className="text-sm font-medium text-foreground">快捷类目</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {categories.map((category) => (
            <button
              key={category.label}
              onClick={() => onCategoryClick(category.label)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-full border border-purple-200 dark:border-purple-800 text-sm hover:bg-purple-50 dark:hover:bg-purple-900/30 transition-colors"
            >
              <span>{category.emoji}</span>
              <span className="text-foreground truncate">{category.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom section - sticky */}
      <div className="p-4 border-t border-border space-y-2">
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
          onClick={onHistoryClick}
        >
          <History className="size-4" />
          历史对话
        </Button>

        {/* Dark mode toggle */}
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {mounted && theme === 'dark' ? (
            <Sun className="size-4" />
          ) : (
            <Moon className="size-4" />
          )}
          {mounted && (theme === 'dark' ? '浅色模式' : '深色模式')}
        </Button>

        {/* Shopping cart button */}
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
          onClick={onCartClick}
        >
          <div className="relative">
            <ShoppingCart className="size-4" />
            {cartItemCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 size-4 flex items-center justify-center bg-red-500 text-white text-[10px] font-medium rounded-full">
                {cartItemCount}
              </span>
            )}
          </div>
          购物车
        </Button>
      </div>
    </div>
  )
}

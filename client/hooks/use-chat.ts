'use client'

import * as React from 'react'
import { toast } from 'sonner'
import type { CartItem, ChatSession, Message, Product } from '@/lib/types'
import {
  addCartItem,
  createChatSession,
  ensureToken,
  fetchCart,
  fetchChatSessions,
  mapProduct,
  removeCartItem,
  streamChat,
  updateCartItem,
} from '@/lib/api'

export function useChatSessions(initialSessionId?: string) {
  const [sessions, setSessions] = React.useState<ChatSession[]>([
    { id: 'local-1', title: '智能导购对话', preview: '开始新对话', timestamp: '刚刚', isActive: true, messages: [] },
  ])
  const [activeSessionId, setActiveSessionId] = React.useState(initialSessionId || 'local-1')

  const activeSession = sessions.find(s => s.id === activeSessionId)
  const messages = activeSession?.messages || []
  const sessionTitle = activeSession?.title || '智能导购对话'
  const activeServerSessionId = activeSession?.serverSessionId

  React.useEffect(() => {
    ensureToken()
      .then(async () => {
        const remoteSessions = await fetchChatSessions()
        if (remoteSessions.length > 0) {
          setSessions(remoteSessions)
          if (initialSessionId && remoteSessions.some(s => s.id === initialSessionId)) {
            setActiveSessionId(initialSessionId)
          } else {
            setActiveSessionId(remoteSessions[0].id)
          }
        }
      })
      .catch(() => toast.error('无法连接后端服务，请确认 FastAPI 已启动'))
  }, [initialSessionId])

  const updateSession = React.useCallback((sessionId: string, updater: (session: ChatSession) => ChatSession) => {
    setSessions(prev => prev.map(s => s.id === sessionId ? updater(s) : s))
  }, [])

  const handleNewChat = React.useCallback(async () => {
    try {
      const newSession = await createChatSession()
      setSessions(prev => [newSession, ...prev])
      setActiveSessionId(newSession.id)
      return newSession
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建会话失败')
      return null
    }
  }, [])

  const handleSelectSession = React.useCallback((id: string) => {
    setActiveSessionId(id)
  }, [])

  const handleCategoryClick = React.useCallback(async (category: string) => {
    try {
      const newSession = await createChatSession(`${category}推荐`)
      setSessions(prev => [newSession, ...prev])
      setActiveSessionId(newSession.id)
      return { session: newSession, input: `我想了解一下${category}类目有什么好的推荐` }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建会话失败')
      return null
    }
  }, [])

  const handleTitleUpdate = React.useCallback((title: string) => {
    updateSession(activeSessionId, s => ({ ...s, title }))
  }, [activeSessionId, updateSession])

  return {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    messages,
    sessionTitle,
    activeServerSessionId,
    updateSession,
    handleNewChat,
    handleSelectSession,
    handleCategoryClick,
    handleTitleUpdate,
  }
}

export function useCart() {
  const [cartItems, setCartItems] = React.useState<CartItem[]>([])
  const cartItemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0)

  React.useEffect(() => {
    ensureToken()
      .then(() => fetchCart())
      .then(setCartItems)
      .catch(() => {})
  }, [])

  const handleUpdateQuantity = React.useCallback(async (id: string, quantity: number) => {
    try {
      setCartItems(await updateCartItem(id, quantity))
      toast.success('数量已更改')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '更新失败')
    }
  }, [])

  const handleRemoveItem = React.useCallback(async (id: string) => {
    try {
      setCartItems(await removeCartItem(id))
      toast.success('已移除商品')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '移除失败')
    }
  }, [])

  const handleAddToCart = React.useCallback(async (product: Product) => {
    const firstSku = product.skus[0]
    try {
      setCartItems(await addCartItem(product.id, firstSku?.sku_id))
      toast.success('已加入购物车')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加购失败')
    }
  }, [])

  return {
    cartItems,
    cartItemCount,
    handleUpdateQuantity,
    handleRemoveItem,
    handleAddToCart,
  }
}

export function useChatStream(
  activeSessionId: string,
  activeServerSessionId: string | undefined,
  updateSession: (sessionId: string, updater: (session: ChatSession) => ChatSession) => void,
) {
  const [isLoading, setIsLoading] = React.useState(false)
  const [pendingImageUrl, setPendingImageUrl] = React.useState<string | undefined>()

  const handleSubmit = React.useCallback(async (
    input: string,
    onInputClear: () => void,
  ) => {
    if ((!input.trim() && !pendingImageUrl) || isLoading) return

    const now = new Date()
    const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim() || '请根据这张图片帮我找相似商品',
      timestamp,
    }

    updateSession(activeSessionId, s => ({
      ...s,
      messages: [...s.messages, userMessage],
      preview: input.trim(),
    }))
    onInputClear()
    setIsLoading(true)

    const streamingMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp,
      isStreaming: true,
    }

    updateSession(activeSessionId, s => ({
      ...s,
      messages: [...s.messages, streamingMessage],
    }))

    try {
      await streamChat(
        { message: userMessage.content, sessionId: activeServerSessionId, imageUrl: pendingImageUrl },
        (event) => {
          if (event.type === 'session' && event.data.session_id) {
            updateSession(activeSessionId, s => ({
              ...s,
              serverSessionId: event.data.session_id,
            }))
          }
          if (event.type === 'text_delta') {
            const content = event.data.content || ''
            updateSession(activeSessionId, s => ({
              ...s,
              messages: s.messages.map(msg =>
                msg.id === streamingMessage.id ? { ...msg, content: msg.content + content } : msg
              ),
            }))
          }
          if (event.type === 'product_cards') {
            const products = (event.data.products || []).map(mapProduct)
            updateSession(activeSessionId, s => ({
              ...s,
              messages: s.messages.map(msg =>
                msg.id === streamingMessage.id ? { ...msg, products } : msg
              ),
            }))
          }
          if (event.type === 'error') {
            toast.error(event.data.message || '聊天处理失败')
          }
        },
      )
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '聊天接口请求失败')
    } finally {
      updateSession(activeSessionId, s => ({
        ...s,
        messages: s.messages.map(msg =>
          msg.id === streamingMessage.id ? { ...msg, isStreaming: false } : msg
        ),
      }))
      setIsLoading(false)
      setPendingImageUrl(undefined)
    }
  }, [activeSessionId, activeServerSessionId, isLoading, pendingImageUrl, updateSession])

  return {
    isLoading,
    pendingImageUrl,
    setPendingImageUrl,
    handleSubmit,
  }
}

export function useVoiceInput(onResult: (text: string) => void) {
  const [isVoiceActive, setIsVoiceActive] = React.useState(false)
  const recognitionRef = React.useRef<any>(null)

  const toggle = React.useCallback(() => {
    if (isVoiceActive) {
      recognitionRef.current?.stop?.()
      setIsVoiceActive(false)
      return
    }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      toast.error('当前浏览器不支持语音输入')
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.interimResults = false
    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript
      if (transcript) onResult(transcript)
    }
    recognition.onerror = () => toast.error('语音识别失败')
    recognition.onend = () => setIsVoiceActive(false)
    recognitionRef.current = recognition
    setIsVoiceActive(true)
    recognition.start()
  }, [isVoiceActive, onResult])

  return { isVoiceActive, toggle }
}

export function useTitleEdit(sessionTitle: string, onSave: (title: string) => void) {
  const [isEditing, setIsEditing] = React.useState(false)
  const [editedTitle, setEditedTitle] = React.useState('')
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const startEdit = React.useCallback(() => {
    setEditedTitle(sessionTitle)
    setIsEditing(true)
  }, [sessionTitle])

  const save = React.useCallback(() => {
    if (editedTitle.trim()) onSave(editedTitle.trim())
    setIsEditing(false)
  }, [editedTitle, onSave])

  const cancel = React.useCallback(() => setIsEditing(false), [])

  const handleKeyDown = React.useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') save()
    else if (e.key === 'Escape') cancel()
  }, [save, cancel])

  return { isEditing, editedTitle, setEditedTitle, inputRef, startEdit, save, cancel, handleKeyDown }
}

export function useScrollToBottom(dependency: unknown) {
  const endRef = React.useRef<HTMLDivElement>(null)
  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [dependency])
  return endRef
}

export function useScrollTop(threshold = 300) {
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const [showScrollTop, setShowScrollTop] = React.useState(false)

  React.useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const handleScroll = () => setShowScrollTop(el.scrollTop > threshold)
    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [threshold])

  const scrollToTop = React.useCallback(() => {
    scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  return { scrollRef, showScrollTop, scrollToTop }
}

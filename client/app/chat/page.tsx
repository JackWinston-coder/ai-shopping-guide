'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import {
  ShoppingCart,
  Send,
  Menu,
  Bot,
  ImagePlus,
  Mic,
  StopCircle,
  Volume2,
  Pencil,
  Check,
  X,
  ArrowUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChatSidebar } from '@/components/chat-sidebar'
import { ProductDetailModal } from '@/components/product-detail-modal'
import { ShoppingCartDrawer } from '@/components/shopping-cart-drawer'
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import type { Product } from '@/lib/types'
import {
  useChatSessions,
  useCart,
  useChatStream,
  useVoiceInput,
  useTitleEdit,
  useScrollToBottom,
  useScrollTop,
} from '@/hooks/use-chat'

function ProductCard({ product, onClick, onAddToCart }: { product: Product; onClick: () => void; onAddToCart: () => void }) {
  return (
    <div
      onClick={onClick}
      className="w-[200px] h-[300px] flex-shrink-0 bg-card border border-border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col text-left cursor-pointer"
    >
      <div className="h-[120px] overflow-hidden flex-shrink-0 relative">
        <Image
          src={product.image}
          alt={product.title}
          fill
          className="object-cover"
          sizes="200px"
          unoptimized={product.image.startsWith('/data/')}
        />
      </div>
      <div className="p-3 flex flex-col flex-1">
        <p className="text-xs text-muted-foreground uppercase tracking-wide truncate">{product.brand}</p>
        <h4 className="text-sm font-medium line-clamp-2 leading-snug h-10 mt-1">{product.title}</h4>
        <div className="flex items-center gap-2 mt-2">
          <p className="text-lg font-bold text-red-500">¥{product.base_price}</p>
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 dark:bg-purple-950 dark:text-purple-300">
            {product.category}
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="w-full mt-auto border-purple-300 text-purple-600 hover:bg-purple-50 dark:border-purple-700 dark:text-purple-400 dark:hover:bg-purple-950"
          onClick={(e) => {
            e.stopPropagation()
            onAddToCart()
          }}
        >
          <ShoppingCart className="size-3.5 mr-1.5" />
          加入购物车
        </Button>
      </div>
    </div>
  )
}

function StreamingCursor() {
  return (
    <span className="inline-block w-0.5 h-4 bg-purple-600 dark:bg-purple-400 ml-0.5 animate-pulse" />
  )
}

function ChatHeader({
  sessionTitle,
  cartItemCount,
  isEditing,
  editedTitle,
  setEditedTitle,
  titleInputRef,
  onTitleKeyDown,
  onStartEdit,
  onSaveTitle,
  onCancelTitle,
  onSidebarOpen,
  onCartOpen,
  onImageUpload,
  onVoiceToggle,
  isVoiceActive,
}: {
  sessionTitle: string
  cartItemCount: number
  isEditing: boolean
  editedTitle: string
  setEditedTitle: (v: string) => void
  titleInputRef: React.RefObject<HTMLInputElement | null>
  onTitleKeyDown: (e: React.KeyboardEvent) => void
  onStartEdit: () => void
  onSaveTitle: () => void
  onCancelTitle: () => void
  onSidebarOpen: () => void
  onCartOpen: () => void
  onImageUpload: () => void
  onVoiceToggle: () => void
  isVoiceActive: boolean
}) {
  return (
    <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-lg border-b border-border px-4 py-3">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onSidebarOpen}
        >
          <Menu className="size-5" />
          <span className="sr-only">打开菜单</span>
        </Button>
        <div className="hidden lg:block w-10" />

        <div className="flex items-center gap-2">
          {isEditing ? (
            <div className="flex items-center gap-1">
              <Input
                ref={titleInputRef}
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                onKeyDown={onTitleKeyDown}
                className="h-8 w-40 text-center text-sm font-semibold"
              />
              <Button variant="ghost" size="icon" className="size-7" onClick={onSaveTitle}>
                <Check className="size-4 text-green-600" />
              </Button>
              <Button variant="ghost" size="icon" className="size-7" onClick={onCancelTitle}>
                <X className="size-4 text-red-500" />
              </Button>
            </div>
          ) : (
            <button
              onDoubleClick={onStartEdit}
              className="flex items-center gap-2 hover:bg-muted px-3 py-1.5 rounded-lg transition-colors group"
            >
              <h2 className="font-semibold text-foreground">{sessionTitle}</h2>
              <Pencil className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground" onClick={onImageUpload}>
            <ImagePlus className="size-5" />
            <span className="sr-only">上传图片</span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={cn("text-muted-foreground hover:text-foreground", isVoiceActive && "text-red-500")}
            onClick={onVoiceToggle}
          >
            <Mic className="size-5" />
            <span className="sr-only">语音输入</span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="relative text-muted-foreground hover:text-foreground"
            onClick={onCartOpen}
          >
            <ShoppingCart className="size-5" />
            {cartItemCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 size-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {cartItemCount}
              </span>
            )}
            <span className="sr-only">购物车</span>
          </Button>
        </div>
      </div>
    </header>
  )
}

function MessageBubble({
  message,
  onProductClick,
  onAddToCart,
  onSpeak,
}: {
  message: import('@/lib/types').Message
  onProductClick: (p: Product) => void
  onAddToCart: (p: Product) => void
  onSpeak: (text: string) => void
}) {
  return (
    <div
      className={cn(
        "flex gap-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
        message.role === 'user' ? "justify-end" : "justify-start"
      )}
    >
      {message.role === 'assistant' && (
        <div className="flex-shrink-0 size-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
          <Bot className="size-4 text-white" />
        </div>
      )}

      <div className={cn("flex flex-col gap-1", message.role === 'user' ? "items-end" : "items-start")}>
        <div
          className={cn(
            "px-4 py-3 text-sm",
            message.role === 'user'
              ? "bg-purple-600 text-white rounded-2xl rounded-br-sm max-w-[70%]"
              : "bg-[#f0f0f5] dark:bg-zinc-800 text-foreground rounded-2xl rounded-bl-sm max-w-[80%]"
          )}
        >
          {message.content}
          {message.isStreaming && <StreamingCursor />}
        </div>

        {message.products && message.products.length > 0 && (
          <div className="mt-2 flex gap-3 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-thin scrollbar-thumb-purple-200 dark:scrollbar-thumb-purple-900 max-w-[calc(100vw-6rem)] lg:max-w-2xl">
            {message.products.map((product) => (
              <div key={product.id} className="snap-start">
                <ProductCard
                  product={product}
                  onClick={() => onProductClick(product)}
                  onAddToCart={() => onAddToCart(product)}
                />
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 px-1">
          <span className="text-xs text-muted-foreground">{message.timestamp}</span>
          {message.role === 'assistant' && !message.isStreaming && (
            <button
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
              onClick={() => onSpeak(message.content)}
            >
              <Volume2 className="size-3" />
              播报
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="size-16 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center mb-4">
        <Bot className="size-8 text-white" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">开始新对话</h3>
      <p className="text-muted-foreground text-sm max-w-sm">
        告诉我你想买什么，或者描述你的需求，我会帮你找到最合适的商品推荐。
      </p>
    </div>
  )
}

export default function ChatPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-background flex items-center justify-center"><div className="size-8 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" /></div>}>
      <ChatPageContent />
    </React.Suspense>
  )
}

function ChatPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const restoreSessionId = searchParams.get('session') || undefined
  const [input, setInput] = React.useState('')
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const [cartOpen, setCartOpen] = React.useState(false)
  const [selectedProduct, setSelectedProduct] = React.useState<Product | null>(null)
  const [isProductModalOpen, setIsProductModalOpen] = React.useState(false)
  const imageInputRef = React.useRef<HTMLInputElement>(null)

  const {
    sessions,
    activeSessionId,
    messages,
    sessionTitle,
    activeServerSessionId,
    updateSession,
    handleNewChat,
    handleSelectSession,
    handleCategoryClick,
    handleTitleUpdate,
  } = useChatSessions(restoreSessionId)

  const {
    cartItems,
    cartItemCount,
    handleUpdateQuantity: handleCartUpdateQuantity,
    handleRemoveItem: handleCartRemoveItem,
    handleAddToCart,
  } = useCart()

  const {
    isLoading,
    pendingImageUrl,
    setPendingImageUrl,
    handleSubmit: streamSubmit,
  } = useChatStream(activeSessionId, activeServerSessionId, updateSession)

  const { isVoiceActive, toggle: toggleVoice } = useVoiceInput(setInput)
  const titleEdit = useTitleEdit(sessionTitle, handleTitleUpdate)
  const messagesEndRef = useScrollToBottom(messages)
  const { scrollRef: chatScrollRef, showScrollTop, scrollToTop } = useScrollTop()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await streamSubmit(input, () => setInput(''))
  }

  const handleCategoryClickWrapper = async (category: string) => {
    const result = await handleCategoryClick(category)
    if (result) {
      setInput(result.input)
      setSidebarOpen(false)
    }
  }

  const handleImageUploadClick = () => imageInputRef.current?.click()

  const handleImageSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      setPendingImageUrl(String(reader.result || ''))
      toast.success('图片已准备好，可以直接发送')
    }
    reader.readAsDataURL(file)
    event.target.value = ''
  }

  const handleSpeak = (text: string) => {
    if (!('speechSynthesis' in window)) {
      toast.error('当前浏览器不支持语音播报')
      return
    }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    window.speechSynthesis.speak(utterance)
  }

  const sidebarContent = (
    <ChatSidebar
      sessions={sessions}
      activeSessionId={activeSessionId}
      onNewChat={async () => { await handleNewChat(); setSidebarOpen(false) }}
      onSelectSession={(id) => { handleSelectSession(id); setSidebarOpen(false) }}
      onCategoryClick={handleCategoryClickWrapper}
      onCartClick={() => { setSidebarOpen(false); setCartOpen(true) }}
      onHistoryClick={() => { setSidebarOpen(false); router.push('/history') }}
      cartItemCount={cartItemCount}
    />
  )

  return (
    <div className="min-h-screen bg-background flex">
      <aside className="hidden lg:block border-r border-border">
        {sidebarContent}
      </aside>

      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="p-0 w-[280px]">
          <SheetTitle className="sr-only">导航菜单</SheetTitle>
          {sidebarContent}
        </SheetContent>
      </Sheet>

      <main className="flex-1 flex flex-col min-w-0 h-screen">
        <ChatHeader
          sessionTitle={sessionTitle}
          cartItemCount={cartItemCount}
          isEditing={titleEdit.isEditing}
          editedTitle={titleEdit.editedTitle}
          setEditedTitle={titleEdit.setEditedTitle}
          titleInputRef={titleEdit.inputRef}
          onTitleKeyDown={titleEdit.handleKeyDown}
          onStartEdit={titleEdit.startEdit}
          onSaveTitle={titleEdit.save}
          onCancelTitle={titleEdit.cancel}
          onSidebarOpen={() => setSidebarOpen(true)}
          onCartOpen={() => setCartOpen(true)}
          onImageUpload={handleImageUploadClick}
          onVoiceToggle={toggleVoice}
          isVoiceActive={isVoiceActive}
        />

        <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 ? (
              <EmptyState />
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onProductClick={(p) => { setSelectedProduct(p); setIsProductModalOpen(true) }}
                  onAddToCart={handleAddToCart}
                  onSpeak={handleSpeak}
                />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {showScrollTop && (
            <Button
              variant="outline"
              size="icon"
              className="fixed bottom-28 right-8 z-20 size-10 rounded-full shadow-lg bg-background border-border"
              onClick={scrollToTop}
            >
              <ArrowUp className="size-4" />
            </Button>
          )}
        </div>

        <div className="sticky bottom-0 bg-background/80 backdrop-blur-lg border-t border-border p-4">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex items-center gap-2">
            {pendingImageUrl && (
              <div className="relative size-10 rounded-md overflow-hidden border border-border flex-shrink-0">
                <Image
                  src={pendingImageUrl}
                  alt="待发送图片"
                  fill
                  className="object-cover"
                  sizes="40px"
                  unoptimized
                />
                <button
                  type="button"
                  onClick={() => setPendingImageUrl(undefined)}
                  className="absolute -top-1 -right-1 size-4 bg-red-500 text-white rounded-full flex items-center justify-center"
                >
                  <X className="size-2.5" />
                </button>
              </div>
            )}
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入消息..."
              className="flex-1 h-11 bg-muted/50 border-border"
              disabled={isLoading}
            />
            <Button
              type="submit"
              size="icon"
              disabled={isLoading || (!input.trim() && !pendingImageUrl)}
              className="size-11 bg-purple-600 hover:bg-purple-700 text-white"
            >
              {isLoading ? <StopCircle className="size-5 animate-spin" /> : <Send className="size-5" />}
            </Button>
          </form>
        </div>
      </main>

      <ProductDetailModal
        product={selectedProduct}
        open={isProductModalOpen}
        onOpenChange={setIsProductModalOpen}
        onAddToCart={handleAddToCart}
      />

      <ShoppingCartDrawer
        open={cartOpen}
        onOpenChange={setCartOpen}
        items={cartItems}
        onUpdateQuantity={handleCartUpdateQuantity}
        onRemoveItem={handleCartRemoveItem}
      />

      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleImageSelected}
      />
    </div>
  )
}

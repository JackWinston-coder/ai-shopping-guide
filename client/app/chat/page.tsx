'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
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
import type { Product, Message, ChatSession, CartItem } from '@/lib/types'

const demoProducts: Product[] = [
  {
    id: 'p_beauty_001',
    title: '雅诗兰黛特润修护肌活精华露淡纹紧致保湿夜间修护抗初老精华30ml',
    brand: '雅诗兰黛',
    category: '美妆护肤',
    sub_category: '精华',
    base_price: 720,
    image: '/data/1_美妆护肤/images/p_beauty_001_live.jpg',
    skus: [
      { sku_id: 's_p_beauty_001_1', properties: { '容量': '30ml 经典装' }, price: 720 },
      { sku_id: 's_p_beauty_001_2', properties: { '容量': '50ml 加大装' }, price: 980 },
      { sku_id: 's_p_beauty_001_3', properties: { '容量': '75ml 家用装' }, price: 1260 },
    ],
    rag_knowledge: {
      marketing_description: '雅诗兰黛特润修护肌活精华露（小棕瓶）是品牌经典抗初老单品，主打夜间肌底修护。核心成分含高浓度二裂酵母发酵产物溶胞物，能深入修护日间紫外线、污染造成的损伤，促进肌肤代谢；搭配透明质酸锁水保湿，猴面包树籽提取物淡纹紧致。适合25+有干纹细纹、熬夜后暗沉的抗初老人群。',
      official_faq: [
        { question: '这款精华的核心成分二裂酵母发酵产物溶胞物有什么作用？', answer: '它能模拟皮肤微生态，帮助修护日间紫外线、污染等外界刺激造成的肌底损伤，促进肌肤新陈代谢，增强皮肤屏障功能。' },
        { question: '不同规格的小棕瓶怎么选？', answer: '30ml经典装适合初次尝试或短期出差携带；50ml加大装性价比更高；75ml家用装适合老用户囤货。' },
        { question: '这款精华适合敏感肌吗？', answer: '大部分肤质适用，但敏感肌建议先做耳后测试，开封后6个月内用完。' },
      ],
      user_reviews: [
        { nickname: '张雅静', rating: 5, content: '熬夜党救星！每晚3滴吸收超快不黏腻，第二天皮肤不暗沉。半个月后眼角干纹淡了，已经回购50ml加大装！' },
        { nickname: '李小米', rating: 1, content: '用了两次就脸颊泛红刺痛，我是敏感肌平时用其他精华都没事，这款成分可能太刺激了。' },
        { nickname: '王梓涵', rating: 2, content: '用了快一个月，保湿还行，但淡纹紧致完全没效果。720块30ml性价比太低。' },
      ],
    },
  },
  {
    id: 'p_digital_001',
    title: 'Apple iPhone 17 Pro 6.3英寸 A19 Pro 256GB 全网通旗舰手机',
    brand: 'Apple 苹果',
    category: '数码电子',
    sub_category: '智能手机',
    base_price: 8999,
    image: '/data/2_数码电子/images/p_digital_001_live.jpg',
    skus: [
      { sku_id: 's_p_digital_001_1', properties: { '存储': '256GB', '颜色': '宇宙橙', '版本': '全网通版' }, price: 8999 },
      { sku_id: 's_p_digital_001_4', properties: { '存储': '512GB', '颜色': '宇宙橙', '版本': '全网通版' }, price: 10499 },
      { sku_id: 's_p_digital_001_7', properties: { '存储': '1TB', '颜色': '宇宙橙', '版本': '全网通版' }, price: 12499 },
    ],
    rag_knowledge: {
      marketing_description: 'Apple iPhone 17 Pro搭载全新A19 Pro芯片，带来颠覆性性能提升。6.3英寸超视网膜XDR显示屏，支持ProMotion自适应刷新率。256GB起步的存储容量，宇宙橙、远峰蓝、深空黑三色可选。',
      official_faq: [
        { question: 'A19 Pro芯片相比上一代有哪些提升？', answer: 'A19 Pro芯片采用3纳米工艺制程，CPU性能提升20%，GPU性能提升30%，AI算力提升40%。' },
        { question: '256GB版本是否足够日常使用？', answer: '256GB版本适合大多数用户，可存储约6万张高清照片、150小时4K视频或500款常用应用。' },
      ],
      user_reviews: [
        { nickname: '张小明', rating: 5, content: 'iPhone 17 Pro真的太香了！A19 Pro芯片让我的工作效率提升了不少，剪辑视频比之前快了一倍。' },
        { nickname: '林小雨', rating: 4, content: '手机整体性能不错，宇宙橙的颜色也很特别。不过续航方面有点失望，重度使用一天需要充电两次。' },
      ],
    },
  },
  {
    id: 'p_clothes_001',
    title: '优衣库 U AIRism 棉质宽松圆领短袖T恤 男装 基础纯色上衣',
    brand: '优衣库',
    category: '服饰运动',
    sub_category: '短袖T恤',
    base_price: 99,
    image: '/data/3_服饰运动/images/p_clothes_001_live.jpg',
    skus: [
      { sku_id: 's_p_clothes_001_1', properties: { '尺码': 'S码', '颜色': '黑色' }, price: 99 },
      { sku_id: 's_p_clothes_001_5', properties: { '尺码': 'M码', '颜色': '白色' }, price: 99 },
      { sku_id: 's_p_clothes_001_9', properties: { '尺码': 'L码', '颜色': '深蓝色' }, price: 99 },
    ],
    rag_knowledge: {
      marketing_description: '优衣库这款AIRism联名系列的男装宽松圆领T恤，把亲肤棉感和黑科技凉感做了完美融合。面料用的是AIRism专属混纺棉，贴身穿完全不扎，自带的吸湿速干属性夏天出了汗也不会黏在背上。',
      official_faq: [
        { question: '这款AIRism棉质T恤和普通纯棉T恤穿感上有什么不一样？', answer: '叠加了AIRism专属的细微凉感纤维导孔，夏天贴身穿不会有普通纯棉刚上身的闷热感，出汗后面料能快速把潮气导出去。' },
        { question: '宽松版型会不会显邋遢？', answer: '这款的宽松是做了微落肩和衣长微调的H型宽松，不是oversize的长款垮版型，按常规码数选不会过于松垮。' },
      ],
      user_reviews: [
        { nickname: '小宇', rating: 5, content: '这是我今年买过最满意的基础T了！面料软乎乎的但是完全不透，出汗了风一吹很快就干。' },
        { nickname: '阿凯', rating: 4, content: '整体穿下来还挺舒服的，凉感确实比我之前买的普通纯棉T明显。' },
      ],
    },
  },
]

const demoMessages: Message[] = [
  {
    id: 'demo-1',
    role: 'user',
    content: '推荐一些好用的护肤品和数码产品',
    timestamp: '14:32',
  },
  {
    id: 'demo-2',
    role: 'assistant',
    content: '为你找到以下热门商品，涵盖护肤和数码领域：',
    timestamp: '14:32',
    products: demoProducts,
  },
  {
    id: 'demo-3',
    role: 'assistant',
    content: '这三款都是各自类目的明星产品。雅诗兰黛小棕瓶是抗初老经典，iPhone 17 Pro性能强劲，优衣库AIRism T恤性价比很高。你对哪款更感兴趣？',
    timestamp: '14:33',
  },
]

const initialSessions: ChatSession[] = [
  {
    id: '1',
    title: '智能导购对话',
    preview: '推荐一些好用的护肤品和数码产品',
    timestamp: '2小时前',
    isActive: true,
    messages: demoMessages,
  },
  {
    id: '2',
    title: '数码电子推荐',
    preview: '想买一款性价比高的手机',
    timestamp: '昨天',
    isActive: false,
    messages: [],
  },
  {
    id: '3',
    title: '服饰穿搭咨询',
    preview: '夏天穿的透气T恤有哪些推荐',
    timestamp: '3天前',
    isActive: false,
    messages: [],
  },
]

const initialCartItems: CartItem[] = [
  {
    id: 'cart-p_beauty_001',
    title: '雅诗兰黛特润修护肌活精华露',
    sku: '30ml 经典装',
    price: 720,
    quantity: 1,
    image: '/data/1_美妆护肤/images/p_beauty_001_live.jpg',
  },
  {
    id: 'cart-p_clothes_001',
    title: '优衣库 AIRism 棉质宽松圆领短袖T恤',
    sku: 'M码 / 白色',
    price: 99,
    quantity: 2,
    image: '/data/3_服饰运动/images/p_clothes_001_live.jpg',
  },
]

function ProductCard({ product, onClick, onAddToCart }: { product: Product; onClick: () => void; onAddToCart: () => void }) {
  return (
    <div
      onClick={onClick}
      className="w-[200px] h-[300px] flex-shrink-0 bg-card border border-border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col text-left cursor-pointer"
    >
      <div className="h-[120px] overflow-hidden flex-shrink-0">
        <img
          src={product.image}
          alt={product.title}
          className="w-full h-full object-cover"
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

export default function ChatPage() {
  const router = useRouter()
  const [sessions, setSessions] = React.useState<ChatSession[]>(initialSessions)
  const [activeSessionId, setActiveSessionId] = React.useState('1')
  const [input, setInput] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const [cartOpen, setCartOpen] = React.useState(false)
  const [cartItems, setCartItems] = React.useState<CartItem[]>(initialCartItems)
  const [isVoiceActive, setIsVoiceActive] = React.useState(false)
  const [isEditingTitle, setIsEditingTitle] = React.useState(false)
  const [editedTitle, setEditedTitle] = React.useState('')
  const [selectedProduct, setSelectedProduct] = React.useState<Product | null>(null)
  const [isProductModalOpen, setIsProductModalOpen] = React.useState(false)
  const [showScrollTop, setShowScrollTop] = React.useState(false)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const chatScrollRef = React.useRef<HTMLDivElement>(null)
  const titleInputRef = React.useRef<HTMLInputElement>(null)

  const activeSession = sessions.find(s => s.id === activeSessionId)
  const messages = activeSession?.messages || []
  const sessionTitle = activeSession?.title || '智能导购对话'
  const cartItemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  React.useEffect(() => {
    scrollToBottom()
  }, [messages])

  React.useEffect(() => {
    if (isEditingTitle && titleInputRef.current) {
      titleInputRef.current.focus()
      titleInputRef.current.select()
    }
  }, [isEditingTitle])

  React.useEffect(() => {
    const el = chatScrollRef.current
    if (!el) return
    const handleScroll = () => {
      setShowScrollTop(el.scrollTop > 300)
    }
    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  const handleCartUpdateQuantity = (id: string, quantity: number) => {
    setCartItems(prev => prev.map(item => item.id === id ? { ...item, quantity } : item))
    toast.success('数量已更新')
  }

  const handleCartRemoveItem = (id: string) => {
    setCartItems(prev => prev.filter(item => item.id !== id))
    toast.success('已移除商品')
  }

  const handleAddToCart = (product: Product) => {
    const firstSku = product.skus[0]
    const skuLabel = firstSku ? Object.values(firstSku.properties).join(' / ') : '默认规格'
    const skuPrice = firstSku?.price ?? product.base_price
    setCartItems(prev => {
      const cartId = `cart-${product.id}-${firstSku?.sku_id ?? 'default'}`
      const existing = prev.find(item => item.id === cartId)
      if (existing) {
        return prev.map(item =>
          item.id === cartId
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      return [...prev, {
        id: cartId,
        title: product.title,
        sku: skuLabel,
        price: skuPrice,
        quantity: 1,
        image: product.image,
      }]
    })
    toast.success('已加入购物车')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const now = new Date()
    const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp,
    }

    setSessions(prev => prev.map(session => 
      session.id === activeSessionId 
        ? { ...session, messages: [...session.messages, userMessage], preview: input.trim() }
        : session
    ))
    setInput('')
    setIsLoading(true)

    const streamingMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp,
      isStreaming: true,
    }

    setSessions(prev => prev.map(session => 
      session.id === activeSessionId 
        ? { ...session, messages: [...session.messages, streamingMessage] }
        : session
    ))

    const responseText = '好的，让我帮你分析一下这个需求。根据你的描述和偏好，我为你推荐以下几款产品，它们都有很好的用户评价和性价比。'
    for (let i = 0; i <= responseText.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 30))
      setSessions(prev => prev.map(session => 
        session.id === activeSessionId 
          ? { 
              ...session, 
              messages: session.messages.map(msg => 
                msg.id === streamingMessage.id 
                  ? { ...msg, content: responseText.slice(0, i) }
                  : msg
              )
            }
          : session
      ))
    }

    setSessions(prev => prev.map(session => 
      session.id === activeSessionId 
        ? { 
            ...session, 
            messages: session.messages.map(msg => 
              msg.id === streamingMessage.id 
                ? { ...msg, isStreaming: false }
                : msg
            )
          }
        : session
    ))
    setIsLoading(false)
  }

  const handleNewChat = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: '新对话',
      preview: '新对话',
      timestamp: '刚刚',
      isActive: true,
      messages: [],
    }
    setSessions(prev => [newSession, ...prev])
    setActiveSessionId(newSession.id)
    setSidebarOpen(false)
  }

  const handleSelectSession = (id: string) => {
    setActiveSessionId(id)
    setSidebarOpen(false)
  }

  const handleCategoryClick = (category: string) => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: `${category}推荐`,
      preview: `${category}推荐`,
      timestamp: '刚刚',
      isActive: true,
      messages: [
        {
          id: 'category-prompt',
          role: 'user',
          content: `我想了解一下${category}类目有什么好的推荐`,
          timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        },
      ],
    }
    setSessions(prev => [newSession, ...prev])
    setActiveSessionId(newSession.id)
    setSidebarOpen(false)
  }

  const handleVoiceToggle = () => {
    setIsVoiceActive(!isVoiceActive)
  }

  const handleTitleDoubleClick = () => {
    setEditedTitle(sessionTitle)
    setIsEditingTitle(true)
  }

  const handleTitleSave = () => {
    if (editedTitle.trim()) {
      setSessions(prev => prev.map(session => 
        session.id === activeSessionId 
          ? { ...session, title: editedTitle.trim() }
          : session
      ))
    }
    setIsEditingTitle(false)
  }

  const handleTitleCancel = () => {
    setIsEditingTitle(false)
  }

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTitleSave()
    } else if (e.key === 'Escape') {
      handleTitleCancel()
    }
  }

  const handleProductClick = (product: Product) => {
    setSelectedProduct(product)
    setIsProductModalOpen(true)
  }

  const sidebarContent = (
    <ChatSidebar
      sessions={sessions}
      activeSessionId={activeSessionId}
      onNewChat={handleNewChat}
      onSelectSession={handleSelectSession}
      onCategoryClick={handleCategoryClick}
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
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-lg border-b border-border px-4 py-3">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="size-5" />
              <span className="sr-only">打开菜单</span>
            </Button>
            <div className="hidden lg:block w-10" />

            <div className="flex items-center gap-2">
              {isEditingTitle ? (
                <div className="flex items-center gap-1">
                  <Input
                    ref={titleInputRef}
                    value={editedTitle}
                    onChange={(e) => setEditedTitle(e.target.value)}
                    onKeyDown={handleTitleKeyDown}
                    className="h-8 w-40 text-center text-sm font-semibold"
                  />
                  <Button variant="ghost" size="icon" className="size-7" onClick={handleTitleSave}>
                    <Check className="size-4 text-green-600" />
                  </Button>
                  <Button variant="ghost" size="icon" className="size-7" onClick={handleTitleCancel}>
                    <X className="size-4 text-red-500" />
                  </Button>
                </div>
              ) : (
                <button
                  onDoubleClick={handleTitleDoubleClick}
                  className="flex items-center gap-2 hover:bg-muted px-3 py-1.5 rounded-lg transition-colors group"
                >
                  <h2 className="font-semibold text-foreground">{sessionTitle}</h2>
                  <Pencil className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                <ImagePlus className="size-5" />
                <span className="sr-only">上传图片</span>
              </Button>
              <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                <Mic className="size-5" />
                <span className="sr-only">语音输入</span>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="relative text-muted-foreground hover:text-foreground"
                onClick={() => setCartOpen(true)}
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

        <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="size-16 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center mb-4">
                  <Bot className="size-8 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">开始新对话</h3>
                <p className="text-muted-foreground text-sm max-w-sm">
                  告诉我你想买什么，或者描述你的需求，我会帮你找到最合适的商品推荐！
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
                  message.role === 'user' ? "justify-end" : "justify-start"
                )}
                style={{ animationDelay: `${index * 50}ms` }}
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
                            onClick={() => handleProductClick(product)}
                            onAddToCart={() => handleAddToCart(product)}
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-2 px-1">
                    <span className="text-xs text-muted-foreground">{message.timestamp}</span>
                    {message.role === 'assistant' && !message.isStreaming && (
                      <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                        <Volume2 className="size-3" />
                        播报
                      </button>
                    )}
                  </div>
                </div>

                {message.role === 'user' && <div className="w-8 flex-shrink-0" />}
              </div>
            ))}
            
            {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
              <div className="flex gap-3 justify-start animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
                <div className="flex-shrink-0 size-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                  <Bot className="size-4 text-white" />
                </div>
                <div className="bg-[#f0f0f5] dark:bg-zinc-800 rounded-2xl rounded-bl-sm px-4 py-3">
                  <div className="flex gap-1">
                    <span className="size-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="size-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="size-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {showScrollTop && (
            <Button
              variant="outline"
              size="icon"
              className="fixed bottom-24 right-6 z-20 size-10 rounded-full shadow-lg bg-background border-border hover:bg-muted"
              onClick={() => chatScrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
            >
              <ArrowUp className="size-4" />
              <span className="sr-only">回到顶部</span>
            </Button>
          )}
        </div>

        <div className="sticky bottom-0 bg-background/80 backdrop-blur-lg border-t border-border p-4">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            <div className="flex items-center gap-2 bg-card border border-border rounded-full px-4 py-2 shadow-lg">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-9 text-muted-foreground hover:text-foreground flex-shrink-0"
              >
                <ImagePlus className="size-5" />
                <span className="sr-only">上传图片</span>
              </Button>

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className={cn(
                  "size-9 flex-shrink-0 transition-colors",
                  isVoiceActive 
                    ? "text-red-500 hover:text-red-600" 
                    : "text-muted-foreground hover:text-foreground"
                )}
                onClick={handleVoiceToggle}
              >
                {isVoiceActive ? <StopCircle className="size-5" /> : <Mic className="size-5" />}
                <span className="sr-only">{isVoiceActive ? '停止录音' : '语音输入'}</span>
              </Button>

              {isVoiceActive ? (
                <div className="flex-1 flex items-center gap-2 px-2">
                  <span className="size-2.5 bg-red-500 rounded-full animate-pulse" />
                  <span className="text-sm text-muted-foreground">正在聆听...</span>
                </div>
              ) : (
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="问我任何购物问题..."
                  disabled={isLoading}
                  className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 px-0 h-9 text-sm"
                />
              )}

              <Button
                type="submit"
                disabled={isLoading || !input.trim() || isVoiceActive}
                size="icon"
                className={cn(
                  "size-9 rounded-full flex-shrink-0 transition-all",
                  input.trim() && !isLoading && !isVoiceActive
                    ? "bg-purple-600 hover:bg-purple-500 text-white"
                    : "bg-muted text-muted-foreground"
                )}
              >
                <Send className="size-4" />
                <span className="sr-only">发送</span>
              </Button>
            </div>
          </form>
        </div>
      </main>

      <ProductDetailModal
        product={selectedProduct}
        open={isProductModalOpen}
        onOpenChange={setIsProductModalOpen}
      />

      <ShoppingCartDrawer
        open={cartOpen}
        onOpenChange={setCartOpen}
        items={cartItems}
        onUpdateQuantity={handleCartUpdateQuantity}
        onRemoveItem={handleCartRemoveItem}
      />
    </div>
  )
}

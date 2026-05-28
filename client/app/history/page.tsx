'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowLeft,
  Search,
  Calendar,
  Package,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface HistoryCard {
  id: string
  title: string
  userPreview: string
  aiPreview: string
  date: string
  itemCount: number
  category: string
  thumbnail: string
}

const demoHistory: HistoryCard[] = [
  {
    id: 'h1',
    title: '推荐好用的护肤品',
    userPreview: '推荐一些好用的护肤品和数码产品',
    aiPreview: '为你找到以下热门商品，涵盖护肤和数码领域...',
    date: '2026-05-25',
    itemCount: 3,
    category: '美妆护肤',
    thumbnail: '/data/1_美妆护肤/images/p_beauty_001_live.jpg',
  },
  {
    id: 'h2',
    title: '性价比高的手机推荐',
    userPreview: '想买一款性价比高的手机',
    aiPreview: '为你推荐以下高性价比智能手机...',
    date: '2026-05-24',
    itemCount: 2,
    category: '数码电子',
    thumbnail: '/data/2_数码电子/images/p_digital_001_live.jpg',
  },
  {
    id: 'h3',
    title: '出差需要买哪些东西',
    userPreview: '出差需要买哪些东西',
    aiPreview: '出差必备好物清单来了，涵盖收纳...',
    date: '2026-05-24',
    itemCount: 5,
    category: '跨类目',
    thumbnail: '/data/2_数码电子/images/p_digital_002_live.jpg',
  },
  {
    id: 'h4',
    title: '夏天穿的透气T恤',
    userPreview: '夏天穿的透气T恤有哪些推荐',
    aiPreview: '这几款T恤透气清凉，非常适合夏天...',
    date: '2026-05-23',
    itemCount: 4,
    category: '服饰运动',
    thumbnail: '/data/3_服饰运动/images/p_clothes_001_live.jpg',
  },
  {
    id: 'h5',
    title: '热门零食推荐',
    userPreview: '有什么好吃又实惠的零食推荐',
    aiPreview: '为你筛选了以下好吃又实惠的零食...',
    date: '2026-05-22',
    itemCount: 2,
    category: '食品饮料',
    thumbnail: '/data/4_食品饮料/images/p_food_001_live.jpg',
  },
  {
    id: 'h6',
    title: '抗初老精华推荐',
    userPreview: '25岁用什么抗初老精华好',
    aiPreview: '为你推荐以下适合25+的抗初老精华...',
    date: '2026-05-21',
    itemCount: 3,
    category: '美妆护肤',
    thumbnail: '/data/1_美妆护肤/images/p_beauty_002_live.jpg',
  },
]

function HistoryCardItem({ card, onClick }: { card: HistoryCard; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-border overflow-hidden hover:shadow-md transition-shadow bg-card"
    >
      <div className="h-1 bg-gradient-to-r from-purple-500 to-indigo-500" />
      <div className="p-4 space-y-3">
        <h3 className="text-sm font-medium line-clamp-2 text-foreground">{card.userPreview}</h3>
        <p className="text-xs text-muted-foreground line-clamp-1">{card.aiPreview}</p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="size-3" />
              {card.date}
            </span>
            <span className="flex items-center gap-1">
              <Package className="size-3" />
              {card.itemCount}件商品
            </span>
          </div>
          <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
            <img
              src={card.thumbnail}
              alt={card.title}
              className="w-full h-full object-cover"
            />
          </div>
        </div>
      </div>
    </button>
  )
}

export default function HistoryPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = React.useState('')

  const filteredCards = demoHistory.filter(card => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      card.userPreview.toLowerCase().includes(q) ||
      card.aiPreview.toLowerCase().includes(q) ||
      card.category.toLowerCase().includes(q)
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

        {filteredCards.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Search className="size-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">没有找到匹配的对话</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredCards.map((card) => (
              <HistoryCardItem
                key={card.id}
                card={card}
                onClick={() => router.push('/chat')}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

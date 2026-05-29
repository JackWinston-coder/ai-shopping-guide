export interface Sku {
  sku_id: string
  properties: Record<string, string>
  price: number
}

export interface OfficialFaq {
  question: string
  answer: string
}

export interface UserReview {
  nickname: string
  rating: number
  content: string
}

export interface RagKnowledge {
  marketing_description: string
  official_faq: OfficialFaq[]
  user_reviews: UserReview[]
}

export interface Product {
  id: string
  title: string
  brand: string
  category: string
  sub_category: string
  base_price: number
  image: string
  skus: Sku[]
  rag_knowledge: RagKnowledge
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  products?: Product[]
  isStreaming?: boolean
  toolResults?: unknown[]
}

export interface ChatSession {
  id: string
  serverSessionId?: string
  title: string
  preview: string
  timestamp: string
  isActive: boolean
  messages: Message[]
}

export interface CartItem {
  id: string
  title: string
  sku: string
  price: number
  quantity: number
  image: string
}

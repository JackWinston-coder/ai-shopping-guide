import type { CartItem, ChatSession, Message, Product } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8010'
const TOKEN_KEY = 'ai-shopping-guide-token'

type StreamEvent =
  | { type: 'session'; data: { session_id?: string } }
  | { type: 'text_delta'; data: { content?: string } }
  | { type: 'product_cards'; data: { products?: BackendProduct[] } }
  | { type: 'tool_result'; data: { tool?: string; result?: unknown } }
  | { type: 'done'; data: Record<string, unknown> }
  | { type: 'error'; data: { code?: string; message?: string } }

interface BackendProduct {
  product_id: string
  title: string
  brand: string
  category: string
  sub_category: string
  base_price: number
  image_path?: string
  skus?: Product['skus']
  rag_knowledge?: Product['rag_knowledge']
}

interface BackendCartItem {
  id: string
  title: string
  sku_label: string
  price: number
  quantity: number
  image_path?: string | null
}

interface BackendSessionMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  products_json?: string | null
  tool_calls_json?: string | null
  created_at?: string | null
}

interface BackendChatSession {
  id: string
  title: string
  state?: string
  summary_text?: string | null
  updated_at?: string | null
  messages?: BackendSessionMessage[]
}

export function getApiBase() {
  return API_BASE
}

export function getStoredToken() {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY)
}

export async function login(credentials: { phone?: string; email?: string; password: string }) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.message || data.detail || '登录失败')
  }
  const data = await response.json()
  storeToken(data.access_token)
  return data.access_token as string
}

export async function register(payload: { phone?: string; email?: string; password: string; nickname?: string }) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.message || data.detail || '注册失败')
  }
  const data = await response.json()
  storeToken(data.access_token)
  return data.access_token as string
}

export async function ensureToken() {
  const existing = getStoredToken()
  if (existing) return existing
  throw new Error('请先登录')
}

async function authedFetch(path: string, init: RequestInit = {}) {
  const token = await ensureToken()
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (response.status === 401) {
    clearToken()
    throw new Error('登录已过期，请重新登录')
  }
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `请求失败：${response.status}`)
  }
  return response
}

export function mapProduct(product: BackendProduct): Product {
  return {
    id: product.product_id,
    title: product.title,
    brand: product.brand,
    category: product.category,
    sub_category: product.sub_category,
    base_price: product.base_price,
    image: product.image_path ? `/data/${product.image_path}` : '/placeholder.jpg',
    skus: product.skus || [],
    rag_knowledge: product.rag_knowledge || {
      marketing_description: '',
      official_faq: [],
      user_reviews: [],
    },
  }
}

function mapCartItem(item: BackendCartItem): CartItem {
  return {
    id: item.id,
    title: item.title,
    sku: item.sku_label,
    price: item.price,
    quantity: item.quantity,
    image: item.image_path ? `/data/${item.image_path}` : '/placeholder.jpg',
  }
}

function formatTimestamp(raw?: string | null) {
  if (!raw) return '刚刚'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return date.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function tryParseProducts(raw?: string | null): Product[] | undefined {
  if (!raw) return undefined
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return undefined
    return parsed.map(mapProduct)
  } catch {
    return undefined
  }
}

function tryParseToolResults(raw?: string | null): unknown[] | undefined {
  if (!raw) return undefined
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : [parsed]
  } catch {
    return undefined
  }
}

function mapMessage(message: BackendSessionMessage): Message {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    timestamp: formatTimestamp(message.created_at),
    products: tryParseProducts(message.products_json),
    toolResults: tryParseToolResults(message.tool_calls_json),
  }
}

function mapSession(session: BackendChatSession): ChatSession {
  return {
    id: session.id,
    serverSessionId: session.id,
    title: session.title,
    preview: session.summary_text || session.messages?.[session.messages.length - 1]?.content || '新对话',
    timestamp: formatTimestamp(session.updated_at),
    isActive: false,
    messages: (session.messages || []).map(mapMessage),
  }
}

export async function fetchCart() {
  const response = await authedFetch('/api/cart')
  const data = await response.json()
  return (data.items || []).map(mapCartItem) as CartItem[]
}

export async function fetchChatSessions() {
  const response = await authedFetch('/api/chat/sessions')
  const data = await response.json()
  return (data.items || []).map(mapSession) as ChatSession[]
}

export async function createChatSession(title = '新对话') {
  const response = await authedFetch('/api/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
  const data = await response.json()
  return mapSession(data as BackendChatSession)
}

export async function addCartItem(productId: string, skuId?: string, quantity = 1) {
  await authedFetch('/api/cart/items', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, sku_id: skuId, quantity }),
  })
  return fetchCart()
}

export async function updateCartItem(itemId: string, quantity: number) {
  await authedFetch(`/api/cart/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify({ quantity }),
  })
  return fetchCart()
}

export async function removeCartItem(itemId: string) {
  await authedFetch(`/api/cart/items/${itemId}`, { method: 'DELETE' })
  return fetchCart()
}

export async function previewOrder() {
  const response = await authedFetch('/api/orders/preview', { method: 'POST' })
  return response.json()
}

export async function createOrder(address: string) {
  const response = await authedFetch('/api/orders', {
    method: 'POST',
    body: JSON.stringify({ address }),
  })
  return response.json()
}

export async function streamChat(
  payload: { message: string; sessionId?: string; imageUrl?: string },
  onEvent: (event: StreamEvent) => void,
) {
  const token = await ensureToken()
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120_000)

  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: payload.message,
        session_id: payload.sessionId,
        image_url: payload.imageUrl,
      }),
      signal: controller.signal,
    })
    if (!response.ok || !response.body) {
      throw new Error('聊天接口请求失败')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split('\n\n')
      buffer = frames.pop() || ''

      for (const frame of frames) {
        const lines = frame.split('\n')
        const eventLine = lines.find((line) => line.startsWith('event: '))
        const dataLine = lines.find((line) => line.startsWith('data: '))
        if (!eventLine || !dataLine) continue
        const eventType = eventLine.slice(7).trim()
        const rawData = dataLine.slice(6)
        let parsedData: Record<string, unknown>
        try {
          parsedData = JSON.parse(rawData)
        } catch {
          continue
        }
        onEvent({
          type: eventType as StreamEvent['type'],
          data: parsedData,
        } as StreamEvent)
      }
    }
  } finally {
    clearTimeout(timeoutId)
  }
}

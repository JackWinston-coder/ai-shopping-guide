'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Check, Copy, MapPin, Package, Truck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import type { CartItem } from '@/lib/types'
import { createOrder, ensureToken, fetchCart, previewOrder } from '@/lib/api'

const DEFAULT_ADDRESS = '北京市朝阳区建国路88号 SOHO现代城 A座 1205'

export default function OrderConfirmPage() {
  const router = useRouter()
  const [items, setItems] = React.useState<CartItem[]>([])
  const [address, setAddress] = React.useState(DEFAULT_ADDRESS)
  const [totalPrice, setTotalPrice] = React.useState(0)
  const [loading, setLoading] = React.useState(true)
  const [submitting, setSubmitting] = React.useState(false)
  const [orderNo, setOrderNo] = React.useState('')
  const [copied, setCopied] = React.useState(false)

  React.useEffect(() => {
    ensureToken()
      .then(() => Promise.all([fetchCart(), previewOrder()]))
      .then(([cart, preview]) => {
        setItems(cart)
        setTotalPrice(preview.total_price || 0)
      })
      .catch((error) => toast.error(error instanceof Error ? error.message : '加载订单失败'))
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const order = await createOrder(address)
      setOrderNo(order.order_no)
      setItems([])
      toast.success('订单提交成功')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '订单提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCopy = () => {
    if (!orderNo) return
    navigator.clipboard.writeText(orderNo)
    setCopied(true)
    toast.success('订单号已复制')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Button variant="ghost" size="icon" onClick={() => router.push('/chat')}>
            <ArrowLeft className="size-5" />
            <span className="sr-only">返回</span>
          </Button>
          <h1 className="text-lg font-semibold text-foreground">确认订单</h1>
        </div>

        {orderNo ? (
          <div className="flex flex-col items-center gap-6 py-12">
            <div className="size-20 rounded-full bg-green-500 flex items-center justify-center">
              <Check className="size-10 text-white" strokeWidth={3} />
            </div>
            <h2 className="text-2xl font-bold text-foreground">下单成功！</h2>
            <div className="w-full max-w-sm bg-card border border-border rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">订单号</span>
                <div className="flex items-center gap-2 min-w-0">
                  <code className="text-sm font-mono font-medium text-foreground truncate">{orderNo}</code>
                  <Button variant="ghost" size="icon" className="size-7" onClick={handleCopy}>
                    {copied ? <Check className="size-3.5 text-green-500" /> : <Copy className="size-3.5" />}
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">订单金额</span>
                <span className="text-sm font-bold text-red-500">¥{totalPrice}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Truck className="size-4" />
              <span>预计3-5个工作日送达 (模拟)</span>
            </div>
            <Button className="w-full max-w-sm h-11 rounded-lg" onClick={() => router.push('/chat')}>
              返回对话
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            <section>
              <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
                <MapPin className="size-4 text-purple-600" />
                收货地址
              </h2>
              <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-medium text-foreground">张三</span>
                  <span className="text-muted-foreground">138****8888</span>
                </div>
                <Input value={address} onChange={(e) => setAddress(e.target.value)} />
              </div>
            </section>

            <section>
              <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
                <Package className="size-4 text-purple-600" />
                商品清单
              </h2>
              <div className="bg-card border border-border rounded-xl divide-y divide-border">
                {loading ? (
                  <div className="p-4 text-sm text-muted-foreground">正在加载订单...</div>
                ) : items.length === 0 ? (
                  <div className="p-4 text-sm text-muted-foreground">购物车为空，请先返回对话添加商品。</div>
                ) : (
                  items.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 p-4">
                      <div className="w-12 h-12 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
                        <img src={item.image} alt={item.title} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium line-clamp-1">{item.title}</h4>
                        <p className="text-xs text-muted-foreground">{item.sku}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm text-red-500 font-medium">¥{item.price * item.quantity}</p>
                        <p className="text-xs text-muted-foreground">x{item.quantity}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="bg-card border border-border rounded-xl p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">商品合计</span>
                <span className="text-foreground">¥{totalPrice}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">运费</span>
                <span className="text-green-600">免运费</span>
              </div>
              <div className="border-t border-border pt-3 flex justify-between items-center">
                <span className="font-bold text-foreground">应付金额</span>
                <span className="text-2xl font-bold text-red-500">¥{totalPrice}</span>
              </div>
            </section>

            <div className="sticky bottom-0 bg-background border-t border-border -mx-4 px-4 py-4">
              <Button
                className="w-full h-12 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-lg"
                onClick={handleSubmit}
                disabled={loading || submitting || items.length === 0 || !address.trim()}
              >
                {submitting ? '提交中...' : '提交订单'}
              </Button>
              <p className="text-xs text-center text-muted-foreground mt-2">
                提交后将生成模拟订单，不涉及真实支付
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

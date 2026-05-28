'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowLeft,
  MapPin,
  Phone,
  Plus,
  Copy,
  Check,
  Package,
  Truck,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { motion, AnimatePresence } from 'framer-motion'
import type { CartItem } from '@/lib/types'

const demoCartItems: CartItem[] = [
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

const ORDER_NO = 'ORD-20260525-A7X3'

function StepIndicator({ currentStep }: { currentStep: number }) {
  const steps = [
    { label: '确认地址', icon: MapPin },
    { label: '确认商品', icon: Package },
    { label: '下单成功', icon: Check },
  ]

  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {steps.map((step, index) => {
        const isCompleted = index < currentStep
        const isActive = index === currentStep
        const isPending = index > currentStep
        const Icon = step.icon

        return (
          <React.Fragment key={step.label}>
            {index > 0 && (
              <div className={cn(
                "w-12 h-0.5 mx-1",
                isCompleted ? "bg-purple-600" : "bg-border"
              )} />
            )}
            <div className="flex flex-col items-center gap-1.5">
              <div className={cn(
                "size-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                isCompleted ? "bg-purple-600 text-white" :
                isActive ? "bg-purple-600 text-white" :
                "bg-muted text-muted-foreground"
              )}>
                {isCompleted ? <Check className="size-4" /> : <Icon className="size-4" />}
              </div>
              <span className={cn(
                "text-xs whitespace-nowrap",
                isActive || isCompleted ? "text-foreground font-medium" : "text-muted-foreground"
              )}>
                {step.label}
              </span>
            </div>
          </React.Fragment>
        )
      })}
    </div>
  )
}

function ConfettiParticle({ delay, x, color }: { delay: number; x: number; color: string }) {
  return (
    <motion.div
      className="absolute size-2 rounded-full"
      style={{ backgroundColor: color, left: `${x}%`, top: '30%' }}
      initial={{ opacity: 1, y: 0, scale: 1 }}
      animate={{
        opacity: 0,
        y: -200 - Math.random() * 100,
        x: (Math.random() - 0.5) * 200,
        scale: 0.5,
        rotate: Math.random() * 360,
      }}
      transition={{ duration: 1.5, delay, ease: 'easeOut' }}
    />
  )
}

function SuccessView() {
  const router = useRouter()
  const [copied, setCopied] = React.useState(false)
  const [showConfetti, setShowConfetti] = React.useState(true)

  React.useEffect(() => {
    const timer = setTimeout(() => setShowConfetti(false), 3000)
    return () => clearTimeout(timer)
  }, [])

  const handleCopy = () => {
    navigator.clipboard.writeText(ORDER_NO)
    setCopied(true)
    toast.success('订单号已复制')
    setTimeout(() => setCopied(false), 2000)
  }

  const confettiColors = ['#8B5CF6', '#6366F1', '#EC4899', '#F59E0B', '#10B981', '#3B82F6']

  return (
    <div className="relative overflow-hidden">
      {showConfetti && (
        <div className="absolute inset-0 pointer-events-none">
          {Array.from({ length: 30 }).map((_, i) => (
            <ConfettiParticle
              key={i}
              delay={Math.random() * 0.5}
              x={Math.random() * 100}
              color={confettiColors[i % confettiColors.length]}
            />
          ))}
        </div>
      )}

      <div className="flex flex-col items-center gap-6 py-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
          className="size-20 rounded-full bg-green-500 flex items-center justify-center"
        >
          <motion.div
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.5, delay: 0.5 }}
          >
            <Check className="size-10 text-white" strokeWidth={3} />
          </motion.div>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-2xl font-bold text-foreground"
        >
          下单成功！
        </motion.h2>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="w-full max-w-sm bg-card border border-border rounded-xl p-4 space-y-3"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">订单号</span>
            <div className="flex items-center gap-2">
              <code className="text-sm font-mono font-medium text-foreground">{ORDER_NO}</code>
              <Button variant="ghost" size="icon" className="size-7" onClick={handleCopy}>
                {copied ? <Check className="size-3.5 text-green-500" /> : <Copy className="size-3.5" />}
              </Button>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">商品数量</span>
            <span className="text-sm text-foreground">2件</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">订单金额</span>
            <span className="text-sm font-bold text-red-500">¥634</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <Truck className="size-4" />
          <span>预计3-5个工作日送达 (模拟)</span>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
          className="flex gap-3 w-full max-w-sm"
        >
          <Button
            variant="outline"
            className="flex-1 h-11 rounded-lg"
            onClick={() => router.push('/chat')}
          >
            返回对话
          </Button>
          <Button
            className="flex-1 h-11 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-lg"
            onClick={() => router.push('/chat')}
          >
            查看订单
          </Button>
        </motion.div>
      </div>
    </div>
  )
}

export default function OrderConfirmPage() {
  const router = useRouter()
  const [isSubmitted, setIsSubmitted] = React.useState(false)

  const subtotal = demoCartItems.reduce((sum, item) => sum + item.price * item.quantity, 0)

  const handleSubmit = () => {
    setIsSubmitted(true)
    toast.success('订单提交成功')
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="size-5" />
            <span className="sr-only">返回</span>
          </Button>
          <h1 className="text-lg font-semibold text-foreground">确认订单</h1>
        </div>

        <StepIndicator currentStep={isSubmitted ? 2 : 1} />

        <AnimatePresence mode="wait">
          {!isSubmitted ? (
            <motion.div
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              <section>
                <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
                  <MapPin className="size-4 text-purple-600" />
                  收货地址
                </h2>
                <div className="bg-card border border-border rounded-xl p-4">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="font-medium text-foreground">张三</span>
                        <span className="text-sm text-muted-foreground">138****8888</span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        北京市朝阳区建国路88号 SOHO现代城 A座 1205
                      </p>
                    </div>
                    <Button variant="link" className="text-purple-600 dark:text-purple-400 text-sm p-0 h-auto">
                      修改
                    </Button>
                  </div>
                </div>
                <Button variant="outline" className="mt-3 w-full border-dashed">
                  <Plus className="size-4 mr-2" />
                  使用新地址
                </Button>
              </section>

              <section>
                <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
                  <Package className="size-4 text-purple-600" />
                  商品清单
                </h2>
                <div className="bg-card border border-border rounded-xl divide-y divide-border">
                  {demoCartItems.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 p-4">
                      <div className="w-12 h-12 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
                        <img
                          src={item.image}
                          alt={item.title}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium line-clamp-1">{item.title}</h4>
                        <p className="text-xs text-muted-foreground">{item.sku}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm text-red-500 font-medium">¥{item.price * item.quantity}</p>
                        <p className="text-xs text-muted-foreground">×{item.quantity}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
                  <ChevronRight className="size-4 text-purple-600" />
                  金额汇总
                </h2>
                <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">商品合计</span>
                    <span className="text-foreground">¥{subtotal}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">运费</span>
                    <span className="text-green-600">¥0 (免运费)</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">优惠</span>
                    <span className="text-foreground">-¥0</span>
                  </div>
                  <div className="border-t border-border pt-3 flex justify-between items-center">
                    <span className="font-bold text-foreground">应付金额</span>
                    <span className="text-2xl font-bold text-red-500">¥{subtotal}</span>
                  </div>
                </div>
              </section>
            </motion.div>
          ) : (
            <motion.div
              key="success"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <StepIndicator currentStep={2} />
              <SuccessView />
            </motion.div>
          )}
        </AnimatePresence>

        {!isSubmitted && (
          <div className="sticky bottom-0 bg-background border-t border-border -mx-4 px-4 py-4 mt-6">
            <Button
              className="w-full h-12 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-lg"
              onClick={handleSubmit}
            >
              提交订单
            </Button>
            <p className="text-xs text-center text-muted-foreground mt-2">
              提交后将生成模拟订单，不涉及真实支付
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

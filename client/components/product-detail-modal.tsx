'use client'

import * as React from 'react'
import { Star, ShoppingCart, Minus, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { cn } from '@/lib/utils'
import type { Product, Sku } from '@/lib/types'

interface ProductDetailModalProps {
  product: Product | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAddToCart?: (product: Product) => void | Promise<void>
}

export function ProductDetailModal({
  product,
  open,
  onOpenChange,
  onAddToCart,
}: ProductDetailModalProps) {
  const [selectedSku, setSelectedSku] = React.useState<Sku | null>(null)
  const [quantity, setQuantity] = React.useState(1)

  React.useEffect(() => {
    if (open && product && product.skus.length > 0) {
      setSelectedSku(product.skus[0])
      setQuantity(1)
    }
  }, [open, product?.id])

  if (!product) return null

  const currentPrice = selectedSku?.price ?? product.base_price
  const avgRating = product.rag_knowledge.user_reviews.length > 0
    ? (product.rag_knowledge.user_reviews.reduce((sum, r) => sum + r.rating, 0) / product.rag_knowledge.user_reviews.length).toFixed(1)
    : '暂无'

  const skuPropertyKeys = product.skus.length > 0
    ? Object.keys(product.skus[0].properties)
    : []

  const skuOptionsByProperty: Record<string, string[]> = {}
  skuPropertyKeys.forEach(key => {
    skuOptionsByProperty[key] = [...new Set(product.skus.map(s => s.properties[key]))]
  })

  const [selectedProperties, setSelectedProperties] = React.useState<Record<string, string>>({})

  React.useEffect(() => {
    if (open && product && product.skus.length > 0) {
      setSelectedProperties({ ...product.skus[0].properties })
      setQuantity(1)
    }
  }, [open, product?.id])

  React.useEffect(() => {
    const matched = product.skus.find(sku =>
      skuPropertyKeys.every(key => sku.properties[key] === selectedProperties[key])
    )
    setSelectedSku(matched ?? product.skus[0] ?? null)
  }, [selectedProperties, product])

  const handlePropertySelect = (key: string, value: string) => {
    setSelectedProperties(prev => ({ ...prev, [key]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="max-w-4xl max-h-[90vh] overflow-y-auto p-0 gap-0 data-[state=open]:animate-in data-[state=open]:zoom-in-95 data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:zoom-out-95 data-[state=closed]:fade-out-0 duration-200"
      >
        <DialogTitle className="sr-only">{product.title} - 商品详情</DialogTitle>
        
        <button
          onClick={() => onOpenChange(false)}
          className="absolute top-4 right-4 z-10 size-9 rounded-full bg-muted/80 hover:bg-muted flex items-center justify-center transition-colors"
        >
          <X className="size-4" />
          <span className="sr-only">关闭</span>
        </button>

        <div className="grid md:grid-cols-2 gap-6 p-6">
          <div className="space-y-4">
            <div className="aspect-square rounded-lg overflow-hidden bg-muted">
              <img
                src={product.image}
                alt={product.title}
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          <div className="space-y-4">
            <p className="text-sm text-muted-foreground uppercase tracking-wide">
              {product.brand}
            </p>

            <h2 className="text-2xl font-bold text-foreground">
              {product.title}
            </h2>

            <div className="flex items-center gap-3">
              <span className="text-3xl font-bold text-red-500">
                ¥{currentPrice}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 dark:bg-purple-950 dark:text-purple-300">
                {product.category} · {product.sub_category}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    className={cn(
                      "size-4",
                      star <= Math.round(Number(avgRating))
                        ? "fill-yellow-400 text-yellow-400"
                        : "fill-muted text-muted"
                    )}
                  />
                ))}
              </div>
              <span className="text-sm text-muted-foreground">
                {avgRating} ({product.rag_knowledge.user_reviews.length}条评价)
              </span>
            </div>

            <hr className="border-border" />

            <div className="space-y-4">
              {skuPropertyKeys.map((key) => (
                <div key={key} className="space-y-2">
                  <label className="text-sm font-medium text-foreground">{key}</label>
                  <div className="flex flex-wrap gap-2">
                    {skuOptionsByProperty[key]?.map((value) => (
                      <button
                        key={value}
                        onClick={() => handlePropertySelect(key, value)}
                        className={cn(
                          "px-4 py-2 rounded-full text-sm transition-colors",
                          selectedProperties[key] === value
                            ? "bg-purple-600 text-white"
                            : "bg-muted text-foreground hover:bg-muted/80"
                        )}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-foreground">数量</label>
              <div className="flex items-center border border-border rounded-lg">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="size-10 flex items-center justify-center hover:bg-muted transition-colors"
                  disabled={quantity <= 1}
                >
                  <Minus className="size-4" />
                </button>
                <span className="w-12 text-center font-medium">{quantity}</span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="size-10 flex items-center justify-center hover:bg-muted transition-colors"
                >
                  <Plus className="size-4" />
                </button>
              </div>
            </div>

            <Button
              className="w-full h-12 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-base font-medium"
              onClick={() => onAddToCart?.(product)}
            >
              <ShoppingCart className="size-5 mr-2" />
              加入购物车
            </Button>

            <hr className="border-border" />

            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="description">
                <AccordionTrigger className="text-base font-medium">
                  商品描述
                </AccordionTrigger>
                <AccordionContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {product.rag_knowledge.marketing_description}
                  </p>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="faq">
                <AccordionTrigger className="text-base font-medium">
                  常见问题
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4">
                    {product.rag_knowledge.official_faq.map((faq, index) => (
                      <div key={index} className="space-y-1">
                        <p className="text-sm font-medium text-foreground">
                          Q: {faq.question}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          A: {faq.answer}
                        </p>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="reviews">
                <AccordionTrigger className="text-base font-medium">
                  用户评价
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4">
                    {product.rag_knowledge.user_reviews.map((review, index) => (
                      <div
                        key={index}
                        className="p-3 bg-muted/50 rounded-lg space-y-2"
                      >
                        <div className="flex items-center gap-3">
                          <div className="size-8 rounded-full bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center text-xs font-medium text-purple-700 dark:text-purple-300">
                            {review.nickname.charAt(0)}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-medium">{review.nickname}</p>
                            <div className="flex">
                              {[1, 2, 3, 4, 5].map((star) => (
                                <Star
                                  key={star}
                                  className={cn(
                                    "size-3",
                                    star <= review.rating
                                      ? "fill-yellow-400 text-yellow-400"
                                      : "fill-muted text-muted"
                                  )}
                                />
                              ))}
                            </div>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {review.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

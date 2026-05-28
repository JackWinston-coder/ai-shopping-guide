'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import {
  ShoppingBag,
  ShoppingCart,
  X,
  Plus,
  Minus,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import type { CartItem } from '@/lib/types'

interface ShoppingCartDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  items: CartItem[]
  onUpdateQuantity: (id: string, quantity: number) => void
  onRemoveItem: (id: string) => void
}

function CartItemCard({
  item,
  onUpdateQuantity,
  onRemoveItem,
}: {
  item: CartItem
  onUpdateQuantity: (id: string, quantity: number) => void
  onRemoveItem: (id: string) => void
}) {
  const [isAnimating, setIsAnimating] = React.useState(false)

  const handleQuantityChange = (newQuantity: number) => {
    if (newQuantity < 1) return
    setIsAnimating(true)
    onUpdateQuantity(item.id, newQuantity)
    setTimeout(() => setIsAnimating(false), 150)
  }

  return (
    <div className="flex gap-3 p-3 bg-card rounded-lg border border-border">
      <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
        <img
          src={item.image}
          alt={item.title}
          className="w-full h-full object-cover"
          crossOrigin="anonymous"
        />
      </div>

      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium line-clamp-1">{item.title}</h4>
        <p className="text-xs text-muted-foreground mt-0.5">{item.sku}</p>
        <p className="text-sm text-red-500 font-medium mt-1">¥{item.price}</p>
      </div>

      <div className="flex flex-col items-center gap-0.5">
        <Button
          variant="ghost"
          size="icon"
          className="size-6 text-muted-foreground hover:text-foreground"
          onClick={() => handleQuantityChange(item.quantity + 1)}
        >
          <Plus className="size-3.5" />
        </Button>
        <span
          className={cn(
            "text-sm font-medium w-6 text-center transition-transform",
            isAnimating && "scale-125"
          )}
        >
          {item.quantity}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="size-6 text-muted-foreground hover:text-foreground"
          onClick={() => handleQuantityChange(item.quantity - 1)}
          disabled={item.quantity <= 1}
        >
          <Minus className="size-3.5" />
        </Button>
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="size-8 text-muted-foreground hover:text-red-500 self-center"
        onClick={() => onRemoveItem(item.id)}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  )
}

function EmptyCart({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 py-12">
      <div className="size-20 rounded-full bg-muted flex items-center justify-center">
        <ShoppingCart className="size-10 text-muted-foreground" />
      </div>
      <p className="text-muted-foreground">购物车是空的</p>
      <Button
        variant="link"
        className="text-purple-600 dark:text-purple-400"
        onClick={onClose}
      >
        去逛逛
      </Button>
    </div>
  )
}

export function ShoppingCartDrawer({
  open,
  onOpenChange,
  items,
  onUpdateQuantity,
  onRemoveItem,
}: ShoppingCartDrawerProps) {
  const router = useRouter()
  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0)
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0)

  const handleCheckout = () => {
    onOpenChange(false)
    router.push('/order/confirm')
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:w-[400px] sm:max-w-[400px] p-0 flex flex-col"
      >
        <SheetHeader className="px-4 py-4 border-b border-border flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShoppingBag className="size-5 text-purple-600 dark:text-purple-400" />
              <SheetTitle className="text-lg font-semibold">购物车</SheetTitle>
              {totalItems > 0 && (
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300">
                  {totalItems}件商品
                </span>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={() => onOpenChange(false)}
            >
              <X className="size-4" />
              <span className="sr-only">关闭</span>
            </Button>
          </div>
        </SheetHeader>

        {items.length === 0 ? (
          <EmptyCart onClose={() => onOpenChange(false)} />
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {items.map((item) => (
                <CartItemCard
                  key={item.id}
                  item={item}
                  onUpdateQuantity={onUpdateQuantity}
                  onRemoveItem={onRemoveItem}
                />
              ))}
            </div>

            <div className="flex-shrink-0 border-t border-border p-4 bg-background space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">商品合计</span>
                  <span className="text-foreground">¥{subtotal}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">运费</span>
                  <span className="text-green-600">免运费</span>
                </div>
                <div className="border-t border-border pt-2 flex justify-between items-center">
                  <span className="font-bold text-foreground">合计</span>
                  <span className="text-xl font-bold text-red-500">¥{subtotal}</span>
                </div>
              </div>

              <Button
                className="w-full h-12 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-lg"
                onClick={handleCheckout}
              >
                去结算
              </Button>

              <p className="text-xs text-center text-muted-foreground">
                仅模拟下单，不涉及真实支付
              </p>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

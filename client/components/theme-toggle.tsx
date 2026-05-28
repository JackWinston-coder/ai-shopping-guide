'use client'

import * as React from 'react'
import { useTheme } from 'next-themes'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ThemeToggleProps {
  variant?: 'default' | 'light'
}

export function ThemeToggle({ variant = 'default' }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const buttonClasses = cn(
    variant === 'light' 
      ? "text-white/80 hover:text-white hover:bg-white/10" 
      : "text-foreground hover:bg-accent"
  )

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className={buttonClasses}>
        <Sun className="size-5" />
        <span className="sr-only">切换主题</span>
      </Button>
    )
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className={buttonClasses}
    >
      {theme === 'dark' ? (
        <Sun className="size-5" />
      ) : (
        <Moon className="size-5" />
      )}
      <span className="sr-only">切换主题</span>
    </Button>
  )
}

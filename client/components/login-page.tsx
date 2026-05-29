'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { ShoppingBag, Sparkles, Phone, Mail, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ThemeToggle } from '@/components/theme-toggle'
import { login, register } from '@/lib/api'
import { toast } from 'sonner'

function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-purple-400/20 rounded-full blur-3xl animate-float" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-indigo-400/15 rounded-full blur-3xl animate-float-delay-1" />
      <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-violet-400/20 rounded-full blur-3xl animate-float-delay-2" />
      <div className="absolute bottom-1/3 right-1/3 w-80 h-80 bg-purple-500/15 rounded-full blur-3xl animate-float-delay-3" />
      <div className="absolute top-1/2 left-1/2 w-48 h-48 bg-indigo-300/20 rounded-full blur-3xl animate-float-delay-4" />
      <div className="absolute top-20 left-20 w-2 h-2 bg-white/40 rounded-full animate-float" />
      <div className="absolute top-40 right-32 w-1.5 h-1.5 bg-white/30 rounded-full animate-float-delay-1" />
      <div className="absolute bottom-32 left-40 w-2 h-2 bg-white/35 rounded-full animate-float-delay-2" />
      <div className="absolute bottom-40 right-20 w-1 h-1 bg-white/40 rounded-full animate-float-delay-3" />
      <div className="absolute top-1/2 left-16 w-1.5 h-1.5 bg-white/30 rounded-full animate-float-delay-4" />
    </div>
  )
}

function PhoneAuthForm({ mode }: { mode: 'login' | 'register' }) {
  const router = useRouter()
  const [phone, setPhone] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [confirmPassword, setConfirmPassword] = React.useState('')
  const [nickname, setNickname] = React.useState('')
  const [showPassword, setShowPassword] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'register' && password !== confirmPassword) {
      toast.error('两次输入的密码不一致')
      return
    }
    setIsLoading(true)
    try {
      if (mode === 'register') {
        await register({ phone, password, nickname: nickname || `用户${phone.slice(-4)}` })
      } else {
        await login({ phone, password })
      }
      router.push('/chat')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : (mode === 'login' ? '登录失败' : '注册失败'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-muted-foreground text-sm">
          <Phone className="size-4" />
          <span>+86</span>
        </div>
        <Input
          type="tel"
          placeholder="请输入手机号"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="pl-20 h-11 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
        />
      </div>

      <div className="relative">
        <Input
          type={showPassword ? 'text' : 'password'}
          placeholder="请输入密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="h-11 pr-10 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
        >
          {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>

      {mode === 'register' && (
        <>
          <div className="relative">
            <Input
              type={showPassword ? 'text' : 'password'}
              placeholder="确认密码"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="h-11 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
            />
          </div>
          <Input
            type="text"
            placeholder="昵称（选填）"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="h-11 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
          />
        </>
      )}

      <Button
        type="submit"
        disabled={isLoading || !phone || !password || (mode === 'register' && !confirmPassword)}
        className="w-full h-11 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium rounded-lg shadow-lg shadow-purple-500/25 transition-all duration-200 hover:shadow-xl hover:shadow-purple-500/30"
      >
        {isLoading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? '登 录' : '注 册')}
      </Button>
    </form>
  )
}

function EmailAuthForm({ mode }: { mode: 'login' | 'register' }) {
  const router = useRouter()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [confirmPassword, setConfirmPassword] = React.useState('')
  const [nickname, setNickname] = React.useState('')
  const [showPassword, setShowPassword] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'register' && password !== confirmPassword) {
      toast.error('两次输入的密码不一致')
      return
    }
    setIsLoading(true)
    try {
      if (mode === 'register') {
        await register({ email, password, nickname: nickname || email.split('@')[0] })
      } else {
        await login({ email, password })
      }
      router.push('/chat')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : (mode === 'login' ? '登录失败' : '注册失败'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
          <Mail className="size-4" />
        </div>
        <Input
          type="email"
          placeholder="请输入邮箱"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="pl-10 h-11 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
        />
      </div>

      <div className="relative">
        <Input
          type={showPassword ? 'text' : 'password'}
          placeholder="请输入密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="h-11 pr-10 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
        >
          {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>

      {mode === 'register' && (
        <>
          <div className="relative">
            <Input
              type={showPassword ? 'text' : 'password'}
              placeholder="确认密码"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="h-11 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
            />
          </div>
          <Input
            type="text"
            placeholder="昵称（选填）"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="h-11 bg-white/50 dark:bg-white/10 border-white/30 dark:border-white/20 focus:border-purple-400 focus:ring-purple-400/30 placeholder:text-muted-foreground/70 transition-all duration-200"
          />
        </>
      )}

      <Button
        type="submit"
        disabled={isLoading || !email || !password || (mode === 'register' && !confirmPassword)}
        className="w-full h-11 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium rounded-lg shadow-lg shadow-purple-500/25 transition-all duration-200 hover:shadow-xl hover:shadow-purple-500/30"
      >
        {isLoading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? '登 录' : '注 册')}
      </Button>
    </form>
  )
}

export function LoginCard() {
  const [mode, setMode] = React.useState<'login' | 'register'>('login')

  return (
    <div className="relative w-full max-w-md mx-auto">
      <div className="relative backdrop-blur-xl bg-white/70 dark:bg-slate-900/70 border border-white/40 dark:border-white/10 rounded-2xl shadow-2xl shadow-purple-900/20 p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center gap-2 mb-4">
            <div className="relative">
              <ShoppingBag className="size-10 text-purple-600 dark:text-purple-400" />
              <Sparkles className="size-5 text-indigo-500 dark:text-indigo-400 absolute -top-1 -right-1" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            AI Shopping Guide
          </h1>
          <p className="text-muted-foreground">
            你的智能购物伙伴
          </p>
        </div>

        <Tabs defaultValue="phone" className="w-full">
          <TabsList className="w-full bg-white/50 dark:bg-white/10 border border-white/30 dark:border-white/20 mb-6">
            <TabsTrigger
              value="phone"
              className="flex-1 data-[state=active]:bg-purple-600 data-[state=active]:text-white"
            >
              手机号{mode === 'login' ? '登录' : '注册'}
            </TabsTrigger>
            <TabsTrigger
              value="email"
              className="flex-1 data-[state=active]:bg-purple-600 data-[state=active]:text-white"
            >
              邮箱{mode === 'login' ? '登录' : '注册'}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="phone">
            <PhoneAuthForm mode={mode} />
          </TabsContent>

          <TabsContent value="email">
            <EmailAuthForm mode={mode} />
          </TabsContent>
        </Tabs>

        <div className="text-center mt-4">
          <button
            type="button"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            className="text-sm text-purple-600 dark:text-purple-400 hover:underline"
          >
            {mode === 'login' ? '没有账号？立即注册' : '已有账号？立即登录'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
      <div className="absolute top-4 right-4 z-20">
        <ThemeToggle variant="light" />
      </div>
      <FloatingParticles />
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <LoginCard />
      </div>
    </div>
  )
}

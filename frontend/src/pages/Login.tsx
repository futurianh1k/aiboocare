import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Heart, Mail, Lock, ArrowRight } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 데모 모드 - 바로 로그인
  const handleDemoLogin = () => {
    navigate('/')
  }

  return (
    <div className="min-h-screen flex">
      {/* 왼쪽 - 브랜딩 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary via-primary-dark to-secondary relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-64 h-64 bg-white rounded-full blur-3xl"></div>
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-white rounded-full blur-3xl"></div>
        </div>
        
        <div className="relative z-10 flex flex-col justify-center p-12">
          <div className="w-20 h-20 rounded-2xl bg-white/20 backdrop-blur-lg flex items-center justify-center mb-8">
            <Heart className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-5xl font-bold text-white mb-4">
            AI Care<br />Companion
          </h1>
          <p className="text-xl text-white/80 max-w-md">
            AI 기반 독거노인 돌봄 시스템으로<br />
            24시간 안심 케어를 제공합니다.
          </p>
          
          <div className="mt-12 grid grid-cols-3 gap-6">
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4">
              <p className="text-3xl font-bold text-white">1,234</p>
              <p className="text-sm text-white/70">돌봄 대상자</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4">
              <p className="text-3xl font-bold text-white">567</p>
              <p className="text-sm text-white/70">활성 디바이스</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4">
              <p className="text-3xl font-bold text-white">99.9%</p>
              <p className="text-sm text-white/70">가동률</p>
            </div>
          </div>
        </div>
      </div>

      {/* 오른쪽 - 로그인 폼 */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* 모바일 로고 */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
              <Heart className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">AI Care Companion</h1>
              <p className="text-sm text-text-muted">Care Console</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold mb-2">로그인</h2>
          <p className="text-text-secondary mb-8">운영자 계정으로 로그인하세요.</p>

          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger rounded-xl p-4 mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">이메일</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@example.com"
                  className="w-full pl-12"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">비밀번호</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-12"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary-dark text-white font-medium py-3 px-6 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  로그인
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="bg-bg-primary px-4 text-sm text-text-muted">또는</span>
            </div>
          </div>

          <button
            onClick={handleDemoLogin}
            className="w-full bg-bg-secondary hover:bg-bg-tertiary border border-border text-text-primary font-medium py-3 px-6 rounded-xl"
          >
            데모 모드로 둘러보기
          </button>

          <p className="text-center text-sm text-text-muted mt-8">
            © 2026 AI Care Companion. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  )
}

/**
 * 认证状态管理 (Pinia Store)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'
import { useRouter } from 'vue-router'

export interface User {
  id: number
  username: string
  email: string
  role: string
  created_at: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter()

  // ---- State ----
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(
    (() => {
      try {
        const raw = localStorage.getItem('user')
        return raw ? JSON.parse(raw) : null
      } catch {
        return null
      }
    })(),
  )
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- Getters ----
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username ?? '')

  // ---- Actions ----
  function setAuth(accessToken: string, userData: User) {
    token.value = accessToken
    user.value = userData
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }

  async function login(payload: LoginPayload) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post('/auth/login', payload)
      setAuth(data.access_token, data.user)
      // 根据角色导航
      if (data.user.role === 'admin') {
        await router.push('/admin')
      } else {
        await router.push('/dashboard')
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || '登录失败，请重试'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post('/auth/register', payload)
      setAuth(data.access_token, data.user)
      await router.push('/dashboard')
    } catch (err: any) {
      error.value = err.response?.data?.detail || '注册失败，请重试'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    clearAuth()
    await router.push('/login')
  }

  async function fetchMe() {
    try {
      const { data } = await api.get('/users/me')
      user.value = data
      localStorage.setItem('user', JSON.stringify(data))
    } catch {
      clearAuth()
    }
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    username,
    login,
    register,
    logout,
    fetchMe,
    clearAuth,
  }
})

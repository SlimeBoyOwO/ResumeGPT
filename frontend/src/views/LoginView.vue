<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = ref({
  username: '',
  password: '',
})

async function handleLogin() {
  try {
    await auth.login(form.value)
  } catch {
    // error 已在 store 中处理
  }
}
</script>

<template>
  <div class="animate-fade-in">
    <!-- 移动端 Logo -->
    <div class="lg:hidden flex items-center gap-3 mb-8">
      <div
        class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-lg font-bold"
      >
        R
      </div>
      <h1 class="text-xl font-bold text-surface-900">ResumeGPT</h1>
    </div>

    <h2 class="text-2xl font-bold text-surface-900 mb-2">欢迎回来</h2>
    <p class="text-surface-500 mb-8">请登录您的账号以继续使用</p>

    <!-- 错误提示 -->
    <div
      v-if="auth.error"
      class="mb-6 p-4 rounded-xl bg-danger-500/10 border border-danger-500/20 text-danger-600 text-sm flex items-center gap-2"
    >
      <span>⚠️</span>
      <span>{{ auth.error }}</span>
    </div>

    <form @submit.prevent="handleLogin" class="space-y-5">
      <div>
        <label for="login-username" class="block text-sm font-medium text-surface-700 mb-2">
          用户名
        </label>
        <input
          id="login-username"
          v-model="form.username"
          type="text"
          required
          autocomplete="username"
          placeholder="请输入用户名"
          class="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all duration-200"
        />
      </div>

      <div>
        <label for="login-password" class="block text-sm font-medium text-surface-700 mb-2">
          密码
        </label>
        <input
          id="login-password"
          v-model="form.password"
          type="password"
          required
          autocomplete="current-password"
          placeholder="请输入密码"
          class="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all duration-200"
        />
      </div>

      <button
        type="submit"
        :disabled="auth.loading"
        class="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white font-semibold text-sm shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 hover:from-primary-600 hover:to-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/40 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
      >
        <span v-if="auth.loading" class="flex items-center justify-center gap-2">
          <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
              fill="none"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          登录中...
        </span>
        <span v-else>登 录</span>
      </button>
    </form>

    <p class="mt-8 text-center text-sm text-surface-500">
      还没有账号？
      <RouterLink
        to="/register"
        class="text-primary-600 font-medium hover:text-primary-700 transition-colors"
      >
        立即注册
      </RouterLink>
    </p>
  </div>
</template>

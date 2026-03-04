<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const validationError = ref<string | null>(null)

async function handleRegister() {
  validationError.value = null

  if (form.value.password !== form.value.confirmPassword) {
    validationError.value = '两次输入的密码不一致'
    return
  }

  if (form.value.password.length < 6) {
    validationError.value = '密码长度至少为6位'
    return
  }

  try {
    await auth.register({
      username: form.value.username,
      email: form.value.email,
      password: form.value.password,
    })
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

    <h2 class="text-2xl font-bold text-surface-900 mb-2">创建账号</h2>
    <p class="text-surface-500 mb-8">注册以开始使用智能简历审阅服务</p>

    <!-- 错误提示 -->
    <div
      v-if="auth.error || validationError"
      class="mb-6 p-4 rounded-xl bg-danger-500/10 border border-danger-500/20 text-danger-600 text-sm flex items-center gap-2"
    >
      <span>⚠️</span>
      <span>{{ validationError || auth.error }}</span>
    </div>

    <form @submit.prevent="handleRegister" class="space-y-5">
      <div>
        <label for="reg-username" class="block text-sm font-medium text-surface-700 mb-2">
          用户名
        </label>
        <input
          id="reg-username"
          v-model="form.username"
          type="text"
          required
          minlength="3"
          maxlength="50"
          autocomplete="username"
          placeholder="3-50 个字符"
          class="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all duration-200"
        />
      </div>

      <div>
        <label for="reg-email" class="block text-sm font-medium text-surface-700 mb-2">
          邮箱
        </label>
        <input
          id="reg-email"
          v-model="form.email"
          type="email"
          required
          autocomplete="email"
          placeholder="example@email.com"
          class="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all duration-200"
        />
      </div>

      <div>
        <label for="reg-password" class="block text-sm font-medium text-surface-700 mb-2">
          密码
        </label>
        <input
          id="reg-password"
          v-model="form.password"
          type="password"
          required
          minlength="6"
          autocomplete="new-password"
          placeholder="至少6个字符"
          class="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all duration-200"
        />
      </div>

      <div>
        <label for="reg-confirm" class="block text-sm font-medium text-surface-700 mb-2">
          确认密码
        </label>
        <input
          id="reg-confirm"
          v-model="form.confirmPassword"
          type="password"
          required
          autocomplete="new-password"
          placeholder="再次输入密码"
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
          注册中...
        </span>
        <span v-else>注 册</span>
      </button>
    </form>

    <p class="mt-8 text-center text-sm text-surface-500">
      已有账号？
      <RouterLink
        to="/login"
        class="text-primary-600 font-medium hover:text-primary-700 transition-colors"
      >
        立即登录
      </RouterLink>
    </p>
  </div>
</template>

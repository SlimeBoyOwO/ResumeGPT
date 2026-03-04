<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const navItems = computed(() => {
  if (auth.isAdmin) {
    return [
      { label: '管理面板', path: '/admin', icon: '📊' },
      { label: '简历管理', path: '/admin/resumes', icon: '📋' },
    ]
  }
  return [
    { label: '仪表盘', path: '/dashboard', icon: '🏠' },
    { label: '我的简历', path: '/my-resumes', icon: '📄' },
  ]
})

function isActive(path: string) {
  return route.path === path
}

async function handleLogout() {
  await auth.logout()
}
</script>

<template>
  <div class="min-h-screen bg-surface-50 flex">
    <!-- 侧边栏 -->
    <aside
      class="w-64 bg-surface-900 text-white flex flex-col fixed inset-y-0 left-0 z-30 shadow-2xl"
    >
      <!-- Logo 区域 -->
      <div class="p-6 border-b border-white/10">
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-lg font-bold shadow-lg"
          >
            R
          </div>
          <div>
            <h1 class="text-lg font-bold tracking-tight">ResumeGPT</h1>
            <p class="text-xs text-surface-400">智能简历审阅</p>
          </div>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 p-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200"
          :class="
            isActive(item.path)
              ? 'bg-primary-600/20 text-primary-300 shadow-lg shadow-primary-500/10'
              : 'text-surface-300 hover:bg-white/5 hover:text-white'
          "
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span
            v-if="isActive(item.path)"
            class="ml-auto w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse"
          />
        </RouterLink>
      </nav>

      <!-- 用户信息 -->
      <div class="p-4 border-t border-white/10">
        <div class="flex items-center gap-3 mb-3">
          <div
            class="w-9 h-9 rounded-full bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center text-sm font-bold"
          >
            {{ auth.username.charAt(0).toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium truncate">{{ auth.username }}</p>
            <p class="text-xs text-surface-400">{{ auth.isAdmin ? '管理员' : '用户' }}</p>
          </div>
        </div>
        <button
          @click="handleLogout"
          class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm text-surface-300 hover:bg-danger-500/20 hover:text-danger-400 transition-all duration-200 cursor-pointer"
        >
          <span>🚪</span>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="flex-1 ml-64">
      <!-- 顶部栏 -->
      <header
        class="h-16 bg-white/80 backdrop-blur-md border-b border-surface-200 flex items-center justify-between px-8 sticky top-0 z-20"
      >
        <div>
          <h2 class="text-lg font-semibold text-surface-900">
            {{ route.meta.title || '仪表盘' }}
          </h2>
        </div>
        <div class="flex items-center gap-4">
          <span
            class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
            :class="
              auth.isAdmin
                ? 'bg-warning-400/15 text-warning-500'
                : 'bg-primary-100 text-primary-600'
            "
          >
            {{ auth.isAdmin ? '🛡️ 管理员' : '👤 用户' }}
          </span>
        </div>
      </header>

      <!-- 页面内容 -->
      <div class="p-8">
        <RouterView />
      </div>
    </main>
  </div>
</template>

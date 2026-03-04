<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'

const stats = ref({
  totalUsers: 0,
  totalResumes: 0,
  pendingResumes: 0,
  completedResumes: 0,
})

const loading = ref(true)

onMounted(async () => {
  try {
    const [usersRes, resumesRes, pendingRes, completedRes] = await Promise.all([
      api.get('/users/', { params: { page_size: 1 } }),
      api.get('/resumes/admin/all', { params: { page_size: 1 } }),
      api.get('/resumes/admin/all', { params: { status_filter: 'pending', page_size: 1 } }),
      api.get('/resumes/admin/all', { params: { status_filter: 'completed', page_size: 1 } }),
    ])
    stats.value.totalUsers = usersRes.data.total
    stats.value.totalResumes = resumesRes.data.total
    stats.value.pendingResumes = pendingRes.data.total
    stats.value.completedResumes = completedRes.data.total
  } catch {
    // 忽略
  } finally {
    loading.value = false
  }
})

const cards = [
  {
    key: 'totalUsers',
    label: '注册用户',
    icon: '👥',
    gradient: 'from-primary-500 to-primary-600',
  },
  {
    key: 'totalResumes',
    label: '简历总数',
    icon: '📄',
    gradient: 'from-accent-400 to-accent-600',
  },
  {
    key: 'pendingResumes',
    label: '待分析',
    icon: '⏳',
    gradient: 'from-warning-400 to-warning-500',
  },
  {
    key: 'completedResumes',
    label: '已完成',
    icon: '✅',
    gradient: 'from-green-400 to-green-600',
  },
]
</script>

<template>
  <div class="animate-fade-in space-y-8">
    <!-- 管理员欢迎 -->
    <div
      class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-surface-800 via-surface-900 to-surface-950 text-white p-8"
    >
      <div class="absolute top-0 right-0 w-72 h-72 bg-primary-500/10 rounded-full -translate-y-1/2 translate-x-1/4" />
      <div class="absolute bottom-0 left-0 w-48 h-48 bg-accent-500/10 rounded-full translate-y-1/2 -translate-x-1/4" />
      <div class="relative z-10">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-2xl">🛡️</span>
          <h1 class="text-2xl font-bold">管理员控制台</h1>
        </div>
        <p class="text-surface-300 text-lg">
          监控系统运行状态，管理用户简历数据。
        </p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <div
        v-for="(card, index) in cards"
        :key="card.key"
        class="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300"
        :style="{ animationDelay: `${index * 80}ms` }"
      >
        <div class="flex items-center justify-between mb-4">
          <div
            class="w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-xl shadow-lg"
            :class="card.gradient"
          >
            {{ card.icon }}
          </div>
        </div>
        <div v-if="loading" class="h-8 w-16 bg-surface-100 rounded-lg animate-pulse" />
        <p v-else class="text-3xl font-bold text-surface-900">
          {{ stats[card.key as keyof typeof stats] }}
        </p>
        <p class="text-sm text-surface-500 mt-1">{{ card.label }}</p>
      </div>
    </div>

    <!-- 快捷功能 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <RouterLink
        to="/admin/resumes"
        class="group bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 flex items-center gap-5"
      >
        <div
          class="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform"
        >
          📋
        </div>
        <div>
          <h3 class="text-lg font-semibold text-surface-900">简历管理</h3>
          <p class="text-sm text-surface-500">查看所有用户上传的简历</p>
        </div>
        <span class="ml-auto text-surface-300 group-hover:text-primary-500 transition-colors text-xl">→</span>
      </RouterLink>

      <div
        class="bg-white/60 rounded-2xl p-6 shadow-sm border-2 border-dashed border-surface-200 flex items-center gap-5"
      >
        <div class="w-14 h-14 rounded-2xl bg-surface-100 flex items-center justify-center text-2xl">
          🎯
        </div>
        <div>
          <h3 class="text-lg font-semibold text-surface-400">岗位匹配分析</h3>
          <p class="text-sm text-surface-400">即将推出…</p>
        </div>
        <span class="ml-auto px-3 py-1 rounded-full bg-surface-100 text-xs text-surface-400 font-medium">
          敬请期待
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

const auth = useAuthStore()

const stats = ref({
  totalResumes: 0,
  pendingResumes: 0,
  completedResumes: 0,
})

const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/resumes/', { params: { page_size: 1 } })
    stats.value.totalResumes = data.total

    const pending = await api.get('/resumes/', { params: { status_filter: 'pending', page_size: 1 } })
    stats.value.pendingResumes = pending.data.total

    const completed = await api.get('/resumes/', {
      params: { status_filter: 'completed', page_size: 1 },
    })
    stats.value.completedResumes = completed.data.total
  } catch {
    // 忽略错误
  } finally {
    loading.value = false
  }
})

const statCards = [
  {
    key: 'totalResumes',
    label: '我的简历',
    icon: '📄',
    gradient: 'from-primary-500 to-primary-600',
    shadow: 'shadow-primary-500/20',
  },
  {
    key: 'pendingResumes',
    label: '待分析',
    icon: '⏳',
    gradient: 'from-warning-400 to-warning-500',
    shadow: 'shadow-warning-400/20',
  },
  {
    key: 'completedResumes',
    label: '已完成',
    icon: '✅',
    gradient: 'from-accent-400 to-accent-600',
    shadow: 'shadow-accent-400/20',
  },
]
</script>

<template>
  <div class="animate-fade-in space-y-8">
    <!-- 欢迎区域 -->
    <div
      class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 text-white p-8"
    >
      <div class="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/4" />
      <div class="absolute bottom-0 left-1/3 w-48 h-48 bg-white/5 rounded-full translate-y-1/2" />
      <div class="relative z-10">
        <h1 class="text-2xl font-bold mb-2">
          👋 欢迎回来，{{ auth.username }}
        </h1>
        <p class="text-primary-200 text-lg">
          您的智能简历分析助手已就绪。上传简历即可开始智能审阅。
        </p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div
        v-for="(card, index) in statCards"
        :key="card.key"
        class="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300"
        :style="{ animationDelay: `${index * 100}ms` }"
      >
        <div class="flex items-center justify-between mb-4">
          <div
            class="w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-xl shadow-lg"
            :class="[card.gradient, card.shadow]"
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

    <!-- 快速操作 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <RouterLink
        to="/my-resumes"
        class="group bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 flex items-center gap-5"
      >
        <div
          class="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform duration-300"
        >
          📤
        </div>
        <div>
          <h3 class="text-lg font-semibold text-surface-900">上传新简历</h3>
          <p class="text-sm text-surface-500">支持 PDF、DOCX、图片格式</p>
        </div>
        <span class="ml-auto text-surface-300 group-hover:text-primary-500 transition-colors text-xl">
          →
        </span>
      </RouterLink>

      <div
        class="bg-white/60 rounded-2xl p-6 shadow-sm border-2 border-dashed border-surface-200 flex items-center gap-5"
      >
        <div
          class="w-14 h-14 rounded-2xl bg-surface-100 flex items-center justify-center text-2xl"
        >
          🔮
        </div>
        <div>
          <h3 class="text-lg font-semibold text-surface-400">AI 分析报告</h3>
          <p class="text-sm text-surface-400">即将推出…</p>
        </div>
        <span
          class="ml-auto px-3 py-1 rounded-full bg-surface-100 text-xs text-surface-400 font-medium"
        >
          敬请期待
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/utils/api'

const stats = ref({
  totalUsers: 0,
  totalResumes: 0,
  pendingResumes: 0,
  parsedResumes: 0,
})

const loading = ref(true)

onMounted(async () => {
  try {
    const [usersRes, resumesRes, pendingRes, parsedRes] = await Promise.all([
      api.get('/users/', { params: { page_size: 1 } }),
      api.get('/resumes/admin/all', { params: { page_size: 1 } }),
      api.get('/resumes/admin/all', { params: { status_filter: 'pending', page_size: 1 } }),
      api.get('/resumes/admin/all', { params: { status_filter: 'parsed', page_size: 1 } }),
    ])

    stats.value.totalUsers = usersRes.data.total
    stats.value.totalResumes = resumesRes.data.total
    stats.value.pendingResumes = pendingRes.data.total
    stats.value.parsedResumes = parsedRes.data.total
  } catch {
    // noop
  } finally {
    loading.value = false
  }
})

const cards = [
  { key: 'totalUsers', label: '注册用户', icon: '👤', gradient: 'from-primary-500 to-primary-600' },
  { key: 'totalResumes', label: '简历总数', icon: '📄', gradient: 'from-accent-400 to-accent-600' },
  { key: 'pendingResumes', label: '待解析', icon: '⏳', gradient: 'from-warning-400 to-warning-500' },
  { key: 'parsedResumes', label: '已解析', icon: '✅', gradient: 'from-green-400 to-green-600' },
]
</script>

<template>
  <div class="animate-fade-in space-y-8">
    <div class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-surface-800 via-surface-900 to-surface-950 text-white p-8">
      <div class="relative z-10">
        <h1 class="text-2xl font-bold">管理员控制台</h1>
        <p class="text-surface-300 text-lg mt-1">监控系统运行状态并管理招聘数据</p>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <div
        v-for="card in cards"
        :key="card.key"
        class="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300"
      >
        <div class="flex items-center justify-between mb-4">
          <div class="w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-xl shadow-lg" :class="card.gradient">
            {{ card.icon }}
          </div>
        </div>
        <div v-if="loading" class="h-8 w-16 bg-surface-100 rounded-lg animate-pulse" />
        <p v-else class="text-3xl font-bold text-surface-900">{{ stats[card.key as keyof typeof stats] }}</p>
        <p class="text-sm text-surface-500 mt-1">{{ card.label }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <RouterLink
        to="/admin/resumes"
        class="group bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 flex items-center gap-5"
      >
        <div class="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center text-2xl">📄</div>
        <div>
          <h3 class="text-lg font-semibold text-surface-900">简历管理</h3>
          <p class="text-sm text-surface-500">查看所有用户上传的简历</p>
        </div>
      </RouterLink>

      <RouterLink
        to="/admin/jobs"
        class="group bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 flex items-center gap-5"
      >
        <div class="w-14 h-14 rounded-2xl bg-accent-50 flex items-center justify-center text-2xl">🧩</div>
        <div>
          <h3 class="text-lg font-semibold text-surface-900">岗位管理</h3>
          <p class="text-sm text-surface-500">创建 JD 并配置专家工作流</p>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

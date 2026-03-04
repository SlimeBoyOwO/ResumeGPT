<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import api from '@/utils/api'

interface ResumeItem {
  id: number
  user_id: number
  original_filename: string
  file_size: number
  file_type: string
  status: string
  score: number | null
  best_match_position: string | null
  uploaded_at: string
  username: string | null
}

const resumes = ref<ResumeItem[]>([])
const total = ref(0)
const loading = ref(true)
const currentPage = ref(1)
const pageSize = 15
const statusFilter = ref('')
const searchUsername = ref('')

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function fetchResumes() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize,
    }
    if (statusFilter.value) params.status_filter = statusFilter.value
    if (searchUsername.value.trim()) params.username_filter = searchUsername.value.trim()

    const { data } = await api.get('/resumes/admin/all', { params })
    resumes.value = data.items
    total.value = data.total
  } catch {
    // 忽略
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchResumes()
}

watch(statusFilter, () => {
  currentPage.value = 1
  fetchResumes()
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusLabel(s: string) {
  const map: Record<string, { text: string; class: string }> = {
    pending: { text: '待分析', class: 'bg-warning-400/15 text-warning-500' },
    processing: { text: '分析中', class: 'bg-primary-100 text-primary-600' },
    completed: { text: '已完成', class: 'bg-accent-400/15 text-accent-600' },
    failed: { text: '失败', class: 'bg-danger-400/15 text-danger-600' },
  }
  return map[s] || { text: s, class: 'bg-surface-100 text-surface-500' }
}

function fileTypeIcon(t: string) {
  if (t === 'pdf') return '📕'
  if (t === 'docx' || t === 'doc') return '📘'
  return '🖼️'
}

onMounted(fetchResumes)
</script>

<template>
  <div class="animate-fade-in space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-surface-900">简历管理</h1>
      <p class="text-surface-500 mt-1">查看和管理所有用户上传的简历</p>
    </div>

    <!-- 筛选栏 -->
    <div class="bg-white rounded-2xl p-4 shadow-sm flex flex-wrap items-center gap-4">
      <!-- 搜索用户 -->
      <div class="flex-1 min-w-[200px]">
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">🔍</span>
          <input
            v-model="searchUsername"
            @keyup.enter="handleSearch"
            type="text"
            placeholder="搜索用户名..."
            class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-surface-200 bg-surface-50 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all"
          />
        </div>
      </div>

      <!-- 状态筛选 -->
      <select
        v-model="statusFilter"
        class="px-4 py-2.5 rounded-xl border border-surface-200 bg-surface-50 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/40 cursor-pointer"
      >
        <option value="">全部状态</option>
        <option value="pending">待分析</option>
        <option value="processing">分析中</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
      </select>

      <button
        @click="handleSearch"
        class="px-5 py-2.5 rounded-xl bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors cursor-pointer"
      >
        搜索
      </button>
    </div>

    <!-- 简历表格 -->
    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-surface-50">
            <tr>
              <th class="text-left px-6 py-3.5 text-xs font-semibold text-surface-500 uppercase tracking-wider">
                文件信息
              </th>
              <th class="text-left px-6 py-3.5 text-xs font-semibold text-surface-500 uppercase tracking-wider">
                上传用户
              </th>
              <th class="text-left px-6 py-3.5 text-xs font-semibold text-surface-500 uppercase tracking-wider">
                状态
              </th>
              <th class="text-left px-6 py-3.5 text-xs font-semibold text-surface-500 uppercase tracking-wider">
                评分
              </th>
              <th class="text-left px-6 py-3.5 text-xs font-semibold text-surface-500 uppercase tracking-wider">
                最佳岗位
              </th>
              <th class="text-left px-6 py-3.5 text-xs font-semibold text-surface-500 uppercase tracking-wider">
                上传时间
              </th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr>
              <td colspan="6" class="text-center py-16">
                <svg class="animate-spin h-8 w-8 text-primary-400 mx-auto" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </td>
            </tr>
          </tbody>
          <tbody v-else-if="resumes.length === 0">
            <tr>
              <td colspan="6" class="text-center py-16">
                <div class="text-4xl mb-3">📭</div>
                <p class="text-surface-400">暂无简历数据</p>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr
              v-for="resume in resumes"
              :key="resume.id"
              class="border-t border-surface-50 hover:bg-surface-50/50 transition-colors"
            >
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <span class="text-xl">{{ fileTypeIcon(resume.file_type) }}</span>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-surface-900 truncate max-w-[220px]">
                      {{ resume.original_filename }}
                    </p>
                    <p class="text-xs text-surface-400">{{ formatSize(resume.file_size) }}</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm text-surface-700">{{ resume.username || '-' }}</span>
              </td>
              <td class="px-6 py-4">
                <span
                  class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
                  :class="statusLabel(resume.status).class"
                >
                  {{ statusLabel(resume.status).text }}
                </span>
              </td>
              <td class="px-6 py-4">
                <span v-if="resume.score !== null" class="text-sm font-semibold text-accent-500">
                  {{ resume.score.toFixed(1) }}
                </span>
                <span v-else class="text-sm text-surface-300">-</span>
              </td>
              <td class="px-6 py-4">
                <span v-if="resume.best_match_position" class="text-sm text-surface-700">
                  {{ resume.best_match_position }}
                </span>
                <span v-else class="text-sm text-surface-300">-</span>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm text-surface-500">{{ formatDate(resume.uploaded_at) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="flex items-center justify-between px-6 py-4 border-t border-surface-100">
        <span class="text-sm text-surface-500">共 {{ total }} 条记录</span>
        <div class="flex items-center gap-2">
          <button
            :disabled="currentPage === 1"
            @click="currentPage--; fetchResumes()"
            class="px-3 py-1.5 rounded-lg text-sm disabled:opacity-40 hover:bg-surface-100 transition-colors cursor-pointer"
          >
            上一页
          </button>
          <span class="text-sm text-surface-500 px-2">{{ currentPage }} / {{ totalPages }}</span>
          <button
            :disabled="currentPage === totalPages"
            @click="currentPage++; fetchResumes()"
            class="px-3 py-1.5 rounded-lg text-sm disabled:opacity-40 hover:bg-surface-100 transition-colors cursor-pointer"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

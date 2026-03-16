<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

interface ResumeItem {
  id: number
  original_filename: string
  file_type: string
  status: string
  ner_extracted_data: Record<string, any> | null
  vector_id: string | null
  uploaded_at: string
}

const auth = useAuthStore()
const resumes = ref<ResumeItem[]>([])
const total = ref(0)
const loading = ref(true)
const uploading = ref(false)
const uploadError = ref<string | null>(null)
const uploadSuccess = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const drawerOpen = ref(false)
const drawerResume = ref<ResumeItem | null>(null)

const currentPage = ref(1)
const pageSize = 10

const totalPages = computed(() => Math.ceil(total.value / pageSize))

function openDrawer(resume: ResumeItem) {
  drawerResume.value = resume
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  drawerResume.value = null
}

async function fetchResumes() {
  loading.value = true
  try {
    const { data } = await api.get('/resumes/', {
      params: { page: currentPage.value, page_size: pageSize },
    })
    resumes.value = data.items
    total.value = data.total
  } catch {
    // 忽略
  } finally {
    loading.value = false
  }
}

async function handleUpload(file: File) {
  uploadError.value = null
  uploadSuccess.value = false
  uploading.value = true

  const formData = new FormData()
  formData.append('file', file)

  try {
    await api.post('/resumes/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    uploadSuccess.value = true
    currentPage.value = 1
    await fetchResumes()
    setTimeout(() => (uploadSuccess.value = false), 3000)
  } catch (err: any) {
    uploadError.value = err.response?.data?.detail || '上传失败'
  } finally {
    uploading.value = false
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    handleUpload(input.files[0])
    input.value = ''
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files?.[0]) {
    handleUpload(e.dataTransfer.files[0])
  }
}

async function handleDelete(id: number) {
  if (!confirm('确定要删除这份简历吗？')) return
  try {
    await api.delete(`/resumes/${id}`)
    await fetchResumes()
  } catch {
    // 忽略
  }
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

function formatJson(data: Record<string, any> | null): string {
  if (!data) return '暂无解析结果'
  return JSON.stringify(data, null, 2)
}

function statusLabel(s: string) {
  const map: Record<string, { text: string; class: string }> = {
    pending: { text: '待解析', class: 'bg-warning-400/15 text-warning-500' },
    parsing: { text: '解析中', class: 'bg-primary-100 text-primary-600' },
    parsed: { text: '已解析', class: 'bg-accent-400/15 text-accent-600' },
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
  <div class="animate-fade-in space-y-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-surface-900">我的简历</h1>
        <p class="text-surface-500 mt-1">管理和上传您的简历文件</p>
      </div>
    </div>

    <!-- 上传区域 -->
    <div
      class="border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 cursor-pointer"
      :class="
        dragOver
          ? 'border-primary-400 bg-primary-50'
          : 'border-surface-200 bg-white hover:border-primary-300 hover:bg-primary-50/50'
      "
      @click="fileInput?.click()"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop.prevent="onDrop"
    >
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.bmp,.webp"
        @change="onFileSelect"
      />

      <div v-if="uploading" class="flex flex-col items-center gap-3">
        <svg class="animate-spin h-10 w-10 text-primary-500" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p class="text-primary-600 font-medium">正在上传...</p>
      </div>
      <div v-else class="flex flex-col items-center gap-3">
        <div class="w-16 h-16 rounded-2xl bg-primary-100 flex items-center justify-center text-3xl">
          📤
        </div>
        <div>
          <p class="text-lg font-semibold text-surface-700">
            拖拽文件到此处，或
            <span class="text-primary-600">点击上传</span>
          </p>
          <p class="text-sm text-surface-400 mt-1">
            支持 PDF、DOCX、JPG、PNG 等格式，最大 10MB
          </p>
        </div>
      </div>
    </div>

    <!-- 上传反馈 -->
    <div
      v-if="uploadSuccess"
      class="p-4 rounded-xl bg-accent-400/10 border border-accent-400/20 text-accent-600 text-sm flex items-center gap-2"
    >
      <span>✅</span> 简历上传成功！
    </div>
    <div
      v-if="uploadError"
      class="p-4 rounded-xl bg-danger-500/10 border border-danger-500/20 text-danger-600 text-sm flex items-center gap-2"
    >
      <span>⚠️</span> {{ uploadError }}
    </div>

    <!-- 简历列表 -->
    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
        <h3 class="font-semibold text-surface-900">
          简历列表
          <span class="text-surface-400 font-normal text-sm ml-2">共 {{ total }} 份</span>
        </h3>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-flex flex-col items-center gap-3">
          <svg class="animate-spin h-8 w-8 text-primary-400" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span class="text-surface-400 text-sm">加载中...</span>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="resumes.length === 0" class="p-12 text-center">
        <div class="text-5xl mb-4">📂</div>
        <p class="text-surface-500 text-lg">还没有上传简历</p>
        <p class="text-surface-400 text-sm mt-1">点击上方区域上传您的第一份简历</p>
      </div>

      <!-- 列表 -->
      <div v-else>
        <div
          v-for="(resume, index) in resumes"
          :key="resume.id"
          class="flex items-center gap-4 px-6 py-4 border-b border-surface-50 hover:bg-surface-50/50 transition-colors"
          :style="{ animationDelay: `${index * 50}ms` }"
        >
          <div class="text-2xl">{{ fileTypeIcon(resume.file_type) }}</div>
          <div class="flex-1 min-w-0">
            <p class="font-medium text-surface-900 truncate">
              {{ resume.original_filename }}
            </p>
            <p class="text-xs text-surface-400 mt-0.5">
              {{ formatDate(resume.uploaded_at) }}
            </p>
          </div>
          <span
            class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
            :class="statusLabel(resume.status).class"
          >
            {{ statusLabel(resume.status).text }}
          </span>
          <div class="flex items-center gap-2 text-sm text-surface-400">
            <button
              @click.stop="openDrawer(resume)"
              class="px-2.5 py-1 rounded-lg bg-surface-100 hover:bg-surface-200 text-surface-600 transition-colors cursor-pointer"
              title="查看解析结果"
            >
              查看解析
            </button>
            <button
              @click.stop="handleDelete(resume.id)"
              class="p-2 rounded-lg hover:bg-danger-50 hover:text-danger-500 transition-colors cursor-pointer"
              title="删除简历"
            >
              🗑️
            </button>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 py-4">
          <button
            :disabled="currentPage === 1"
            @click="currentPage--; fetchResumes()"
            class="px-3 py-1.5 rounded-lg text-sm disabled:opacity-40 hover:bg-surface-100 transition-colors cursor-pointer"
          >
            上一页
          </button>
          <span class="text-sm text-surface-500">{{ currentPage }} / {{ totalPages }}</span>
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

    <!-- 解析结果抽屉 -->
    <div
      v-if="drawerOpen"
      class="fixed inset-0 z-50 bg-black/30"
      @click.self="closeDrawer"
    >
      <div class="absolute right-0 top-0 h-full w-full max-w-lg bg-white shadow-xl p-6 overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-surface-900">解析结果</h3>
          <button
            @click="closeDrawer"
            class="px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-surface-200 text-sm text-surface-600"
          >
            关闭
          </button>
        </div>
        <div class="text-sm text-surface-500 mb-3">
          <span class="font-medium text-surface-700">向量ID：</span>
          <span>{{ drawerResume?.vector_id || '-' }}</span>
        </div>
        <pre class="bg-surface-50 border border-surface-200 rounded-xl p-4 text-xs whitespace-pre-wrap">
{{ formatJson(drawerResume?.ner_extracted_data || null) }}
        </pre>
      </div>
    </div>
  </div>
</template>

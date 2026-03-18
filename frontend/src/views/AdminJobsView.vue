<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '@/utils/api'
import ExpertGraphEditor from '@/components/ExpertGraphEditor.vue'

interface ExpertOption {
  id: number
  name: string
  description: string | null
  system_prompt: string
}



interface JobItem {
  id: number
  title: string
  department: string | null
  description: string
  status: 'open' | 'closed'
  created_at: string
  workflow_mode: 'manual' | 'auto_pending'
  workflow_graph: { nodes: any[]; edges: any[] } | null
}

const experts = ref<ExpertOption[]>([])
const jobs = ref<JobItem[]>([])
const total = ref(0)
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const form = reactive({
  title: '',
  department: '',
  description: '',
  status: 'open' as 'open' | 'closed',
  workflowMode: 'manual' as 'manual' | 'auto',
  workflow_graph: { nodes: [], edges: [] } as { nodes: any[]; edges: any[] },
})

function resetForm() {
  form.title = ''
  form.department = ''
  form.description = ''
  form.status = 'open'
  form.workflowMode = 'manual'
  form.workflow_graph = { nodes: [], edges: [] }
}

function validateForm(): string | null {
  if (!form.title.trim()) return '请输入岗位名称。'
  if (!form.description.trim()) return '请输入岗位描述。'

  if (form.workflowMode === 'manual') {
    if (!form.workflow_graph.nodes || form.workflow_graph.nodes.length === 0) {
      return '手动模式下必须在画布中配置至少一个专家节点。'
    }
  }

  return null
}

async function fetchExperts() {
  const { data } = await api.get('/experts/')
  experts.value = data
}

async function fetchJobs() {
  loading.value = true
  try {
    const { data } = await api.get('/job-descriptions/', { params: { page: 1, page_size: 50 } })
    jobs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function submitJob() {
  error.value = null
  success.value = null

  const validationError = validateForm()
  if (validationError) {
    error.value = validationError
    return
  }

  submitting.value = true
  try {
    const payload = {
      title: form.title.trim(),
      department: form.department.trim() || null,
      description: form.description.trim(),
      status: form.status,
      auto_select_experts: form.workflowMode === 'auto',
      workflow_graph: form.workflowMode === 'manual' ? form.workflow_graph : null,
    }

    await api.post('/job-descriptions/', payload)
    success.value = 'JD 已创建。'
    resetForm()
    await fetchJobs()
  } catch (err: any) {
    error.value = err.response?.data?.detail || '创建 JD 失败，请重试。'
  } finally {
    submitting.value = false
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(async () => {
  try {
    await Promise.all([fetchExperts(), fetchJobs()])
  } catch (err: any) {
    error.value = err.response?.data?.detail || '初始化数据失败。'
  }
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-surface-900">岗位管理</h1>
      <p class="text-surface-500 mt-1">创建 JD 并配置专家工作流</p>
    </div>

    <div class="bg-white rounded-2xl p-6 shadow-sm space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-surface-600 mb-1">岗位名称</label>
          <input v-model="form.title" class="w-full px-3 py-2 rounded-lg border border-surface-200" type="text" />
        </div>
        <div>
          <label class="block text-sm text-surface-600 mb-1">部门（可选）</label>
          <input v-model="form.department" class="w-full px-3 py-2 rounded-lg border border-surface-200" type="text" />
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-surface-600 mb-1">岗位状态</label>
          <select v-model="form.status" class="w-full px-3 py-2 rounded-lg border border-surface-200 bg-white">
            <option value="open">open</option>
            <option value="closed">closed</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-surface-600 mb-1">专家模式</label>
          <select v-model="form.workflowMode" class="w-full px-3 py-2 rounded-lg border border-surface-200 bg-white">
            <option value="manual">手动选择专家</option>
            <option value="auto">自动选择（预留）</option>
          </select>
        </div>
      </div>

      <div>
        <label class="block text-sm text-surface-600 mb-1">岗位描述</label>
        <textarea v-model="form.description" rows="5" class="w-full px-3 py-2 rounded-lg border border-surface-200"></textarea>
      </div>

      <div class="mt-4">
        <h3 class="text-sm font-semibold text-surface-800 mb-3">专家节点连线配置（手动模式）</h3>
        <ExpertGraphEditor
          v-model="form.workflow_graph"
          :experts="experts"
          :disabled="form.workflowMode === 'auto'"
        />
      </div>

      <div v-if="error" class="p-3 rounded-lg bg-danger-50 text-danger-700 text-sm">
        {{ error }}
      </div>
      <div v-if="success" class="p-3 rounded-lg bg-accent-50 text-accent-700 text-sm">
        {{ success }}
      </div>

      <div class="flex justify-end">
        <button
          @click="submitJob"
          :disabled="submitting"
          class="px-5 py-2.5 rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40"
        >
          {{ submitting ? '提交中...' : '创建 JD' }}
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl p-6 shadow-sm">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-surface-900">JD 列表</h2>
        <span class="text-sm text-surface-500">共 {{ total }} 条</span>
      </div>

      <div v-if="loading" class="py-10 text-center text-surface-400">加载中...</div>
      <div v-else-if="jobs.length === 0" class="py-10 text-center text-surface-400">暂无 JD</div>
      <div v-else class="space-y-3">
        <div v-for="job in jobs" :key="job.id" class="border border-surface-100 rounded-xl p-4">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="text-base font-semibold text-surface-900">{{ job.title }}</h3>
              <p class="text-xs text-surface-500 mt-1">
                {{ job.department || '未填写部门' }} · {{ formatDate(job.created_at) }}
              </p>
            </div>
            <div class="text-right text-xs text-surface-500 space-y-1">
              <p>状态：{{ job.status }}</p>
              <p>模式：{{ job.workflow_mode }}</p>
              <p>节点总数：{{ job.workflow_graph?.nodes?.length || 0 }}</p>
            </div>
          </div>
          <p class="text-sm text-surface-700 mt-3 whitespace-pre-wrap">{{ job.description }}</p>

          <div v-if="job.workflow_graph?.nodes?.length" class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="node in job.workflow_graph.nodes"
              :key="node.id"
              class="px-2.5 py-1 rounded-full text-xs bg-surface-100 text-surface-700"
            >
              {{ node.label || `节点#${node.data?.expert_id}` }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

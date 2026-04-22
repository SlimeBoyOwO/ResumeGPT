<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import ExpertGraphEditor from '@/components/ExpertGraphEditor.vue'

interface ExpertOption {
  id: number
  name: string
  description: string | null
  system_prompt: string
}

const router = useRouter()
const experts = ref<ExpertOption[]>([])
const submitting = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const form = reactive({
  title: '',
  department: '',
  description: '',
  status: 'open' as 'open' | 'closed',
  workflowMode: 'manual' as 'manual' | 'auto',
  expectedHires: 10,
  workflow_graph: { nodes: [], edges: [] } as { nodes: any[]; edges: any[] },
})

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
      expected_hires: form.expectedHires,
      auto_select_experts: form.workflowMode === 'auto',
      workflow_graph: form.workflowMode === 'manual' ? form.workflow_graph : null,
    }

    await api.post('/job-descriptions/', payload)
    success.value = 'JD 已创建成功，正在跳转到列表...'
    setTimeout(() => {
      router.push('/admin/jobs/list')
    }, 1500)
  } catch (err: any) {
    error.value = err.response?.data?.detail || '创建 JD 失败，请重试。'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    await fetchExperts()
  } catch (err: any) {
    error.value = err.response?.data?.detail || '初始化数据失败。'
  }
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-surface-900">创建 JD</h1>
      <p class="text-surface-500 mt-1">创建新的职位描述并配置专家工作流</p>
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
      
      <div class="grid grid-cols-1 gap-4">
        <div>
          <label class="block text-sm text-surface-600 mb-1">查阅简历数量 (筛出TopN名)</label>
          <input v-model.number="form.expectedHires" type="number" min="1" max="100" class="w-full px-3 py-2 rounded-lg border border-surface-200" />
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

      <div class="flex justify-end gap-3">
        <button
          @click="router.push('/admin/jobs/list')"
          class="px-5 py-2.5 rounded-xl border border-surface-200 text-surface-700 hover:bg-surface-50 transition"
        >
          取消
        </button>
        <button
          @click="submitJob"
          :disabled="submitting"
          class="px-5 py-2.5 rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40"
        >
          {{ submitting ? '提交中...' : '创建 JD' }}
        </button>
      </div>
    </div>
  </div>
</template>

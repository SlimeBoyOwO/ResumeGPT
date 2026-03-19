<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '@/utils/api'
import ExpertGraphEditor from '@/components/ExpertGraphEditor.vue'

import * as echarts from 'echarts'

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

const matchesDrawerOpen = ref(false)
const currentJdTitle = ref('')
const matchesList = ref<any[]>([])
const loadingMatches = ref(false)

const evaluationsDrawerOpen = ref(false)
const selectedMatchForEvals = ref<any>(null)
const expertEvaluations = ref<any[]>([])
const loadingEvals = ref(false)
let currentChartInstance: echarts.EChartsType | null = null

const form = reactive({
  title: '',
  department: '',
  description: '',
  status: 'open' as 'open' | 'closed',
  workflowMode: 'manual' as 'manual' | 'auto',
  expectedHires: 10,
  workflow_graph: { nodes: [], edges: [] } as { nodes: any[]; edges: any[] },
})

function resetForm() {
  form.title = ''
  form.department = ''
  form.description = ''
  form.status = 'open'
  form.workflowMode = 'manual'
  form.expectedHires = 10
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
      expected_hires: form.expectedHires,
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

async function viewMatches(job: JobItem) {
  currentJdTitle.value = job.title
  matchesDrawerOpen.value = true
  loadingMatches.value = true
  try {
    const { data } = await api.get(`/job-descriptions/${job.id}/matches`)
    matchesList.value = data.items || []
  } catch (err) {
    console.error(err)
  } finally {
    loadingMatches.value = false
  }
}

async function viewEvaluations(match: any) {
  selectedMatchForEvals.value = match
  evaluationsDrawerOpen.value = true
  loadingEvals.value = true
  expertEvaluations.value = []
  
  try {
    const { data } = await api.get(`/job-descriptions/matches/${match.match_id}/evaluations`)
    expertEvaluations.value = data.items || []
  } catch (err) {
    console.error(err)
  } finally {
    loadingEvals.value = false
    // Render radar chart if available
    setTimeout(() => {
      renderRadarChart(match.ability_summary)
    }, 100)
  }
}

function renderRadarChart(summary: Record<string, number> | null) {
  const container = document.getElementById('radar-chart-container')
  if (!container) return
  if (currentChartInstance) {
    currentChartInstance.dispose()
  }
  
  if (!summary) {
    container.innerHTML = '<div class="flex h-full items-center justify-center text-surface-400">能力图暂未生成</div>'
    return
  }

  const chart = echarts.init(container)
  currentChartInstance = chart
  
  const indicator = [
    { name: '专业技能', max: 100 },
    { name: '业务经验', max: 100 },
    { name: '学习与潜力', max: 100 },
    { name: '沟通与协作', max: 100 },
    { name: '抗压与稳定性', max: 100 },
    { name: '岗位匹配度', max: 100 }
  ]
  
  const values = indicator.map(ind => summary[ind.name] || 0)
  
  const option = {
    radar: {
      indicator: indicator,
      radius: '65%',
      axisName: {
        color: '#64748b',
        fontSize: 12
      },
      splitArea: {
        areaStyle: {
          color: ['#f8fafc', '#f1f5f9', '#e2e8f0', '#cbd5e1']
        }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '能力评估',
        itemStyle: { color: '#0ea5e9' },
        areaStyle: { color: 'rgba(14, 165, 233, 0.4)' },
        lineStyle: { width: 2 }
      }]
    }]
  }
  chart.setOption(option)
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
              <button
                @click="viewMatches(job)"
                class="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-50 text-primary-700 hover:bg-primary-100 transition font-medium"
              >
                📊 查看初筛匹配
              </button>
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

    <!-- Top Matches 抽屉 -->
    <div
      v-if="matchesDrawerOpen"
      class="fixed inset-0 z-50 bg-black/30"
      @click.self="matchesDrawerOpen = false"
    >
      <div class="absolute right-0 top-0 h-full w-full max-w-2xl bg-surface-50 shadow-xl p-6 overflow-y-auto flex flex-col">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-bold text-surface-900 flex items-center gap-2">
            <span>📊</span> 初筛匹配结果 - {{ currentJdTitle }}
          </h3>
          <button
            @click="matchesDrawerOpen = false"
            class="px-3 py-1.5 rounded-lg bg-surface-200 hover:bg-surface-300 text-sm text-surface-700 transition"
          >
            关闭
          </button>
        </div>

        <div v-if="loadingMatches" class="py-12 flex flex-col items-center justify-center">
          <svg class="animate-spin h-8 w-8 text-primary-500 mb-4" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p class="text-surface-500 animate-pulse">正在向量库中检索匹配的简历...</p>
        </div>
        
        <div v-else-if="matchesList.length === 0" class="py-12 flex flex-col justify-center items-center text-center opacity-70">
          <div class="text-5xl mb-4">📭</div>
          <p class="text-surface-700 font-medium">暂无匹配的候选人</p>
          <p class="text-sm text-surface-400 mt-1">目前向量库中没有与之匹配度较高的简历数据</p>
        </div>

        <div v-else class="space-y-4 flex-1">
          <div v-for="match in matchesList" :key="match.match_id" class="p-4 bg-white border border-surface-200 rounded-xl shadow-sm hover:border-primary-300 transition-colors">
            <div class="flex justify-between items-start mb-2">
              <div>
                <h4 class="font-bold text-surface-900 text-base">{{ match.resume_name }}</h4>
                <p class="text-xs text-surface-500 mt-1">文件: {{ match.resume_filename }}</p>
              </div>
              <div class="text-right">
                <span class="text-2xl font-black text-primary-600 bg-primary-50 px-2 py-0.5 rounded-lg border border-primary-200">{{ match.final_score ?? '-' }}</span>
                <p class="text-[10px] text-surface-400 mt-1">综合得分</p>
              </div>
            </div>
            
            <div class="space-y-2 mt-4">
              <div>
                <div class="flex justify-between text-xs mb-1">
                  <span class="text-surface-600">语义相似度 (余弦向量)</span>
                  <span class="font-medium text-surface-800">{{ match.vector_similarity || 0 }}分</span>
                </div>
                <div class="w-full bg-surface-100 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-accent-400 h-1.5" :style="`width: ${match.vector_similarity || 0}%`"></div>
                </div>
              </div>
              <div class="text-[11px] text-surface-400 mt-3 flex items-center justify-between border-t border-surface-100 pt-3">
                <span class="px-2 py-1 bg-surface-100 rounded-md font-medium" :class="{'text-accent-600 bg-accent-50': match.workflow_status === 'completed'}">当前进度：{{ match.workflow_status }}</span>
                <button
                  v-if="match.workflow_status === 'completed' || match.workflow_status === 'agent_evaluating'"
                  @click="viewEvaluations(match)"
                  class="px-3 py-1.5 bg-primary-50 text-primary-700 hover:bg-primary-100 rounded-lg transition-colors font-medium cursor-pointer"
                >
                  查看详评分析
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Evals Drawer -->
    <div
      v-if="evaluationsDrawerOpen"
      class="fixed inset-0 z-[60] bg-black/40 flex"
      @click.self="evaluationsDrawerOpen = false"
    >
      <div class="ml-auto w-full max-w-xl h-full bg-surface-50 shadow-2xl flex flex-col p-6 overflow-hidden animate-slide-in-right">
        <div class="flex items-center justify-between mb-4 border-b border-surface-200 pb-4 shrink-0">
          <div>
            <h3 class="text-xl font-bold text-surface-900 flex items-center gap-2">
              <span>📑</span> 综合评价报告
            </h3>
            <p class="text-sm text-surface-500 mt-1">{{ selectedMatchForEvals?.resume_name }} 的多维度审核结果</p>
          </div>
          <button
            @click="evaluationsDrawerOpen = false"
            class="p-2 rounded-xl bg-surface-200 hover:bg-surface-300 text-surface-700 transition"
          >
            ❌ 关闭
          </button>
        </div>

        <div class="flex-1 overflow-y-auto pr-2 space-y-6">
          <div class="bg-white rounded-2xl p-4 shadow-sm border border-surface-100">
            <h4 class="font-bold text-surface-800 mb-3 text-sm flex items-center gap-1.5">
              <span class="w-1.5 h-4 bg-primary-500 rounded-full inline-block"></span>
              六维度能力雷达图
            </h4>
            <div id="radar-chart-container" class="w-full h-64"></div>
          </div>
          
          <div class="space-y-4">
            <h4 class="font-bold text-surface-800 text-sm flex items-center gap-1.5">
              <span class="w-1.5 h-4 bg-accent-500 rounded-full inline-block"></span>
              专家网络独立评审记录
            </h4>
            <div v-if="loadingEvals" class="py-10 text-center text-surface-400">加载评审数据中...</div>
            <div v-else-if="expertEvaluations.length === 0" class="text-xs text-center text-surface-400 py-6">暂无评价记录</div>
            <div v-else class="space-y-3">
              <div v-for="ev in expertEvaluations" :key="ev.id" class="p-4 bg-white border-l-4 border-l-blue-400 rounded-lg shadow-sm">
                <div class="flex justify-between items-center mb-2">
                  <span class="font-bold text-surface-800 text-[15px]">{{ ev.expert_name }}</span>
                  <span class="text-lg font-black text-blue-600">{{ ev.score }}分</span>
                </div>
                <div class="text-xs text-surface-500 bg-surface-50 p-2 rounded whitespace-pre-wrap leading-relaxed">
                  {{ ev.analysis_content }}
                </div>
                <div class="text-[10px] text-surface-400 mt-2 text-right">评估于 {{ formatDate(ev.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

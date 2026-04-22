<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import ExpertGraphEditor from '@/components/ExpertGraphEditor.vue'

import * as echarts from 'echarts'

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

const router = useRouter()
const jobs = ref<JobItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const matchesDrawerOpen = ref(false)
const currentJdTitle = ref('')
const matchesList = ref<any[]>([])
const loadingMatches = ref(false)

const evaluationsDrawerOpen = ref(false)
const selectedMatchForEvals = ref<any>(null)
const expertEvaluations = ref<any[]>([])
const loadingEvals = ref(false)
let currentChartInstance: echarts.EChartsType | null = null

const graphDrawerOpen = ref(false)
const currentGraphData = ref<{ nodes: any[]; edges: any[] } | null>(null)

async function fetchJobs() {
  loading.value = true
  try {
    const { data } = await api.get('/job-descriptions/', { params: { page: 1, page_size: 50 } })
    jobs.value = data.items
    total.value = data.total
  } catch (err: any) {
    error.value = err.response?.data?.detail || '获取 JD 列表失败。'
  } finally {
    loading.value = false
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

function viewWorkflowGraph(job: JobItem) {
  currentJdTitle.value = job.title
  currentGraphData.value = job.workflow_graph || { nodes: [], edges: [] }
  graphDrawerOpen.value = true
}

async function deleteJob(id: number) {
  if (!confirm('确定要删除这个 JD 吗？相关的匹配记录也将被同时删除。')) return
  try {
    await api.delete(`/job-descriptions/${id}`)
    await fetchJobs()
  } catch (err: any) {
    alert(err.response?.data?.detail || '删除失败，请重试')
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

onMounted(() => {
  fetchJobs()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-surface-900">JD 列表</h1>
        <p class="text-surface-500 mt-1">查看和管理已发布的职位描述</p>
      </div>
      <button
        @click="router.push('/admin/jobs/create')"
        class="px-4 py-2 rounded-xl bg-primary-600 text-white font-medium hover:bg-primary-700 transition"
      >
        ➕ 创建 JD
      </button>
    </div>

    <div class="bg-white rounded-2xl p-6 shadow-sm">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-surface-900">所有岗位</h2>
        <span class="text-sm text-surface-500">共 {{ total }} 条</span>
      </div>

      <div v-if="error" class="p-3 mb-4 rounded-lg bg-danger-50 text-danger-700 text-sm">
        {{ error }}
      </div>

      <div v-if="loading" class="py-10 text-center text-surface-400">加载中...</div>
      <div v-else-if="jobs.length === 0" class="py-10 text-center text-surface-400">暂无 JD</div>
      <div v-else class="space-y-3">
        <div v-for="job in jobs" :key="job.id" class="border border-surface-100 rounded-xl p-4 hover:shadow-md transition">
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
                class="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-50 text-primary-700 hover:bg-primary-100 transition font-medium cursor-pointer"
              >
                📊 查看初筛匹配
              </button>
              <button
                @click="viewWorkflowGraph(job)"
                class="mt-2 ml-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-50 text-surface-700 hover:bg-surface-100 transition font-medium cursor-pointer"
              >
                🔀 查看节点流
              </button>
              <button
                @click="deleteJob(job.id)"
                class="mt-2 ml-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger-50 text-danger-700 hover:bg-danger-100 transition font-medium cursor-pointer"
              >
                🗑️ 删除
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
            class="px-3 py-1.5 rounded-lg bg-surface-200 hover:bg-surface-300 text-sm text-surface-700 transition cursor-pointer"
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

    <!-- Evals Modal -->
    <div
      v-if="evaluationsDrawerOpen"
      class="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4"
      @click.self="evaluationsDrawerOpen = false"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div class="p-5 border-b border-surface-200 flex justify-between items-center bg-surface-50">
          <div>
            <h3 class="text-xl font-bold text-surface-900 flex items-center gap-2">
              <span>📑</span> 综合评价报告
            </h3>
            <p class="text-sm text-surface-500 mt-1">{{ selectedMatchForEvals?.resume_name }} 的多维度审核结果</p>
          </div>
          <button
            @click="evaluationsDrawerOpen = false"
            class="p-2 rounded-xl bg-surface-200 hover:bg-surface-300 text-surface-700 transition cursor-pointer"
          >
            ❌ 关闭
          </button>
        </div>

        <div class="overflow-y-auto p-6 space-y-6" style="max-height: calc(90vh - 140px);">
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
            <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div v-for="ev in expertEvaluations" :key="ev.id" class="p-5 bg-white rounded-xl shadow-sm border border-surface-200 hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-3">
                  <div class="flex items-center gap-2">
                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm">
                      {{ ev.expert_name.charAt(0) }}
                    </div>
                    <div>
                      <span class="font-bold text-surface-800">{{ ev.expert_name }}</span>
                      <div class="text-xs text-surface-400">专家评审</div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-xl font-bold text-blue-600">{{ ev.score }}分</div>
                  </div>
                </div>
                <div class="text-sm text-surface-600 bg-surface-50 p-3 rounded-lg whitespace-pre-wrap leading-relaxed">
                  {{ ev.analysis_content }}
                </div>
                <div class="text-xs text-surface-400 mt-3 text-right">评估于 {{ formatDate(ev.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Graph Drawer / Modal -->
    <div
      v-if="graphDrawerOpen"
      class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      @click.self="graphDrawerOpen = false"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div class="p-5 border-b border-surface-200 flex justify-between items-center bg-surface-50">
          <h3 class="text-xl font-bold text-surface-900 flex items-center gap-2">
            <span>🔀</span> 节点流视图 - {{ currentJdTitle }}
          </h3>
          <button
            @click="graphDrawerOpen = false"
            class="p-2 rounded-xl bg-surface-200 hover:bg-surface-300 text-surface-700 transition cursor-pointer"
          >
            ❌ 关闭
          </button>
        </div>
        <div class="p-6 bg-surface-50">
          <ExpertGraphEditor
            v-model="currentGraphData"
            disabled
            readonly
          />
        </div>
      </div>
    </div>
  </div>
</template>

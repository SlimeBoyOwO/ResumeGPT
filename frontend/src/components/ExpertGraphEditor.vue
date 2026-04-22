<script setup lang="ts">
import { ref, watch } from 'vue'
import { VueFlow, useVueFlow, Handle, Position, MarkerType, type NodeMouseEvent } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

interface ExpertOption {
  id: number
  name: string
  description: string | null
  system_prompt: string
}

const props = withDefaults(defineProps<{
  experts?: ExpertOption[]
  modelValue: { nodes: any[]; edges: any[] } | null
  disabled?: boolean
  readonly?: boolean
}>(), {
  experts: () => []
})

const emit = defineEmits(['update:modelValue'])

const nodes = ref<any[]>([])
const edges = ref<any[]>([])

const selectedNodeForDetails = ref<any>(null)

// Define default options config for edges (arrows)
const defaultEdgeOptions = {
  markerEnd: MarkerType.ArrowClosed,
  style: { strokeWidth: 2 }
}

// Initialize from props
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      nodes.value = (newVal.nodes || []).map((n: any, i: number) => ({
        ...n,
        type: n.type || 'custom',
        position: n.position || { x: (i % 3) * 300 + 50, y: Math.floor(i / 3) * 150 + 50 },
      }))
      edges.value = newVal.edges || []
    } else {
      nodes.value = []
      edges.value = []
    }
  },
  { immediate: true }
)

const { onConnect, addEdges, project } = useVueFlow()

onConnect((params) => {
  if (props.disabled) return
  addEdges([params])
  emitUpdate()
})

function onDragStart(event: DragEvent, expert: ExpertOption) {
  if (props.disabled) return
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vueflow', JSON.stringify(expert))
    event.dataTransfer.effectAllowed = 'move'
  }
}

function onDrop(event: DragEvent) {
  if (props.disabled) return
  const data = event.dataTransfer?.getData('application/vueflow')
  if (!data) return

  const expert = JSON.parse(data)
  
  // Try to use a standard project coordinates, roughly translating client offset
  const position = project({ 
    x: event.clientX - (event.target as HTMLElement).getBoundingClientRect().left, 
    y: event.clientY - (event.target as HTMLElement).getBoundingClientRect().top 
  }) || { x: event.offsetX, y: event.offsetY }

  const newNode = {
    id: `node-${Date.now()}`,
    type: 'custom',
    position: { x: position.x, y: position.y },
    label: expert.name,
    data: { 
      expert_id: expert.id, 
      weight: 1.0,
      description: expert.description,
      system_prompt: expert.system_prompt
    },
  }

  nodes.value.push(newNode)
  emitUpdate()
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

// Emitting graph updates whenever nodes or edges mutate
function emitUpdate() {
  emit('update:modelValue', { nodes: nodes.value, edges: edges.value })
}

function removeFocusElements(event: KeyboardEvent) {
  if (props.disabled) return
  if (event.key === 'Backspace' || event.key === 'Delete') {
    setTimeout(() => {
        emitUpdate()
    }, 50)
  }
}

function onNodeDoubleClick({ node }: NodeMouseEvent) {
  selectedNodeForDetails.value = node
}

watch(nodes, emitUpdate, { deep: true })
watch(edges, emitUpdate, { deep: true })

</script>

<template>
  <div class="flex h-[500px] border border-surface-200 rounded-xl overflow-hidden bg-white" @keydown="removeFocusElements">
    <!-- Sidebar -->
    <div v-if="!readonly" class="w-64 bg-surface-50 border-r border-surface-200 p-4 flex flex-col gap-3 overflow-y-auto">
      <h3 class="text-sm font-semibold text-surface-700">专家库节点 (拖拽添加)</h3>
      <div
        v-for="expert in experts"
        :key="expert.id"
        class="p-3 bg-white border border-surface-200 rounded-lg shadow-sm hover:border-primary-400 transition-colors text-sm"
        :class="disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-grab active:cursor-grabbing'"
        :draggable="!disabled"
        @dragstart="onDragStart($event, expert)"
      >
        <div class="font-medium text-surface-900">{{ expert.name }}</div>
        <div class="text-xs text-surface-500 mt-1" v-if="expert.description">{{ expert.description }}</div>
      </div>
      <div v-if="experts.length === 0" class="text-xs text-surface-400 py-4 text-center">
        暂无可用专家
      </div>
    </div>

    <!-- Canvas -->
    <div class="flex-1 relative" @drop="onDrop" @dragover="onDragOver">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :class="{ 'opacity-80': disabled && !readonly }"
        :nodes-draggable="!(disabled || readonly)"
        :nodes-connectable="!(disabled || readonly)"
        :elements-selectable="true"
        :default-edge-options="defaultEdgeOptions"
        @nodeDoubleClick="onNodeDoubleClick"
        fit-view-on-init
      >
        <Background pattern-color="#aaa" :gap="16" />

        <template #node-custom="nodeProps">
          <div class="bg-white border-2 border-primary-500 rounded-lg p-3 min-w-[160px] shadow-sm relative group cursor-pointer hover:shadow-md transition-shadow">
            <Handle type="target" :position="Position.Left" class="!w-3 !h-3 !bg-primary-500 -ml-1.5 border-2 border-white" />
            
            <div class="font-bold text-sm text-surface-900 mb-2 truncate" :title="nodeProps.label as string">
              {{ nodeProps.label }}
            </div>
            
            <div class="text-xs text-surface-600 flex items-center justify-between border-t border-surface-100 pt-2 mt-2">
              <span>节点权重</span>
              <input 
                v-if="!readonly"
                type="number" 
                step="0.1" 
                min="0"
                v-model.number="nodeProps.data.weight" 
                @input="emitUpdate"
                @mousedown.stop 
                class="w-16 border border-surface-200 rounded px-1.5 py-0.5 text-right nodrag focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
              />
              <span v-else class="text-surface-900 font-medium">{{ nodeProps.data.weight }}</span>
            </div>

            <Handle type="source" :position="Position.Right" class="!w-3 !h-3 !bg-primary-500 -mr-1.5 border-2 border-white" />

            <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-surface-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none transition-opacity">
              双击查看详细配置
            </div>
          </div>
        </template>
      </VueFlow>
    </div>

    <!-- Node Details Drawer / Modal -->
    <div v-if="selectedNodeForDetails" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 transition-opacity" @click.self="selectedNodeForDetails = null">
      <div class="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div class="p-5 border-b border-surface-200 flex justify-between items-center bg-surface-50">
          <h3 class="font-bold text-lg text-surface-900 flex items-center gap-2">
            <span class="w-2 h-6 bg-primary-500 rounded-full inline-block"></span>
            {{ selectedNodeForDetails.label }}
          </h3>
          <button @click="selectedNodeForDetails = null" class="text-surface-400 hover:text-surface-600 hover:bg-surface-200 p-1.5 rounded-lg transition-colors">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
        <div class="p-6 overflow-y-auto space-y-6 text-sm flex-1">
          <div>
            <div class="font-semibold text-surface-800 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              功能描述
            </div>
            <div class="text-surface-600 leading-relaxed bg-surface-50 p-3 rounded-xl border border-surface-100">
              {{ selectedNodeForDetails.data?.description || '暂无描述' }}
            </div>
          </div>
          <div>
            <div class="font-semibold text-surface-800 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
              Prompt 指令系统
            </div>
            <pre class="bg-gray-900 text-gray-100 p-4 rounded-xl text-[13px] overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed shadow-sm">{{ selectedNodeForDetails.data?.system_prompt || '暂无 Prompt 设定' }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

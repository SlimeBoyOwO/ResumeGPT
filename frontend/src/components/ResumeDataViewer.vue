<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: Record<string, any> | null
}>()

const basicInfo = computed(() => {
  if (!props.data) return {}
  const { 教育经历, 工作经历, 项目经历, 技能, ...rest } = props.data
  return rest
})

const education = computed(() => props.data?.['教育经历'] || [])
const workExperience = computed(() => props.data?.['工作经历'] || [])
const projects = computed(() => props.data?.['项目经历'] || [])
const skills = computed(() => props.data?.['技能'] || [])

function isObject(val: any) {
  return val !== null && typeof val === 'object' && !Array.isArray(val)
}
</script>

<template>
  <div class="resume-data-viewer space-y-6 text-surface-800 p-2">
    <!-- 未解析出数据 -->
    <div v-if="!data" class="flex flex-col items-center justify-center py-12 text-surface-400">
      <div class="text-4xl mb-3">📄</div>
      <p>暂无解析结果</p>
    </div>

    <div v-else class="space-y-8">
      <!-- 基本信息 -->
      <section v-if="Object.keys(basicInfo).length > 0" class="bg-white rounded-xl p-5 border border-surface-100 shadow-sm">
        <h3 class="text-base font-bold text-primary-700 flex items-center gap-2 mb-4 border-b border-surface-50 pb-2">
          <span>👤</span> 基本信息
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-for="(value, key) in basicInfo" :key="key" class="flex flex-col">
            <span class="text-xs text-surface-500 mb-1">{{ key }}</span>
            <span class="text-sm font-medium text-surface-900" v-if="!isObject(value)">{{ value || '-' }}</span>
            <pre v-else class="text-sm text-surface-900 whitespace-pre-wrap">{{ JSON.stringify(value, null, 2) }}</pre>
          </div>
        </div>
      </section>

      <!-- 教育经历 -->
      <section v-if="education.length > 0" class="bg-white rounded-xl p-5 border border-surface-100 shadow-sm">
        <h3 class="text-base font-bold text-accent-600 flex items-center gap-2 mb-4 border-b border-surface-50 pb-2">
          <span>🎓</span> 教育经历
        </h3>
        <div class="space-y-4">
          <div v-for="(item, index) in education" :key="index" class="relative pl-4 border-l-2 border-accent-200">
            <div class="absolute w-2 h-2 bg-accent-400 rounded-full -left-[5px] top-1.5"></div>
            <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
              <h4 class="font-bold text-surface-900">{{ item['学校名称'] || item['学校'] || '未知学校' }}</h4>
              <span class="text-xs text-surface-500 bg-surface-100 px-2 py-0.5 rounded">{{ item['时间'] || item['在校时间'] || '-' }}</span>
            </div>
            <p class="text-sm text-surface-700 font-medium">{{ item['专业'] || item['专业名称'] || '' }} <span v-if="item['学历'] || item['最高学历'] || item['学位']" class="ml-2 text-surface-500 border border-surface-200 px-1.5 py-0.5 rounded text-xs">{{ item['学历'] || item['最高学历'] || item['学位'] }}</span></p>
            <div class="mt-2 text-xs text-surface-600 space-y-1">
              <div v-for="(v, k) in item" :key="k">
                <span v-if="!['学校名称', '学校', '时间', '在校时间', '专业', '专业名称', '学历', '最高学历', '学位'].includes(String(k))">
                  <span class="text-surface-400">{{ k }}:</span> {{ v }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 工作经历 -->
      <section v-if="workExperience.length > 0" class="bg-white rounded-xl p-5 border border-surface-100 shadow-sm">
        <h3 class="text-base font-bold text-blue-600 flex items-center gap-2 mb-4 border-b border-surface-50 pb-2">
          <span>💼</span> 工作经历
        </h3>
        <div class="space-y-5">
          <div v-for="(item, index) in workExperience" :key="index" class="relative pl-4 border-l-2 border-blue-200">
            <div class="absolute w-2 h-2 bg-blue-400 rounded-full -left-[5px] top-1.5"></div>
            <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
              <h4 class="font-bold text-surface-900">{{ item['公司名称'] || item['公司'] || '未知公司' }}</h4>
              <span class="text-xs text-surface-500 bg-surface-100 px-2 py-0.5 rounded">{{ item['时间'] || item['工作时间'] || '-' }}</span>
            </div>
            <p class="text-sm font-medium text-surface-700 mb-2">{{ item['职位'] || item['职务'] || '未知职位' }}</p>
            <p v-if="item['工作内容'] || item['描述']" class="text-sm text-surface-600 whitespace-pre-wrap leading-relaxed bg-surface-50 p-3 rounded-lg">{{ item['工作内容'] || item['描述'] }}</p>
            
            <div class="mt-2 text-xs text-surface-600 space-y-1">
              <div v-for="(v, k) in item" :key="k">
                <span v-if="!['公司名称', '公司', '时间', '工作时间', '职位', '职务', '工作内容', '描述'].includes(String(k))">
                  <span class="text-surface-400">{{ k }}:</span> {{ v }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 项目经历 -->
      <section v-if="projects.length > 0" class="bg-white rounded-xl p-5 border border-surface-100 shadow-sm">
        <h3 class="text-base font-bold text-emerald-600 flex items-center gap-2 mb-4 border-b border-surface-50 pb-2">
          <span>🚀</span> 项目经历
        </h3>
        <div class="space-y-5">
          <div v-for="(item, index) in projects" :key="index" class="relative pl-4 border-l-2 border-emerald-200">
            <div class="absolute w-2 h-2 bg-emerald-400 rounded-full -left-[5px] top-1.5"></div>
            <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
              <h4 class="font-bold text-surface-900">{{ item['项目名称'] || item['项目'] || '未知项目' }}</h4>
              <span class="text-xs text-surface-500 bg-surface-100 px-2 py-0.5 rounded">{{ item['时间'] || item['项目时间'] || '-' }}</span>
            </div>
            <p class="text-sm font-medium text-surface-700 mb-2">{{ item['角色'] || item['项目责任'] || item['职务'] || '' }}</p>
            <p v-if="item['项目描述'] || item['描述']" class="text-sm text-surface-600 whitespace-pre-wrap leading-relaxed mb-2"><span class="font-medium text-surface-700">项目描述：</span>{{ item['项目描述'] || item['描述'] }}</p>
            <p v-if="item['项目职责'] || item['责任描述'] || item['工作内容']" class="text-sm text-surface-600 whitespace-pre-wrap leading-relaxed bg-surface-50 p-3 rounded-lg"><span class="font-medium text-surface-700">责任内容：</span><br/>{{ item['项目职责'] || item['责任描述'] || item['工作内容'] }}</p>
            
            <div class="mt-2 text-xs text-surface-600 space-y-1">
              <div v-for="(v, k) in item" :key="k">
                <span v-if="!['项目名称', '项目', '时间', '项目时间', '角色', '项目责任', '职务', '项目描述', '描述', '项目职责', '责任描述', '工作内容'].includes(String(k))">
                  <span class="text-surface-400">{{ k }}:</span> {{ v }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 技能和其他 -->
      <section v-if="skills && (typeof skills === 'string' ? skills.length > 0 : Object.keys(skills).length > 0)" class="bg-white rounded-xl p-5 border border-surface-100 shadow-sm">
        <h3 class="text-base font-bold text-purple-600 flex items-center gap-2 mb-4 border-b border-surface-50 pb-2">
          <span>🛠️</span> 技能与专长
        </h3>
        <div v-if="typeof skills === 'string'" class="text-sm text-surface-700 whitespace-pre-wrap">
          {{ skills }}
        </div>
        <div v-else-if="Array.isArray(skills)" class="flex flex-wrap gap-2">
          <span v-for="(skill, i) in skills" :key="i" class="px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg text-sm border border-purple-100">
            {{ skill }}
          </span>
        </div>
        <div v-else class="space-y-2">
          <div v-for="(v, k) in skills" :key="k" class="text-sm">
            <span class="font-medium text-surface-700">{{ k }}: </span>
            <span class="text-surface-600">{{ v }}</span>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="min-h-screen flex">
    <!-- 左侧装饰区 -->
    <div
      class="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 relative overflow-hidden"
    >
      <!-- 装饰背景 -->
      <div class="absolute inset-0">
        <div
          class="absolute top-1/4 -left-20 w-80 h-80 bg-primary-400/20 rounded-full blur-3xl"
        />
        <div
          class="absolute bottom-1/4 right-0 w-96 h-96 bg-primary-300/10 rounded-full blur-3xl"
        />
        <div
          class="absolute top-1/2 left-1/3 w-64 h-64 bg-accent-400/10 rounded-full blur-3xl"
        />
      </div>

      <!-- 品牌内容 -->
      <div class="relative z-10 flex flex-col justify-center px-16 text-white">
        <div class="flex items-center gap-4 mb-8">
          <div
            class="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-md flex items-center justify-center text-2xl font-bold shadow-2xl"
          >
            R
          </div>
          <h1 class="text-3xl font-bold tracking-tight">ResumeGPT</h1>
        </div>

        <h2 class="text-4xl font-extrabold leading-tight mb-6">
          AI 驱动的
          <br />
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-accent-400 to-primary-200">
            智能简历审阅
          </span>
        </h2>

        <p class="text-lg text-primary-200 leading-relaxed max-w-lg mb-10">
          基于大模型与多智能体技术，实现简历的自动解析、评分与人岗匹配，为求职者和企业提供高效精准的匹配服务。
        </p>

        <div class="space-y-4">
          <div class="flex items-center gap-3 text-primary-200">
            <span
              class="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-sm"
            >🤖</span>
            <span>多智能体协同分析，全方位评估简历</span>
          </div>
          <div class="flex items-center gap-3 text-primary-200">
            <span
              class="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-sm"
            >📊</span>
            <span>BERT 语义匹配 + LLM 深度评估</span>
          </div>
          <div class="flex items-center gap-3 text-primary-200">
            <span
              class="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-sm"
            >🎯</span>
            <span>精准人岗匹配，可视化数据报告</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="flex-1 flex items-center justify-center px-6 py-12 bg-surface-50">
      <div class="w-full max-w-md">
        <RouterView />
      </div>
    </div>
  </div>
</template>

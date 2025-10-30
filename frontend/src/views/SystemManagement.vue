<template>
  <div class="system-management">
    <div class="container mx-auto px-4 py-8">
      <!-- Header -->
      <div class="header mb-8">
        <h1 class="text-3xl font-bold text-slate-900">系统管理</h1>
        <p class="text-slate-600 mt-2">AI 配置、监控、异步任务等系统功能管理</p>
      </div>

      <!-- Tabs -->
      <div class="tabs-container">
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            @click="activeTab = tab.key"
            :class="['tab', { 'tab-active': activeTab === tab.key }]"
          >
            <component :is="tab.icon" class="w-5 h-5" />
            <span>{{ tab.label }}</span>
            <span v-if="tab.badge" class="badge">{{ tab.badge }}</span>
          </button>
        </div>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- AI 供应商管理 -->
        <div v-if="activeTab === 'providers'" class="content-panel">
          <AIProviderManagement />
        </div>

        <!-- AI 功能配置 -->
        <div v-else-if="activeTab === 'functions'" class="content-panel">
          <AIFunctionConfig />
        </div>

        <!-- AI 调用监控 -->
        <div v-else-if="activeTab === 'monitoring'" class="content-panel">
          <AIMonitoring />
        </div>

        <!-- 异步任务 -->
        <div v-else-if="activeTab === 'tasks'" class="content-panel">
          <AsyncTaskManagement />
        </div>

        <!-- 番茄小说管理 -->
        <div v-else-if="activeTab === 'fanqie'" class="content-panel">
          <FanqieManagement />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, h } from 'vue'
import AIProviderManagement from '@/components/system/AIProviderManagement.vue'
import AIFunctionConfig from '@/components/system/AIFunctionConfig.vue'
import AIMonitoring from '@/components/system/AIMonitoring.vue'
import AsyncTaskManagement from '@/components/system/AsyncTaskManagement.vue'
import FanqieManagement from '@/components/system/FanqieManagement.vue'

const activeTab = ref('providers')

const tabs = [
  {
    key: 'providers',
    label: 'AI 供应商',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }, [
      h('path', { d: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5' })
    ])
  },
  {
    key: 'functions',
    label: '功能配置',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }, [
      h('circle', { cx: 12, cy: 12, r: 3 }),
      h('path', { d: 'M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24' })
    ])
  },
  {
    key: 'monitoring',
    label: 'AI 监控',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }, [
      h('path', { d: 'M3 3v18h18' }),
      h('path', { d: 'M18 17V9M13 17V5M8 17v-3' })
    ])
  },
  {
    key: 'tasks',
    label: '异步任务',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }, [
      h('circle', { cx: 12, cy: 12, r: 10 }),
      h('polyline', { points: '12 6 12 12 16 14' })
    ]),
    badge: '3'
  },
  {
    key: 'fanqie',
    label: '番茄小说',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }, [
      h('path', { d: 'M4 19.5A2.5 2.5 0 016.5 17H20' }),
      h('path', { d: 'M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z' })
    ])
  }
]
</script>

<style scoped>
.system-management {
  @apply min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40;
}

.header {
  @apply border-b border-slate-200 pb-6;
}

.tabs-container {
  @apply bg-white rounded-lg shadow-sm border border-slate-200 p-2 mb-6;
}

.tabs {
  @apply flex gap-2 overflow-x-auto;
}

.tab {
  @apply flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap;
  @apply text-slate-600 hover:text-slate-900 hover:bg-slate-50;
}

.tab-active {
  @apply bg-gradient-to-r from-indigo-50 to-indigo-100/80 text-indigo-700 shadow-sm ring-1 ring-indigo-200/50;
}

.badge {
  @apply ml-auto px-2 py-0.5 text-xs font-semibold bg-red-100 text-red-700 rounded-full;
}

.tab-content {
  @apply bg-white rounded-lg shadow-sm border border-slate-200 p-6;
}

.content-panel {
  @apply min-h-[600px];
}
</style>


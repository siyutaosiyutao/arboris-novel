<template>
  <div class="async-task-management">
    <div class="header">
      <h2 class="title">异步分析任务</h2>
      <div class="filters">
        <select v-model="statusFilter" @change="loadTasks" class="filter-select">
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">运行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <button @click="loadTasks" class="btn-refresh">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- Task List -->
    <div class="task-list">
      <div v-for="task in tasks" :key="task.id" class="task-card">
        <div class="task-header">
          <div class="task-info">
            <h3 class="task-title">{{ task.task_type }}</h3>
            <p class="task-id">ID: {{ task.id }}</p>
          </div>
          <span :class="['status-badge', `status-${task.status}`]">
            {{ statusText(task.status) }}
          </span>
        </div>

        <div class="task-details">
          <div class="detail-item">
            <span class="detail-label">项目:</span>
            <span class="detail-value">{{ task.project_name || task.project_id }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">创建时间:</span>
            <span class="detail-value">{{ formatDate(task.created_at) }}</span>
          </div>
          <div v-if="task.completed_at" class="detail-item">
            <span class="detail-label">完成时间:</span>
            <span class="detail-value">{{ formatDate(task.completed_at) }}</span>
          </div>
          <div v-if="task.progress" class="detail-item">
            <span class="detail-label">进度:</span>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
              <span class="progress-text">{{ task.progress }}%</span>
            </div>
          </div>
        </div>

        <div v-if="task.error" class="task-error">
          <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="error-text">{{ task.error }}</span>
        </div>

        <div class="task-actions">
          <button v-if="task.status === 'completed'" @click="viewResult(task)" class="btn-view">
            查看结果
          </button>
          <button v-if="task.status === 'pending' || task.status === 'running'" @click="cancelTask(task)" class="btn-cancel">
            取消任务
          </button>
        </div>
      </div>

      <div v-if="tasks.length === 0" class="empty-state">
        <svg class="w-16 h-16 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p class="text-slate-500 mt-4">暂无任务</p>
      </div>
    </div>

    <!-- Result Modal -->
    <div v-if="viewingTask" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">任务结果</h3>
          <button @click="closeModal" class="modal-close">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <pre class="result-content">{{ JSON.stringify(viewingTask.result, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { asyncAnalysisApi } from '@/api/novel'

const tasks = ref<any[]>([])
const statusFilter = ref('')
const viewingTask = ref<any>(null)

const statusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadTasks = async () => {
  try {
    tasks.value = await asyncAnalysisApi.getTasks(statusFilter.value)
  } catch (error: any) {
    console.error('加载任务失败:', error)
  }
}

const viewResult = (task: any) => {
  viewingTask.value = task
}

const cancelTask = async (task: any) => {
  if (!confirm('确定要取消此任务吗？')) return
  
  try {
    await asyncAnalysisApi.cancelTask(task.id)
    await loadTasks()
  } catch (error: any) {
    console.error('取消任务失败:', error)
  }
}

const closeModal = () => {
  viewingTask.value = null
}

onMounted(() => {
  loadTasks()
  // 每30秒自动刷新
  setInterval(loadTasks, 30000)
})
</script>

<style scoped>
.async-task-management {
  @apply space-y-6;
}

.header {
  @apply flex items-center justify-between;
}

.title {
  @apply text-2xl font-bold text-slate-900;
}

.filters {
  @apply flex items-center gap-3;
}

.filter-select {
  @apply px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent;
}

.btn-refresh {
  @apply flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors;
}

.task-list {
  @apply space-y-4;
}

.task-card {
  @apply bg-white border border-slate-200 rounded-lg p-6;
}

.task-header {
  @apply flex items-start justify-between mb-4;
}

.task-info {
  @apply flex-1;
}

.task-title {
  @apply text-lg font-semibold text-slate-900;
}

.task-id {
  @apply text-sm text-slate-500 mt-1;
}

.status-badge {
  @apply px-3 py-1 text-sm font-medium rounded-full;
}

.status-pending {
  @apply bg-gray-100 text-gray-700;
}

.status-running {
  @apply bg-blue-100 text-blue-700;
}

.status-completed {
  @apply bg-green-100 text-green-700;
}

.status-failed {
  @apply bg-red-100 text-red-700;
}

.task-details {
  @apply grid grid-cols-2 gap-4 mb-4;
}

.detail-item {
  @apply flex flex-col;
}

.detail-label {
  @apply text-xs text-slate-500 mb-1;
}

.detail-value {
  @apply text-sm font-medium text-slate-900;
}

.progress-bar {
  @apply relative w-full h-6 bg-slate-100 rounded-full overflow-hidden;
}

.progress-fill {
  @apply absolute inset-y-0 left-0 bg-indigo-600 transition-all duration-300;
}

.progress-text {
  @apply absolute inset-0 flex items-center justify-center text-xs font-medium text-slate-700;
}

.task-error {
  @apply flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg mb-4;
}

.error-text {
  @apply text-sm text-red-700;
}

.task-actions {
  @apply flex gap-2;
}

.btn-view {
  @apply px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors;
}

.btn-cancel {
  @apply px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors;
}

.empty-state {
  @apply flex flex-col items-center justify-center py-12;
}

/* Modal styles */
.modal-overlay {
  @apply fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4;
}

.modal-content {
  @apply bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto;
}

.modal-header {
  @apply flex items-center justify-between p-6 border-b border-slate-200;
}

.modal-title {
  @apply text-xl font-bold text-slate-900;
}

.modal-close {
  @apply text-slate-400 hover:text-slate-600 transition-colors;
}

.modal-body {
  @apply p-6;
}

.result-content {
  @apply bg-slate-50 p-4 rounded-lg text-sm overflow-x-auto;
}
</style>


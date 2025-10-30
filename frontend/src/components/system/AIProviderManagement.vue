<template>
  <div class="ai-provider-management">
    <div class="header">
      <h2 class="title">AI 供应商管理</h2>
      <button @click="showAddModal = true" class="btn-primary">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        添加供应商
      </button>
    </div>

    <!-- Provider List -->
    <div class="provider-list">
      <div v-for="provider in providers" :key="provider.id" class="provider-card">
        <div class="provider-header">
          <div class="provider-info">
            <h3 class="provider-name">{{ provider.name }}</h3>
            <span class="provider-type">{{ provider.provider_type }}</span>
          </div>
          <div class="provider-status">
            <span :class="['status-badge', provider.is_active ? 'status-active' : 'status-inactive']">
              {{ provider.is_active ? '启用' : '禁用' }}
            </span>
            <span v-if="provider.health_status" :class="['health-badge', `health-${provider.health_status}`]">
              {{ healthStatusText(provider.health_status) }}
            </span>
          </div>
        </div>

        <div class="provider-details">
          <div class="detail-item">
            <span class="detail-label">模型:</span>
            <span class="detail-value">{{ provider.model_name }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">优先级:</span>
            <span class="detail-value">{{ provider.priority }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">限额:</span>
            <span class="detail-value">{{ provider.rate_limit || '无限制' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">超时:</span>
            <span class="detail-value">{{ provider.timeout }}s</span>
          </div>
        </div>

        <div class="provider-actions">
          <button @click="editProvider(provider)" class="btn-secondary">编辑</button>
          <button @click="toggleProvider(provider)" class="btn-secondary">
            {{ provider.is_active ? '禁用' : '启用' }}
          </button>
          <button @click="deleteProvider(provider)" class="btn-danger">删除</button>
        </div>
      </div>

      <div v-if="providers.length === 0" class="empty-state">
        <svg class="w-16 h-16 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p class="text-slate-500 mt-4">暂无 AI 供应商</p>
        <button @click="showAddModal = true" class="btn-primary mt-4">添加第一个供应商</button>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div v-if="showAddModal || editingProvider" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingProvider ? '编辑供应商' : '添加供应商' }}</h3>
          <button @click="closeModal" class="modal-close">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">供应商名称</label>
            <input v-model="formData.name" type="text" class="form-input" placeholder="例如: OpenAI GPT-4" />
          </div>

          <div class="form-group">
            <label class="form-label">供应商类型</label>
            <select v-model="formData.provider_type" class="form-input">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="azure">Azure OpenAI</option>
              <option value="custom">自定义</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">模型名称</label>
            <input v-model="formData.model_name" type="text" class="form-input" placeholder="例如: gpt-4" />
          </div>

          <div class="form-group">
            <label class="form-label">API Key</label>
            <input v-model="formData.api_key" type="password" class="form-input" placeholder="sk-..." />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">优先级</label>
              <input v-model.number="formData.priority" type="number" class="form-input" min="0" />
            </div>

            <div class="form-group">
              <label class="form-label">超时(秒)</label>
              <input v-model.number="formData.timeout" type="number" class="form-input" min="1" />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">限额(请求/分钟)</label>
            <input v-model.number="formData.rate_limit" type="number" class="form-input" placeholder="留空表示无限制" />
          </div>

          <div class="form-group">
            <label class="flex items-center gap-2">
              <input v-model="formData.is_active" type="checkbox" class="form-checkbox" />
              <span class="form-label mb-0">启用此供应商</span>
            </label>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-secondary">取消</button>
          <button @click="saveProvider" class="btn-primary">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { aiConfigApi } from '@/api/novel'

const providers = ref<any[]>([])
const showAddModal = ref(false)
const editingProvider = ref<any>(null)
const formData = ref({
  name: '',
  provider_type: 'openai',
  model_name: '',
  api_key: '',
  priority: 0,
  timeout: 30,
  rate_limit: null,
  is_active: true
})

const healthStatusText = (status: string) => {
  const map: Record<string, string> = {
    healthy: '健康',
    degraded: '降级',
    unhealthy: '异常'
  }
  return map[status] || status
}

const loadProviders = async () => {
  try {
    providers.value = await aiConfigApi.getProviders()
  } catch (error: any) {
    console.error('加载供应商失败:', error)
  }
}

const editProvider = (provider: any) => {
  editingProvider.value = provider
  formData.value = { ...provider }
}

const toggleProvider = async (provider: any) => {
  try {
    await aiConfigApi.updateProvider(provider.id, {
      ...provider,
      is_active: !provider.is_active
    })
    await loadProviders()
  } catch (error: any) {
    console.error('切换供应商状态失败:', error)
  }
}

const deleteProvider = async (provider: any) => {
  if (!confirm(`确定要删除供应商 "${provider.name}" 吗？`)) return
  
  try {
    await aiConfigApi.deleteProvider(provider.id)
    await loadProviders()
  } catch (error: any) {
    console.error('删除供应商失败:', error)
  }
}

const saveProvider = async () => {
  try {
    if (editingProvider.value) {
      await aiConfigApi.updateProvider(editingProvider.value.id, formData.value)
    } else {
      await aiConfigApi.addProvider(formData.value)
    }
    await loadProviders()
    closeModal()
  } catch (error: any) {
    console.error('保存供应商失败:', error)
  }
}

const closeModal = () => {
  showAddModal.value = false
  editingProvider.value = null
  formData.value = {
    name: '',
    provider_type: 'openai',
    model_name: '',
    api_key: '',
    priority: 0,
    timeout: 30,
    rate_limit: null,
    is_active: true
  }
}

onMounted(() => {
  loadProviders()
})
</script>

<style scoped>
.ai-provider-management {
  @apply space-y-6;
}

.header {
  @apply flex items-center justify-between;
}

.title {
  @apply text-2xl font-bold text-slate-900;
}

.provider-list {
  @apply grid gap-4;
}

.provider-card {
  @apply bg-white border border-slate-200 rounded-lg p-6 hover:shadow-md transition-shadow;
}

.provider-header {
  @apply flex items-start justify-between mb-4;
}

.provider-info {
  @apply flex items-center gap-3;
}

.provider-name {
  @apply text-lg font-semibold text-slate-900;
}

.provider-type {
  @apply px-2 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded;
}

.provider-status {
  @apply flex items-center gap-2;
}

.status-badge {
  @apply px-2 py-1 text-xs font-medium rounded;
}

.status-active {
  @apply bg-green-100 text-green-700;
}

.status-inactive {
  @apply bg-gray-100 text-gray-700;
}

.health-badge {
  @apply px-2 py-1 text-xs font-medium rounded;
}

.health-healthy {
  @apply bg-green-100 text-green-700;
}

.health-degraded {
  @apply bg-yellow-100 text-yellow-700;
}

.health-unhealthy {
  @apply bg-red-100 text-red-700;
}

.provider-details {
  @apply grid grid-cols-2 md:grid-cols-4 gap-4 mb-4;
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

.provider-actions {
  @apply flex gap-2;
}

.empty-state {
  @apply flex flex-col items-center justify-center py-12;
}

/* Modal styles */
.modal-overlay {
  @apply fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4;
}

.modal-content {
  @apply bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto;
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
  @apply p-6 space-y-4;
}

.modal-footer {
  @apply flex justify-end gap-3 p-6 border-t border-slate-200;
}

.form-group {
  @apply space-y-2;
}

.form-row {
  @apply grid grid-cols-2 gap-4;
}

.form-label {
  @apply text-sm font-medium text-slate-700;
}

.form-input {
  @apply w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent;
}

.form-checkbox {
  @apply w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500;
}

.btn-primary {
  @apply flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors;
}

.btn-secondary {
  @apply px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors;
}

.btn-danger {
  @apply px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-50 transition-colors;
}
</style>


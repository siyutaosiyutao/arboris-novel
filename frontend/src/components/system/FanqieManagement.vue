<template>
  <div class="fanqie-management">
    <div class="header">
      <h2 class="title">番茄小说管理</h2>
      <p class="description">管理番茄小说账号、Cookie 和上传记录</p>
    </div>

    <!-- Account Management -->
    <div class="section">
      <div class="section-header">
        <h3 class="section-title">账号管理</h3>
        <button @click="showAddAccount = true" class="btn-primary">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          添加账号
        </button>
      </div>

      <div class="account-list">
        <div v-for="account in accounts" :key="account.id" class="account-card">
          <div class="account-header">
            <div>
              <h4 class="account-name">{{ account.name }}</h4>
              <p class="account-identifier">标识: {{ account.identifier }}</p>
            </div>
            <span :class="['cookie-status', account.cookie_valid ? 'status-valid' : 'status-invalid']">
              {{ account.cookie_valid ? 'Cookie 有效' : 'Cookie 失效' }}
            </span>
          </div>

          <div class="account-stats">
            <div class="stat">
              <span class="stat-label">上传书籍:</span>
              <span class="stat-value">{{ account.books_count || 0 }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">上传章节:</span>
              <span class="stat-value">{{ account.chapters_count || 0 }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">最后上传:</span>
              <span class="stat-value">{{ account.last_upload ? formatDate(account.last_upload) : '从未' }}</span>
            </div>
          </div>

          <div class="account-actions">
            <button @click="loginAccount(account)" class="btn-login">
              {{ account.cookie_valid ? '重新登录' : '立即登录' }}
            </button>
            <button @click="viewUploadHistory(account)" class="btn-secondary">上传记录</button>
            <button @click="deleteAccount(account)" class="btn-danger">删除</button>
          </div>
        </div>

        <div v-if="accounts.length === 0" class="empty-state">
          <svg class="w-16 h-16 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <p class="text-slate-500 mt-4">暂无番茄小说账号</p>
          <button @click="showAddAccount = true" class="btn-primary mt-4">添加第一个账号</button>
        </div>
      </div>
    </div>

    <!-- Upload History -->
    <div class="section">
      <h3 class="section-title">最近上传记录</h3>
      <div class="upload-history">
        <table class="history-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>账号</th>
              <th>书籍</th>
              <th>章节数</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in uploadHistory" :key="record.id">
              <td>{{ formatDate(record.created_at) }}</td>
              <td>{{ record.account_name }}</td>
              <td>{{ record.book_name }}</td>
              <td>{{ record.chapter_count }}</td>
              <td>
                <span :class="['status-badge', `status-${record.status}`]">
                  {{ statusText(record.status) }}
                </span>
              </td>
              <td>
                <button v-if="record.status === 'failed'" @click="retryUpload(record)" class="btn-retry">
                  重试
                </button>
                <button @click="viewDetails(record)" class="btn-view">详情</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="uploadHistory.length === 0" class="empty-state-small">
          <p class="text-slate-500">暂无上传记录</p>
        </div>
      </div>
    </div>

    <!-- Add Account Modal -->
    <div v-if="showAddAccount" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">添加番茄小说账号</h3>
          <button @click="closeModal" class="modal-close">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">账号名称</label>
            <input v-model="newAccount.name" type="text" class="form-input" placeholder="例如: 主账号" />
          </div>

          <div class="form-group">
            <label class="form-label">账号标识</label>
            <input v-model="newAccount.identifier" type="text" class="form-input" placeholder="例如: main" />
            <p class="form-hint">用于区分不同账号的 Cookie 文件</p>
          </div>

          <div class="alert alert-info">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>添加账号后，需要点击"立即登录"按钮在浏览器中完成登录，系统会自动保存 Cookie。</p>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-secondary">取消</button>
          <button @click="addAccount" class="btn-primary">添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { novelApi } from '@/api/novel'

const accounts = ref<any[]>([])
const uploadHistory = ref<any[]>([])
const showAddAccount = ref(false)
const newAccount = ref({
  name: '',
  identifier: ''
})

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const statusText = (status: string) => {
  const map: Record<string, string> = {
    success: '成功',
    failed: '失败',
    pending: '进行中'
  }
  return map[status] || status
}

const loadAccounts = async () => {
  // TODO: 实现加载账号列表的 API
  accounts.value = [
    {
      id: '1',
      name: '主账号',
      identifier: 'default',
      cookie_valid: true,
      books_count: 3,
      chapters_count: 150,
      last_upload: new Date().toISOString()
    }
  ]
}

const loadUploadHistory = async () => {
  // TODO: 实现加载上传记录的 API
  uploadHistory.value = []
}

const loginAccount = async (account: any) => {
  try {
    await novelApi.fanqieLogin(account.identifier, 120)
    await loadAccounts()
  } catch (error: any) {
    console.error('登录失败:', error)
  }
}

const viewUploadHistory = (account: any) => {
  // TODO: 实现查看上传记录
  console.log('查看上传记录:', account)
}

const deleteAccount = async (account: any) => {
  if (!confirm(`确定要删除账号 "${account.name}" 吗？`)) return
  
  // TODO: 实现删除账号的 API
  await loadAccounts()
}

const addAccount = async () => {
  if (!newAccount.value.name || !newAccount.value.identifier) {
    alert('请填写完整信息')
    return
  }
  
  // TODO: 实现添加账号的 API
  await loadAccounts()
  closeModal()
}

const retryUpload = (record: any) => {
  // TODO: 实现重试上传
  console.log('重试上传:', record)
}

const viewDetails = (record: any) => {
  // TODO: 实现查看详情
  console.log('查看详情:', record)
}

const closeModal = () => {
  showAddAccount.value = false
  newAccount.value = {
    name: '',
    identifier: ''
  }
}

onMounted(() => {
  loadAccounts()
  loadUploadHistory()
})
</script>

<style scoped>
.fanqie-management {
  @apply space-y-6;
}

.header {
  @apply mb-6;
}

.title {
  @apply text-2xl font-bold text-slate-900;
}

.description {
  @apply text-sm text-slate-600 mt-1;
}

.section {
  @apply bg-white border border-slate-200 rounded-lg p-6;
}

.section-header {
  @apply flex items-center justify-between mb-4;
}

.section-title {
  @apply text-lg font-semibold text-slate-900;
}

.account-list {
  @apply space-y-4;
}

.account-card {
  @apply border border-slate-200 rounded-lg p-4;
}

.account-header {
  @apply flex items-start justify-between mb-3;
}

.account-name {
  @apply font-semibold text-slate-900;
}

.account-identifier {
  @apply text-sm text-slate-500 mt-1;
}

.cookie-status {
  @apply px-2 py-1 text-xs font-medium rounded;
}

.status-valid {
  @apply bg-green-100 text-green-700;
}

.status-invalid {
  @apply bg-red-100 text-red-700;
}

.account-stats {
  @apply grid grid-cols-3 gap-4 mb-3;
}

.stat {
  @apply flex flex-col;
}

.stat-label {
  @apply text-xs text-slate-500;
}

.stat-value {
  @apply text-sm font-medium text-slate-900 mt-1;
}

.account-actions {
  @apply flex gap-2;
}

.btn-login {
  @apply px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors;
}

.upload-history {
  @apply overflow-x-auto;
}

.history-table {
  @apply w-full text-sm;
}

.history-table thead {
  @apply bg-slate-50 border-b border-slate-200;
}

.history-table th {
  @apply px-4 py-3 text-left font-medium text-slate-700;
}

.history-table td {
  @apply px-4 py-3 border-b border-slate-100;
}

.status-badge {
  @apply px-2 py-1 text-xs font-medium rounded;
}

.status-success {
  @apply bg-green-100 text-green-700;
}

.status-failed {
  @apply bg-red-100 text-red-700;
}

.status-pending {
  @apply bg-blue-100 text-blue-700;
}

.btn-retry {
  @apply px-3 py-1 text-xs font-medium text-orange-600 bg-orange-50 rounded hover:bg-orange-100 transition-colors mr-2;
}

.btn-view {
  @apply px-3 py-1 text-xs font-medium text-indigo-600 bg-indigo-50 rounded hover:bg-indigo-100 transition-colors;
}

.empty-state {
  @apply flex flex-col items-center justify-center py-12;
}

.empty-state-small {
  @apply text-center py-8;
}

.alert {
  @apply flex items-start gap-3 p-4 rounded-lg;
}

.alert-info {
  @apply bg-blue-50 border border-blue-200 text-blue-800;
}

/* Modal styles */
.modal-overlay {
  @apply fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4;
}

.modal-content {
  @apply bg-white rounded-lg shadow-xl max-w-2xl w-full;
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

.form-label {
  @apply text-sm font-medium text-slate-700;
}

.form-input {
  @apply w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent;
}

.form-hint {
  @apply text-xs text-slate-500;
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


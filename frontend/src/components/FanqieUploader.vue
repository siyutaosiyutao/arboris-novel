<template>
  <div class="fanqie-uploader">
    <!-- 上传按钮 -->
    <div class="upload-section">
      <div class="section-header">
        <h3 class="section-title">📚 番茄小说上传</h3>
        <p class="section-description">一键上传小说到番茄小说平台</p>
      </div>

      <!-- 状态显示 -->
      <div v-if="uploadStatus" class="status-card" :class="statusClass">
        <div class="status-icon">
          <svg v-if="uploadStatus.type === 'success'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else-if="uploadStatus.type === 'error'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <svg v-else class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <div class="status-content">
          <p class="status-message">{{ uploadStatus.message }}</p>
          <p v-if="uploadStatus.hint" class="status-hint">{{ uploadStatus.hint }}</p>
        </div>
      </div>

      <!-- Cookie状态 -->
      <div class="cookie-status">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="status-dot" :class="hasCookie ? 'bg-green-500' : 'bg-gray-300'"></div>
            <span class="text-sm text-slate-600">
              Cookie状态: {{ hasCookie ? '已保存' : '未登录' }}
            </span>
          </div>
          <button
            v-if="!hasCookie"
            @click="handleLogin"
            :disabled="isLoggingIn"
            class="btn-secondary"
          >
            {{ isLoggingIn ? '登录中...' : '立即登录' }}
          </button>
        </div>
      </div>

      <!-- 上传设置 -->
      <div class="upload-settings">
        <div class="setting-item">
          <label class="setting-label">账号标识</label>
          <input
            v-model="account"
            type="text"
            class="setting-input"
            placeholder="default"
          />
          <p class="setting-hint">用于区分不同番茄小说账号的Cookie</p>
        </div>

        <div class="setting-item">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              v-model="headless"
              type="checkbox"
              class="setting-checkbox"
            />
            <span class="setting-label">无头模式</span>
          </label>
          <p class="setting-hint">生产环境建议开启，调试时可关闭</p>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button
          @click="handleUpload"
          :disabled="isUploading || !hasCookie"
          class="btn-primary"
        >
          <svg v-if="!isUploading" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <svg v-else class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>{{ isUploading ? '上传中...' : '一键上传' }}</span>
        </button>
      </div>

      <!-- 使用说明 -->
      <div class="help-section">
        <h4 class="help-title">📖 使用说明</h4>
        <ol class="help-list">
          <li>在番茄小说平台手动创建一本新书，书名与本地小说名称一致</li>
          <li>点击"立即登录"按钮，在弹出的浏览器中完成登录</li>
          <li>登录成功后，Cookie会自动保存</li>
          <li>点击"一键上传"按钮，系统会自动同步分卷和章节</li>
          <li>上传过程中如遇错误会立即停止，请根据提示处理</li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { novelApi } from '@/api/novel'

const props = defineProps<{
  projectId: string
}>()

// 状态
const account = ref('default')
const headless = ref(true)
const isUploading = ref(false)
const isLoggingIn = ref(false)
const hasCookie = ref(false)
const uploadStatus = ref<{
  type: 'success' | 'error' | 'loading'
  message: string
  hint?: string
} | null>(null)

// 计算属性
const statusClass = computed(() => {
  if (!uploadStatus.value) return ''
  return {
    'status-success': uploadStatus.value.type === 'success',
    'status-error': uploadStatus.value.type === 'error',
    'status-loading': uploadStatus.value.type === 'loading'
  }
})

// 检查Cookie状态
const checkCookieStatus = () => {
  // 这里可以添加检查Cookie文件是否存在的逻辑
  // 暂时假设如果登录过就有Cookie
  hasCookie.value = localStorage.getItem(`fanqie_cookie_${account.value}`) === 'true'
}

// 处理登录
const handleLogin = async () => {
  isLoggingIn.value = true
  uploadStatus.value = {
    type: 'loading',
    message: '正在打开浏览器，请在浏览器中完成登录...'
  }

  try {
    const result = await novelApi.fanqieLogin(account.value, 120)
    
    if (result.success) {
      hasCookie.value = true
      localStorage.setItem(`fanqie_cookie_${account.value}`, 'true')
      uploadStatus.value = {
        type: 'success',
        message: '登录成功！Cookie已保存'
      }
    } else {
      uploadStatus.value = {
        type: 'error',
        message: result.error || '登录失败',
        hint: '请确保在浏览器中完成了登录操作'
      }
    }
  } catch (error: any) {
    uploadStatus.value = {
      type: 'error',
      message: '登录失败: ' + error.message
    }
  } finally {
    isLoggingIn.value = false
  }
}

// 处理上传
const handleUpload = async () => {
  if (!hasCookie.value) {
    uploadStatus.value = {
      type: 'error',
      message: '请先登录番茄小说',
      hint: '点击"立即登录"按钮完成登录'
    }
    return
  }

  isUploading.value = true
  uploadStatus.value = {
    type: 'loading',
    message: '正在上传小说到番茄小说平台...'
  }

  try {
    const result = await novelApi.uploadToFanqie(props.projectId, account.value, headless.value)
    
    if (result.success) {
      uploadStatus.value = {
        type: 'success',
        message: `上传成功！共上传 ${result.chapter_count} 章节到 ${result.volume_count} 个分卷`,
        hint: `书籍ID: ${result.book_id}`
      }
    } else {
      uploadStatus.value = {
        type: 'error',
        message: result.error || '上传失败',
        hint: result.hint
      }
      
      // 如果是Cookie失效，更新状态
      if (result.error?.includes('Cookie')) {
        hasCookie.value = false
        localStorage.removeItem(`fanqie_cookie_${account.value}`)
      }
    }
  } catch (error: any) {
    uploadStatus.value = {
      type: 'error',
      message: '上传失败: ' + error.message
    }
  } finally {
    isUploading.value = false
  }
}

// 初始化
checkCookieStatus()
</script>

<style scoped>
.fanqie-uploader {
  @apply w-full;
}

.upload-section {
  @apply space-y-6;
}

.section-header {
  @apply border-b border-slate-200 pb-4;
}

.section-title {
  @apply text-2xl font-bold text-slate-900;
}

.section-description {
  @apply text-sm text-slate-600 mt-1;
}

.status-card {
  @apply flex items-start gap-4 p-4 rounded-lg border;
}

.status-success {
  @apply bg-green-50 border-green-200;
}

.status-error {
  @apply bg-red-50 border-red-200;
}

.status-loading {
  @apply bg-blue-50 border-blue-200;
}

.status-icon {
  @apply flex-shrink-0;
}

.status-success .status-icon {
  @apply text-green-600;
}

.status-error .status-icon {
  @apply text-red-600;
}

.status-loading .status-icon {
  @apply text-blue-600;
}

.status-content {
  @apply flex-1;
}

.status-message {
  @apply font-medium text-slate-900;
}

.status-hint {
  @apply text-sm text-slate-600 mt-1;
}

.cookie-status {
  @apply p-4 bg-slate-50 rounded-lg border border-slate-200;
}

.status-dot {
  @apply w-2 h-2 rounded-full;
}

.upload-settings {
  @apply space-y-4;
}

.setting-item {
  @apply space-y-2;
}

.setting-label {
  @apply text-sm font-medium text-slate-700;
}

.setting-input {
  @apply w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent;
}

.setting-checkbox {
  @apply w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500;
}

.setting-hint {
  @apply text-xs text-slate-500;
}

.action-buttons {
  @apply flex gap-3;
}

.btn-primary {
  @apply flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg;
}

.btn-secondary {
  @apply px-4 py-2 text-sm font-medium text-indigo-600 bg-white border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-all duration-200;
}

.help-section {
  @apply p-4 bg-amber-50 border border-amber-200 rounded-lg;
}

.help-title {
  @apply text-sm font-semibold text-amber-900 mb-2;
}

.help-list {
  @apply text-sm text-amber-800 space-y-1 list-decimal list-inside;
}
</style>


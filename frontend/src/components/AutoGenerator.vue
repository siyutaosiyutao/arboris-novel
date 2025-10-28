<template>
  <div class="auto-generator-panel">
    <div class="panel-header">
      <h2>🤖 自动生成器</h2>
      <p class="subtitle">设置后系统将日夜不停地自动生成小说章节</p>
    </div>

    <!-- 创建任务表单 -->
    <div v-if="!currentTask || currentTask.status === 'completed' || currentTask.status === 'stopped'" class="create-form">
      <h3>创建新任务</h3>

      <!-- 智能提示 -->
      <div class="info-banner">
        <span class="info-icon">💡</span>
        <div class="info-content">
          <strong>智能大纲生成</strong>
          <p>当检测到大纲不足时，系统会自动生成新的10章大纲，实现真正的无限自动生成！</p>
        </div>
      </div>

      <div class="form-group">
        <label>目标章节数</label>
        <input 
          v-model.number="form.targetChapters" 
          type="number" 
          placeholder="留空表示无限生成"
          min="1"
        />
        <span class="hint">不填写则持续生成直到手动停止</span>
      </div>

      <div class="form-group">
        <label>生成间隔（秒）</label>
        <input 
          v-model.number="form.intervalSeconds" 
          type="number" 
          min="10"
          placeholder="60"
        />
        <span class="hint">每生成一章后等待的时间，建议60秒以上</span>
      </div>

      <div class="form-group">
        <label>
          <input v-model="form.autoSelectVersion" type="checkbox" />
          自动选择版本
        </label>
        <span class="hint">自动选择第一个生成的版本，否则需要手动选择</span>
      </div>

      <div class="form-group">
        <label>每章生成版本数</label>
        <input
          v-model.number="form.versionCount"
          type="number"
          min="1"
          max="5"
          placeholder="1"
        />
        <span class="hint">默认生成1个版本，可设置1-5个版本供选择</span>
      </div>

      <div class="creative-features-section">
        <h4>🎨 创意功能（AI自动分析）</h4>
        <p class="section-hint">这些功能会在章节生成后自动运行，提供智能分析和建议</p>
        
        <div class="feature-toggles">
          <label class="feature-toggle">
            <input v-model="form.enableTensionAnalysis" type="checkbox" />
            <div class="feature-info">
              <span class="feature-name">📊 情节张力分析</span>
              <span class="feature-desc">自动分析章节的张力、冲突强度和节奏</span>
            </div>
          </label>
          
          <label class="feature-toggle">
            <input v-model="form.enableCharacterConsistency" type="checkbox" />
            <div class="feature-info">
              <span class="feature-name">👤 角色一致性检查</span>
              <span class="feature-desc">检查角色行为是否符合设定</span>
            </div>
          </label>
          
          <label class="feature-toggle">
            <input v-model="form.enableForeshadowing" type="checkbox" />
            <div class="feature-info">
              <span class="feature-name">🔮 伏笔自动识别</span>
              <span class="feature-desc">识别和追踪章节中的伏笔</span>
            </div>
          </label>
        </div>
      </div>

      <button @click="createTask" class="btn-primary" :disabled="loading">
        {{ loading ? '创建中...' : '创建并启动任务' }}
      </button>
    </div>

    <!-- 任务状态显示 -->
    <div v-if="currentTask" class="task-status">
      <h3>当前任务状态</h3>
      
      <div class="status-card">
        <div class="status-badge" :class="currentTask.status">
          {{ getStatusText(currentTask.status) }}
        </div>
        
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">已生成章节</span>
            <span class="stat-value">{{ currentTask.chapters_generated }}</span>
          </div>
          
          <div class="stat-item" v-if="currentTask.target_chapters">
            <span class="stat-label">目标章节</span>
            <span class="stat-value">{{ currentTask.target_chapters }}</span>
          </div>
          
          <div class="stat-item" v-if="currentTask.target_chapters">
            <span class="stat-label">进度</span>
            <span class="stat-value">
              {{ Math.round((currentTask.chapters_generated / currentTask.target_chapters) * 100) }}%
            </span>
          </div>
          
          <div class="stat-item">
            <span class="stat-label">错误次数</span>
            <span class="stat-value" :class="{ error: currentTask.error_count > 0 }">
              {{ currentTask.error_count }}
            </span>
          </div>
        </div>

        <div v-if="currentTask.last_generation_at" class="last-generation">
          最后生成时间: {{ formatTime(currentTask.last_generation_at) }}
        </div>

        <div v-if="currentTask.last_error" class="error-message">
          ⚠️ {{ currentTask.last_error }}
        </div>

        <!-- 控制按钮 -->
        <div class="control-buttons">
          <button 
            v-if="currentTask.status === 'pending' || currentTask.status === 'paused'"
            @click="startTask"
            class="btn-success"
            :disabled="loading"
          >
            ▶️ 启动
          </button>
          
          <button 
            v-if="currentTask.status === 'running'"
            @click="pauseTask"
            class="btn-warning"
            :disabled="loading"
          >
            ⏸️ 暂停
          </button>
          
          <button 
            v-if="currentTask.status === 'running' || currentTask.status === 'paused'"
            @click="stopTask"
            class="btn-danger"
            :disabled="loading"
          >
            ⏹️ 停止
          </button>
        </div>
      </div>
    </div>

    <!-- 日志显示 -->
    <div v-if="currentTask" class="logs-section">
      <h3>生成日志</h3>
      <div class="logs-container">
        <div 
          v-for="log in logs" 
          :key="log.id" 
          class="log-item"
          :class="log.log_type"
        >
          <span class="log-time">{{ formatTime(log.created_at) }}</span>
          <span class="log-type">{{ log.log_type.toUpperCase() }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" class="no-logs">
          暂无日志
        </div>
      </div>
      <button @click="refreshLogs" class="btn-secondary">刷新日志</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/base'

// 接受 props
const props = defineProps({
  projectId: {
    type: String,
    required: false
  }
})

const route = useRoute()
// 优先使用 props，否则从路由获取
const projectId = props.projectId || route.params.id

const loading = ref(false)
const currentTask = ref(null)
const logs = ref([])
const refreshInterval = ref(null)

const form = ref({
  targetChapters: null,
  intervalSeconds: 60,
  autoSelectVersion: true,
  versionCount: 1,
  enableTensionAnalysis: true,
  enableCharacterConsistency: true,
  enableForeshadowing: true
})

const createTask = async () => {
  loading.value = true
  try {
    const task = await api.post('/api/auto-generator/tasks', {
      project_id: projectId,
      target_chapters: form.value.targetChapters || null,
      interval_seconds: form.value.intervalSeconds,
      auto_select_version: form.value.autoSelectVersion,
      generation_config: {
        version_count: form.value.versionCount,
        enable_tension_analysis: form.value.enableTensionAnalysis,
        enable_character_consistency: form.value.enableCharacterConsistency,
        enable_foreshadowing: form.value.enableForeshadowing
      }
    })

    currentTask.value = task

    // 自动启动
    await startTask()
  } catch (error) {
    alert('创建任务失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const startTask = async () => {
  if (!currentTask.value) return

  loading.value = true
  try {
    const task = await api.post(`/api/auto-generator/tasks/${currentTask.value.id}/start`)
    currentTask.value = task
    await refreshLogs()
    startAutoRefresh()
  } catch (error) {
    alert('启动任务失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const pauseTask = async () => {
  if (!currentTask.value) return

  loading.value = true
  try {
    const task = await api.post(`/api/auto-generator/tasks/${currentTask.value.id}/pause`)
    currentTask.value = task
    stopAutoRefresh()
  } catch (error) {
    alert('暂停任务失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const stopTask = async () => {
  if (!currentTask.value) return

  if (!confirm('确定要停止任务吗？停止后无法恢复。')) return

  loading.value = true
  try {
    const task = await api.post(`/api/auto-generator/tasks/${currentTask.value.id}/stop`)
    currentTask.value = task
    stopAutoRefresh()
  } catch (error) {
    alert('停止任务失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const refreshStatus = async () => {
  if (!currentTask.value) return

  try {
    const task = await api.get(`/api/auto-generator/tasks/${currentTask.value.id}`)
    currentTask.value = task
  } catch (error) {
    console.error('刷新状态失败:', error)
  }
}

const refreshLogs = async () => {
  if (!currentTask.value) return

  try {
    const taskLogs = await api.get(`/api/auto-generator/tasks/${currentTask.value.id}/logs`)
    logs.value = taskLogs
  } catch (error) {
    console.error('刷新日志失败:', error)
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshInterval.value = setInterval(() => {
    refreshStatus()
    refreshLogs()
  }, 5000) // 每5秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '等待中',
    running: '运行中',
    paused: '已暂停',
    stopped: '已停止',
    completed: '已完成',
    error: '错误'
  }
  return statusMap[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(async () => {
  // 检查是否有现有任务
  try {
    const tasks = await api.get(`/api/auto-generator/projects/${projectId}/tasks`)
    const taskList = Array.isArray(tasks) ? tasks : []

    // 查找运行中或暂停的任务
    const activeTask = taskList.find(t =>
      t.status === 'running' ||
      t.status === 'paused' ||
      t.status === 'pending'
    )

    if (activeTask) {
      currentTask.value = activeTask
      await refreshLogs()

      // 如果任务正在运行，启动自动刷新
      if (activeTask.status === 'running') {
        startAutoRefresh()
      }
    }
  } catch (error) {
    console.error('加载现有任务失败:', error)
    // 如果 API 不存在（还未实现），静默失败
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.auto-generator-panel {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.panel-header {
  text-align: center;
  margin-bottom: 30px;
}

.panel-header h2 {
  font-size: 28px;
  margin-bottom: 10px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.create-form, .task-status, .logs-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-group input[type="number"],
.form-group input[type="text"] {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
}

.hint {
  display: block;
  margin-top: 5px;
  font-size: 12px;
  color: #999;
}

.info-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.info-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.info-content {
  flex: 1;
}

.info-content strong {
  display: block;
  font-size: 16px;
  margin-bottom: 4px;
}

.info-content p {
  margin: 0;
  font-size: 14px;
  opacity: 0.95;
  line-height: 1.5;
}

.btn-primary, .btn-success, .btn-warning, .btn-danger, .btn-secondary {
  padding: 12px 24px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-warning {
  background: #ffc107;
  color: #333;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  margin-top: 10px;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
}

.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 20px;
}

.status-badge.pending { background: #ffc107; color: #333; }
.status-badge.running { background: #28a745; color: white; }
.status-badge.paused { background: #6c757d; color: white; }
.status-badge.stopped { background: #dc3545; color: white; }
.status-badge.completed { background: #17a2b8; color: white; }
.status-badge.error { background: #dc3545; color: white; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.stat-value.error {
  color: #dc3545;
}

.last-generation {
  font-size: 14px;
  color: #666;
  margin-bottom: 15px;
}

.error-message {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 15px;
  color: #856404;
  font-size: 14px;
}

.control-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.logs-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 10px;
  background: #f8f9fa;
}

.log-item {
  padding: 8px;
  margin-bottom: 5px;
  border-radius: 4px;
  font-size: 13px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.log-item.info { background: #d1ecf1; }
.log-item.success { background: #d4edda; }
.log-item.warning { background: #fff3cd; }
.log-item.error { background: #f8d7da; }

.log-time {
  color: #666;
  font-size: 11px;
  white-space: nowrap;
}

.log-type {
  font-weight: bold;
  font-size: 11px;
  white-space: nowrap;
}

.log-message {
  flex: 1;
}

.no-logs {
  text-align: center;
  color: #999;
  padding: 20px;
}

.creative-features-section {
  margin-top: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px dashed #007bff;
}

.creative-features-section h4 {
  margin: 0 0 10px 0;
  color: #007bff;
}

.section-hint {
  font-size: 13px;
  color: #666;
  margin-bottom: 15px;
}

.feature-toggles {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-toggle {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.feature-toggle:hover {
  background: #e3f2fd;
}

.feature-toggle input[type="checkbox"] {
  margin-top: 4px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.feature-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.feature-name {
  font-weight: 500;
  font-size: 14px;
  color: #333;
}

.feature-desc {
  font-size: 12px;
  color: #666;
}
</style>

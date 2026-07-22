<template>
  <div class="home">
    <header class="hero">
      <h1 class="hero-title">AI 旅行规划助手</h1>
      <p class="hero-sub">告诉我你想去哪，剩下的事情交给我</p>
    </header>

    <form class="card form" @submit.prevent="submit">
      <!-- ── 目的地 ──────────────────────────────────────── -->
      <div class="form-group">
        <label class="form-label">目的地城市</label>
        <input
          v-model="form.city"
          class="form-input"
          type="text"
          placeholder="例如：杭州、成都、东京"
          required
        />
      </div>

      <!-- ── 日期 & 天数 ─────────────────────────────────── -->
      <div class="form-row">
        <div class="form-group flex-1">
          <label class="form-label">开始日期</label>
          <input v-model="form.start_date" class="form-input" type="date" required />
        </div>
        <div class="form-group flex-1">
          <label class="form-label">结束日期</label>
          <input
            v-model="form.end_date"
            class="form-input"
            type="date"
            :min="form.start_date"
            required
          />
        </div>
        <div class="form-group days-group">
          <label class="form-label">天数</label>
          <input
            v-model.number="form.days"
            class="form-input"
            type="number"
            min="1"
            max="30"
            required
          />
        </div>
      </div>

      <!-- ── 交通 & 住宿 ─────────────────────────────────── -->
      <div class="form-row">
        <div class="form-group flex-1">
          <label class="form-label">交通方式</label>
          <select v-model="form.transportation" class="form-input" required>
            <option value="" disabled>请选择</option>
            <option value="公共交通">公共交通</option>
            <option value="自驾">自驾</option>
            <option value="出租车+地铁">出租车 + 地铁</option>
            <option value="租车">租车自驾</option>
          </select>
        </div>
        <div class="form-group flex-1">
          <label class="form-label">住宿偏好</label>
          <select v-model="form.accommodation" class="form-input" required>
            <option value="" disabled>请选择</option>
            <option value="经济型">经济型</option>
            <option value="舒适型">舒适型</option>
            <option value="豪华型">豪华型</option>
          </select>
        </div>
      </div>

      <!-- ── 旅行偏好（多选标签） ──────────────────────── -->
      <div class="form-group">
        <label class="form-label">旅行偏好（可多选）</label>
        <div class="tag-group">
          <button
            v-for="p in PREFERENCES"
            :key="p"
            type="button"
            class="tag"
            :class="{ active: form.preferences.includes(p) }"
            @click="togglePreference(p)"
          >
            {{ p }}
          </button>
        </div>
      </div>

      <!-- ── 额外要求 ────────────────────────────────────── -->
      <div class="form-group">
        <label class="form-label">额外要求（选填）</label>
        <textarea
          v-model="form.free_text_input"
          class="form-input form-textarea"
          placeholder="例如：带老人出行少爬楼梯、想要每天的咖啡馆推荐、对海鲜过敏..."
          rows="3"
        ></textarea>
      </div>

      <!-- ── 提交（按钮内嵌进度条） ──────────────────── -->
      <button type="submit" class="btn-submit" :class="{ loading: loading }" :disabled="loading">
        <div v-if="loading" class="progress-bar" :style="{ width: progress + '%' }"></div>
        <span class="btn-text">
          <span v-if="!loading">开始规划</span>
          <span v-else-if="progress < 100">{{ progressText }}</span>
          <span v-else>✓ 完成！</span>
        </span>
      </button>

      <!-- ── 错误提示 ────────────────────────────────────── -->
      <p v-if="error" class="error-msg">{{ error }}</p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { createTravelPlan } from '../services/api'
import { addPlan } from '../services/planStore'
import type { TripPlanRequest } from '../types'

const PREFERENCES = ['自然风光', '人文历史', '美食', '购物', '亲子', '摄影']

const router = useRouter()

const form = reactive<TripPlanRequest>({
  city: '',
  start_date: '',
  end_date: '',
  days: 3,
  transportation: '公共交通',
  accommodation: '经济型',
  preferences: [],
  free_text_input: '',
})

const loading = ref(false)
const error = ref('')
const progress = ref(0)

// ── 进度条：定时器 ──────────────────────────────────────────────


// ── 进度条：时间驱动的对数曲线 ──────────────────────────────
let progressTimer: ReturnType<typeof setInterval> | null = null
let progressStart = 0

const PROGRESS_CAP = 99.5       // 封顶百分比（API 返回前永不达到 100）
const TIME_CONSTANT = 21       // 时间常数（秒），93秒时约达98.6%

/** 阶段性文案 */
const progressText = computed(() => {
  if (progress.value < 25) return '连接中...'
  if (progress.value < 75) return 'AI 搜索景点/酒店/天气中...'
  return 'AI 生成旅行计划中...'
})

/** 启动模拟进度（每 200ms 根据耗时计算一次） */
function startProgress() {
  progress.value = 0
  progressStart = Date.now()

  progressTimer = setInterval(() => {
    const elapsed = (Date.now() - progressStart) / 1000  // 秒
    // 对数曲线: progress = CAP × (1 - e^(-t / Tau))
    // 永远在增长，但越来越慢，永不撞墙
    progress.value = Math.min(
      PROGRESS_CAP,
      PROGRESS_CAP * (1 - Math.exp(-elapsed / TIME_CONSTANT)),
    )
    // 当耗时极长时给一点微小的补偿
    if (elapsed > 120) {
      progress.value = Math.min(PROGRESS_CAP, PROGRESS_CAP + (elapsed - 120) * 0.02)
    }
  }, 200)
}

/** API 返回后调用: 冲刺 100% 并延迟 0.5s */
async function finishProgress(): Promise<void> {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  progress.value = 100
  return new Promise((resolve) => setTimeout(resolve, 500))
}

/** 日期变化时自动计算天数 */
watch(
  () => [form.start_date, form.end_date],
  ([s, e]) => {
    if (s && e) {
      const ms = new Date(e as string).getTime() - new Date(s as string).getTime()
      const days = Math.round(ms / 86400000) + 1
      if (days > 0 && days <= 30) form.days = days
    }
  },
)

/** 切换偏好标签 */
function togglePreference(p: string) {
  const idx = form.preferences.indexOf(p)
  if (idx >= 0) {
    form.preferences.splice(idx, 1)
  } else {
    form.preferences.push(p)
  }
}

/** 提交表单 */
async function submit() {
  if (loading.value) return
  error.value = ''
  loading.value = true
  startProgress()

  try {
    const plan = await createTravelPlan({ ...form })
    await finishProgress()
    const id = addPlan(plan)
    router.push(`/result/${id}`)
  } catch (e: any) {
    // 出错时停止进度条
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    error.value = e.message || '规划失败，请稍后重试'
  } finally {
    loading.value = false
    progress.value = 0
  }
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px 80px;
}

/* ── Hero ───────────────────────────────────────────────── */
.hero {
  text-align: center;
  margin-bottom: 32px;
}
.hero-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
  letter-spacing: -0.02em;
}
.hero-sub {
  font-size: 1.05rem;
  color: var(--color-text-secondary);
}

/* ── Form ───────────────────────────────────────────────── */
.form {
  width: 100%;
  max-width: 640px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text);
}
.form-input {
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.95rem;
  transition: border-color .15s, box-shadow .15s;
  outline: none;
}
.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}
.form-input::placeholder {
  color: var(--color-text-muted);
}
.form-textarea {
  resize: vertical;
  min-height: 80px;
}

/* ── Row layout ──────────────────────────────────────────── */
.form-row {
  display: flex;
  gap: 16px;
}
.flex-1 {
  flex: 1;
}
.days-group {
  flex: 0 0 100px;
}

/* ── Preference tags ─────────────────────────────────────── */
.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  padding: 7px 16px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  transition: all .15s;
}
.tag:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.tag.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

/* ── Submit button (progress bar container) ───────────────── */
.btn-submit {
  position: relative;
  margin-top: 8px;
  padding: 14px;
  border: none;
  border-radius: var(--radius);
  background: var(--color-primary);
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  transition: background .3s;
}
.btn-submit:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.btn-submit:disabled {
  cursor: not-allowed;
}
/* 加载中背景变浅 */
.btn-submit.loading {
  background: #93b4f5;
}

/* 按钮文字始终在上层 */
.btn-text {
  position: relative;
  z-index: 1;
}

/* ── Progress bar ─────────────────────────────────────────── */
.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  transition: width .4s ease-out;
  z-index: 0;
  border-radius: var(--radius);
}

/* ── Error ────────────────────────────────────────────────── */
.error-msg {
  color: var(--color-error);
  font-size: .9rem;
  text-align: center;
}
</style>

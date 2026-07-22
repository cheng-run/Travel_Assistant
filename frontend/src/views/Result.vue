<template>
  <div v-if="plan" class="result">
    <!-- ── 顶部信息 ──────────────────────────────────── -->
    <header class="result-header">
      <div class="header-meta">
        <h1>{{ plan.city }}</h1>
        <p>{{ plan.start_date }} → {{ plan.end_date }} · 共 {{ plan.days.length }} 天</p>
      </div>
    </header>

    <div class="container">
      <!-- ── 每日行程 Tab ─────────────────────────────── -->
      <section class="section">
        <h2 class="section-title">每日行程</h2>
        <div class="tabs">
          <button
            v-for="(day, i) in plan.days"
            :key="i"
            class="tab"
            :class="{ active: activeDay === i }"
            @click="activeDay = i"
          >
            第 {{ i + 1 }} 天
            <small>{{ day.date }}</small>
          </button>
        </div>

        <!-- ── 当前日内容 ────────────────────────────── -->
        <div v-if="plan.days[activeDay]" class="day-content">
          <p class="day-desc">{{ plan.days[activeDay].description }}</p>

          <!-- 交通 & 住宿 -->
          <div class="meta-row">
            <div class="meta-item">
              <span class="meta-icon">🚗</span>
              <span>{{ plan.days[activeDay].transportation }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-icon">🛏️</span>
              <span>{{ plan.days[activeDay].accommodation }}</span>
            </div>
          </div>

          <!-- 景点卡片 -->
          <h3 v-if="plan.days[activeDay].attractions.length" class="sub-title">
            🏛️ 景点
          </h3>
          <div class="card-grid">
            <div
              v-for="attr in plan.days[activeDay].attractions"
              :key="attr.name"
              class="card attr-card"
            >
              <div class="attr-img-wrap">
                <img
                  :src="attrImages[attr.name] || PLACEHOLDER"
                  :alt="attr.name"
                  class="attr-img"
                  @error="onImgError"
                />
                <span v-if="loadingImages[attr.name]" class="img-loading">加载中...</span>
              </div>
              <div class="attr-body">
                <div class="attr-header">
                  <h4>{{ attr.name }}</h4>
                  <span v-if="attr.rating" class="attr-rating">⭐ {{ attr.rating }}</span>
                </div>
                <p class="attr-addr">{{ attr.address }}</p>
                <p class="attr-desc">{{ attr.description }}</p>
                <div class="attr-footer">
                  <span class="attr-meta">⏱️ {{ attr.visit_duration }}分钟</span>
                  <span v-if="attr.ticket_price > 0" class="attr-meta">
                    🎫 ¥{{ attr.ticket_price }}
                  </span>
                  <span v-else class="attr-meta free">🎫 免费</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 酒店 -->
          <div v-if="plan.days[activeDay].hotel" class="card hotel-card">
            <h3>🏨 {{ plan.days[activeDay].hotel!.name }}</h3>
            <div class="hotel-info">
              <span>{{ plan.days[activeDay].hotel!.address }}</span>
              <span>{{ plan.days[activeDay].hotel!.type }}</span>
              <span>评分 {{ plan.days[activeDay].hotel!.rating }}</span>
              <span class="hotel-price">¥{{ plan.days[activeDay].hotel!.estimated_cost }}/晚</span>
            </div>
          </div>

          <!-- 餐饮 -->
          <h3 v-if="plan.days[activeDay].meals.length" class="sub-title">🍽️ 餐饮</h3>
          <div class="meals">
            <div
              v-for="meal in plan.days[activeDay].meals"
              :key="meal.name + meal.type"
              class="meal-item"
            >
              <span class="meal-badge" :class="meal.type">{{
                MEAL_LABELS[meal.type]
              }}</span>
              <span class="meal-name">{{ meal.name }}</span>
              <span v-if="meal.estimated_cost" class="meal-cost">
                ¥{{ meal.estimated_cost }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- ── 天气预报 ─────────────────────────────────── -->
      <section v-if="plan.weather_info.length" class="section">
        <h2 class="section-title">🌤️ 天气预报</h2>
        <div class="weather-grid">
          <div
            v-for="w in plan.weather_info"
            :key="w.date"
            class="card weather-card"
          >
            <p class="weather-date">{{ w.date }}</p>
            <p class="weather-main">
              <span>白天 {{ w.day_weather }} {{ w.day_temp }}°C</span>
              <span>夜间 {{ w.night_weather }} {{ w.night_temp }}°C</span>
            </p>
            <p class="weather-wind">🌬️ {{ w.wind_direction }} {{ w.wind_power }}</p>
          </div>
        </div>
      </section>

      <!-- ── 预算 ─────────────────────────────────────── -->
      <section v-if="plan.budget" class="section">
        <h2 class="section-title">💰 预算概览</h2>
        <div class="card budget-card">
          <div class="budget-row">
            <span>景点门票</span>
            <span>¥{{ plan.budget.total_attractions }}</span>
          </div>
          <div class="budget-row">
            <span>酒店住宿</span>
            <span>¥{{ plan.budget.total_hotels }}</span>
          </div>
          <div class="budget-row">
            <span>餐饮费用</span>
            <span>¥{{ plan.budget.total_meals }}</span>
          </div>
          <div class="budget-row">
            <span>交通费用</span>
            <span>¥{{ plan.budget.total_transportation }}</span>
          </div>
          <div class="budget-row budget-total">
            <span>总费用</span>
            <span>¥{{ plan.budget.total }}</span>
          </div>
        </div>
      </section>

      <!-- ── 总体建议 ─────────────────────────────────── -->
      <section class="section">
        <h2 class="section-title">💡 旅行建议</h2>
        <div class="card suggestion-card">
          <p>{{ plan.overall_suggestions }}</p>
        </div>
      </section>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchAttractionImages } from '../services/api'
import { getPlan } from '../services/planStore'
import type { TripPlan } from '../types'

const PLACEHOLDER =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" fill="#e2e8f0"><rect width="400" height="300"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" font-size="14" fill="#94a3b8">暂无图片</text></svg>',
  )

const MEAL_LABELS: Record<string, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  dinner: '晚餐',
  snack: '小吃',
}

const route = useRoute()
const router = useRouter()

const id = Number(route.params.id)
const plan: TripPlan | null = getPlan(id)
if (!plan) router.replace({ name: 'Home' })

const activeDay = ref(0)

// 懒加载景点图片
const attrImages = reactive<Record<string, string>>({})
const loadingImages = reactive<Record<string, boolean>>({})

async function loadImages() {
  if (!plan) return
  for (const day of plan.days) {
    for (const attr of day.attractions) {
      if (attrImages[attr.name]) continue
      loadingImages[attr.name] = true
      try {
        const r = await searchAttractionImages(attr.name, 1)
        if (r.images.length > 0) {
          attrImages[attr.name] = r.images[0].urls.regular
        }
      } catch {
        // 图片加载失败静默忽略，显示占位图
      } finally {
        loadingImages[attr.name] = false
      }
    }
  }
}

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  img.src = PLACEHOLDER
}

onMounted(loadImages)
</script>

<style scoped>
.result {
  min-height: 100vh;
  padding-bottom: 80px;
}

/* ── Header ──────────────────────────────────────────────── */
.result-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255,255,255,.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--color-border);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 20px;
}
.header-meta h1 {
  font-size: 1.3rem;
  font-weight: 700;
}
.header-meta p {
  font-size: .85rem;
  color: var(--color-text-secondary);
}

/* ── Sections ───────────────────────────────────────────── */
.section {
  margin-top: 32px;
}
.section-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 16px;
}
.sub-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 20px 0 12px;
}

/* ── Tabs ───────────────────────────────────────────────── */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  overflow-x: auto;
}
.tab {
  flex: 1;
  min-width: 100px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: .9rem;
  text-align: center;
  transition: all .15s;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tab small {
  font-size: .75rem;
  color: var(--color-text-muted);
}
.tab.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.tab.active small {
  color: rgba(255,255,255,.7);
}

/* ── Day content ────────────────────────────────────────── */
.day-desc {
  font-size: .95rem;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
  line-height: 1.7;
}
.meta-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: .875rem;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
}
.meta-icon {
  font-size: 1rem;
}

/* ── Attraction cards ───────────────────────────────────── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.attr-card {
  overflow: hidden;
  padding: 0;
}
.attr-img-wrap {
  position: relative;
  width: 100%;
  height: 180px;
  background: var(--color-bg);
  overflow: hidden;
}
.attr-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.img-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: .8rem;
}
.attr-body {
  padding: 16px;
}
.attr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.attr-header h4 {
  font-size: 1rem;
  font-weight: 600;
}
.attr-rating {
  font-size: .85rem;
  color: var(--color-warning);
  font-weight: 600;
}
.attr-addr {
  font-size: .8rem;
  color: var(--color-text-muted);
  margin-bottom: 8px;
}
.attr-desc {
  font-size: .85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
}
.attr-footer {
  display: flex;
  gap: 12px;
}
.attr-meta {
  font-size: .8rem;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
}
.attr-meta.free {
  color: var(--color-success);
}

/* ── Hotel ──────────────────────────────────────────────── */
.hotel-card {
  margin-top: 16px;
}
.hotel-card h3 {
  margin-bottom: 8px;
  font-size: 1rem;
}
.hotel-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: .85rem;
  color: var(--color-text-secondary);
}
.hotel-price {
  font-weight: 700;
  color: var(--color-primary);
}

/* ── Meals ──────────────────────────────────────────────── */
.meals {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.meal-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}
.meal-badge {
  font-size: .75rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  color: #fff;
}
.meal-badge.breakfast { background: #f59e0b; }
.meal-badge.lunch { background: #16a34a; }
.meal-badge.dinner { background: #2563eb; }
.meal-badge.snack { background: #8b5cf6; }
.meal-name {
  flex: 1;
  font-size: .9rem;
}
.meal-cost {
  font-size: .85rem;
  color: var(--color-text-secondary);
  font-weight: 600;
}

/* ── Weather ────────────────────────────────────────────── */
.weather-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.weather-card {
  text-align: center;
  padding: 16px;
}
.weather-date {
  font-weight: 600;
  margin-bottom: 8px;
}
.weather-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: .85rem;
  color: var(--color-text-secondary);
}
.weather-wind {
  font-size: .8rem;
  color: var(--color-text-muted);
  margin-top: 8px;
}

/* ── Budget ─────────────────────────────────────────────── */
.budget-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.budget-row {
  display: flex;
  justify-content: space-between;
  font-size: .9rem;
  padding: 4px 0;
  border-bottom: 1px solid var(--color-bg);
}
.budget-row:last-child { border: none; }
.budget-total {
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--color-primary);
  padding-top: 8px;
  border-top: 2px solid var(--color-primary-light);
}

/* ── Suggestion ─────────────────────────────────────────── */
.suggestion-card p {
  font-size: .95rem;
  line-height: 1.8;
  color: var(--color-text-secondary);
}

</style>

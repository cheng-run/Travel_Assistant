<template>
  <aside class="sidebar">
    <h3 class="sidebar-title">📋 规划历史</h3>

    <!-- 空状态 -->
    <div v-if="plans.length === 0" class="empty">
      <span class="empty-icon">📭</span>
      <p>暂无规划记录</p>
    </div>

    <!-- 历史列表 -->
    <nav v-else class="history-list">
      <router-link
        v-for="(p, i) in plans"
        :key="i"
        :to="`/result/${i}`"
        class="history-item"
        :class="{ active: activeIndex === i }"
      >
        <span class="item-icon">🏙️</span>
        <div class="item-body">
          <span class="item-city">{{ p.city }}</span>
          <span class="item-date">{{ p.start_date }} → {{ p.end_date }}</span>
        </div>
      </router-link>
    </nav>

    <!-- 返回首页 -->
    <router-link to="/" class="btn-home" :class="{ active: $route.path === '/' }">
      ✨ 新建规划
    </router-link>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { getAllPlans } from '../services/planStore'

const route = useRoute()
const plans = computed(() => getAllPlans())
const activeIndex = computed(() => {
  if (route.name === 'Result') return Number(route.params.id)
  return -1
})
</script>

<style scoped>
.sidebar {
  width: 260px;
  min-width: 260px;
  height: 100vh;
  position: sticky;
  top: 0;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.sidebar-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

/* ── 空状态 ─────────────────────────────────────── */
.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  gap: 8px;
}
.empty-icon { font-size: 2rem; }

/* ── 历史列表 ───────────────────────────────────── */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--color-text);
  transition: background .12s;
}
.history-item:hover {
  background: var(--color-bg);
}
.history-item.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.item-icon { font-size: 1.2rem; flex-shrink: 0; }

.item-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.item-city {
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-date {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* ── 新建按钮 ───────────────────────────────────── */
.btn-home {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-light);
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
  margin-top: auto;
  transition: background .12s;
}
.btn-home:hover { background: #dbeafe; }
.btn-home.active {
  background: var(--color-primary);
  color: #fff;
}
</style>

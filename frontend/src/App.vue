<template>
  <div class="app-layout">
    <main class="main-content">
      <router-view />
    </main>
    <HistorySidebar />
  </div>
</template>

<script setup lang="ts">
import HistorySidebar from './components/HistorySidebar.vue'
</script>

<style>
/* ═══════════════════════════════════════════════════════════════════════
   全局样式 — CSS 变量驱动的现代简约主题
   ═══════════════════════════════════════════════════════════════════════ */

:root {
  /* 主色调 */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-light: #eff6ff;

  /* 中性色 */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #1e293b;
  --color-text-secondary: #64748b;
  --color-text-muted: #94a3b8;

  /* 语义色 */
  --color-success: #16a34a;
  --color-warning: #f59e0b;
  --color-error: #dc2626;

  /* 尺寸 */
  --radius-sm: 8px;
  --radius: 12px;
  --radius-lg: 16px;
  --shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md: 0 4px 6px rgba(0,0,0,.05), 0 2px 4px rgba(0,0,0,.04);
  --shadow-lg: 0 10px 15px rgba(0,0,0,.06), 0 4px 6px rgba(0,0,0,.04);

  /* 字体 */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
}

/* ── Reset ──────────────────────────────────────────────────────────── */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg);
  line-height: 1.6;
  min-height: 100vh;
}

a {
  color: var(--color-primary);
  text-decoration: none;
}

button {
  cursor: pointer;
  font-family: inherit;
}

input, select, textarea {
  font-family: inherit;
  font-size: inherit;
}

/* ── 布局 ────────────────────────────────────────────────────────────── */
.app-layout {
  display: flex;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  min-width: 0;  /* 防止 flex 子项溢出 */
}

/* ── 通用工具类 ────────────────────────────────────────────────────── */
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px;
}
</style>

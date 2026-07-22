import type { RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import Result from '../views/Result.vue'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/result/:id',
    name: 'Result',
    component: Result,
  },
]

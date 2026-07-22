/**
 * 规划历史存储 — 数组形式，支持多个规划结果的保存与检索。
 *
 * 每次提交成功后自动追加，所有历史结果在侧边栏中可见可点。
 */

import type { TripPlan } from '../types'

const plans: TripPlan[] = []

/** 追加一条规划结果，返回在数组中的索引 */
export function addPlan(plan: TripPlan): number {
  plans.push(plan)
  return plans.length - 1
}

/** 按索引获取规划结果 */
export function getPlan(index: number): TripPlan | null {
  return plans[index] ?? null
}

/** 获取全部历史规划 */
export function getAllPlans(): TripPlan[] {
  return plans
}

/** 清空全部历史 */
export function clearPlans(): void {
  plans.length = 0
}

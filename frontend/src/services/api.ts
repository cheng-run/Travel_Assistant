/**
 * API 调用层 — 封装所有后端请求
 *
 * Vite proxy 会把 /api/* 转发到 http://localhost:8000，
 * 所以这里直接用相对路径即可，无需写完整 URL。
 */

import type { TripPlan, TripPlanRequest, UnsplashSearchResult } from '../types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!resp.ok) {
    const detail = (await resp.json().catch(() => ({}))).detail || resp.statusText
    throw new Error(detail)
  }

  return resp.json()
}

/** 提交旅行需求，获取完整旅行计划 */
export async function createTravelPlan(req: TripPlanRequest): Promise<TripPlan> {
  return request<TripPlan>('/travel/plan', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

/** 根据景点名称搜索 Unsplash 图片 */
export async function searchAttractionImages(
  name: string,
  maxImages = 3,
): Promise<UnsplashSearchResult> {
  const params = new URLSearchParams({ max_images: String(maxImages) })
  return request<UnsplashSearchResult>(
    `/attractions/${encodeURIComponent(name)}/images?${params}`,
  )
}

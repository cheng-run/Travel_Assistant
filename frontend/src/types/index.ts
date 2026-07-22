/** 经纬度坐标 */
export interface Location {
  longitude: number
  latitude: number
}

/** 景点 */
export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  image_url?: string
  ticket_price: number
}

/** 餐饮 */
export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  address?: string
  location?: Location
  description?: string
  estimated_cost: number
}

/** 酒店 */
export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string
  rating: string
  distance: string
  type: string
  estimated_cost: number
}

/** 预算 */
export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total: number
}

/** 单日行程 */
export interface DayPlan {
  date: string
  day_index: number
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

/** 天气信息 */
export interface WeatherInfo {
  date: string
  day_weather: string
  night_weather: string
  day_temp: number
  night_temp: number
  wind_direction: string
  wind_power: string
}

/** 完整旅行计划 */
export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}

/** 旅行需求（发送给后端） */
export interface TripPlanRequest {
  city: string
  start_date: string
  end_date: string
  days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input?: string
}

/** Unsplash 图片 */
export interface UnsplashImage {
  image_id: string
  description?: string
  alt_description?: string
  width: number
  height: number
  urls: {
    raw: string
    full: string
    regular: string
    small: string
    thumb: string
  }
  photographer_name: string
  photographer_url: string
}

/** Unsplash 搜索结果 */
export interface UnsplashSearchResult {
  query: string
  total: number
  images: UnsplashImage[]
  has_results: boolean
}

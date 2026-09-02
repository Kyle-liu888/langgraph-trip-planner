<template>
  <div class="result-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <a-button class="back-button" size="large" @click="goBack">
        <ArrowLeftOutlined />
        返回首页
      </a-button>
      <a-space size="middle">
        <a-button v-if="!editMode" @click="toggleEditMode" type="default">
          <EditOutlined />
          编辑行程
        </a-button>
        <a-button v-else @click="saveChanges" type="primary">
          <SaveOutlined />
          保存修改
        </a-button>
        <a-button v-if="editMode" @click="cancelEdit" type="default">
          <CloseOutlined />
          取消编辑
        </a-button>

        <!-- 导出按钮 -->
        <a-dropdown v-if="!editMode">
          <template #overlay>
            <a-menu>
              <a-menu-item key="image" @click="exportAsImage">
                <PictureOutlined />
                导出为图片
              </a-menu-item>
              <a-menu-item key="pdf" @click="exportAsPDF">
                <FilePdfOutlined />
                导出为PDF
              </a-menu-item>
            </a-menu>
          </template>
          <a-button type="default">
            <DownloadOutlined />
            导出行程 <DownOutlined />
          </a-button>
        </a-dropdown>
      </a-space>
    </div>

    <div v-if="tripPlan" class="content-wrapper">
      <!-- 侧边导航 -->
      <div class="side-nav">
        <a-affix :offset-top="80">
          <a-menu mode="inline" :selected-keys="[activeSection]" @click="scrollToSection">
            <a-menu-item key="overview">
              <OrderedListOutlined />
              <span>行程概览</span>
            </a-menu-item>
            <a-menu-item key="budget" v-if="tripPlan.budget">
              <WalletOutlined />
              <span>预算明细</span>
            </a-menu-item>
            <a-menu-item key="map">
              <EnvironmentOutlined />
              <span>全程地图</span>
            </a-menu-item>
            <a-menu-item key="daily-maps">
              <EnvironmentOutlined />
              <span>每日地图</span>
            </a-menu-item>
            <a-sub-menu key="days" title="每日行程">
              <a-menu-item v-for="(day, index) in tripPlan.days" :key="`day-${index}`">
                第{{ day.day_index + 1 }}天
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item key="weather" v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0">
              <CloudOutlined />
              <span>天气信息</span>
            </a-menu-item>
          </a-menu>
        </a-affix>
      </div>

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 顶部信息区:左侧概览+预算,右侧地图 -->
        <div class="top-info-section">
          <!-- 左侧:行程概览和预算明细 -->
          <div class="left-info">
            <!-- 行程概览 -->
            <a-card id="overview" :title="`${tripPlan.city}旅行计划`" :bordered="false" class="overview-card">
              <div class="overview-content">
                <div class="info-item">
                  <span class="info-label">日期</span>
                  <span class="info-value">{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">整体建议</span>
                  <span class="info-value">{{ tripPlan.overall_suggestions }}</span>
                </div>
              </div>
            </a-card>

            <!-- 预算明细 -->
            <a-card id="budget" v-if="tripPlan.budget" title="预算明细" :bordered="false" class="budget-card">
              <div class="budget-grid">
                <div class="budget-item">
                  <div class="budget-label">景点门票</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_attractions }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-label">酒店住宿</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_hotels }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-label">餐饮费用</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_meals }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-label">交通费用</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_transportation }}</div>
                </div>
              </div>
              <div class="budget-total">
                <span class="total-label">预估总费用</span>
                <span class="total-value">¥{{ tripPlan.budget.total }}</span>
              </div>
            </a-card>
          </div>

          <!-- 右侧:地图 -->
          <div class="right-map">
            <a-card id="map" title="全程地图" :bordered="false" class="map-card">
              <div class="map-shell">
                <div id="amap-container" class="amap-container"></div>
                <div class="map-legend">
                  <span><i class="legend-dot legend-hotel"></i>住宿</span>
                  <span><i class="legend-dot legend-attraction"></i>景点</span>
                  <span><i class="legend-dot legend-meal"></i>餐饮</span>
                </div>
              </div>
            </a-card>
          </div>
        </div>

        <!-- 每日地图 -->
        <a-card id="daily-maps" title="每日地图" :bordered="false" class="daily-maps-card">
          <div class="daily-map-grid">
            <div
              v-for="(day, index) in tripPlan.days"
              :key="`daily-map-${index}`"
              class="daily-map-panel"
            >
              <div class="daily-map-heading">
                <div>
                  <div class="daily-map-title">第{{ day.day_index + 1 }}天</div>
                  <div class="daily-map-date">{{ day.date }}</div>
                </div>
                <div class="daily-map-count">
                  {{ getDayMapPoints(index).length }} 个地点
                </div>
              </div>
              <div class="map-shell daily-map-shell">
                <div
                  :id="getDailyMapContainerId(index)"
                  class="amap-container daily-amap-container"
                ></div>
                <div class="map-legend compact">
                  <span><i class="legend-dot legend-hotel"></i>住宿</span>
                  <span><i class="legend-dot legend-attraction"></i>景点</span>
                  <span><i class="legend-dot legend-meal"></i>餐饮</span>
                </div>
                <div v-if="!hasDailyMapLocations(index)" class="map-empty-state">
                  暂无可展示坐标
                </div>
              </div>
            </div>
          </div>
        </a-card>

        <!-- 每日行程:可折叠 -->
        <a-card title="每日行程" :bordered="false" class="days-card">
          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :id="`day-${index}`"
            >
              <template #header>
                <div class="day-header">
                  <span class="day-title">第{{ day.day_index + 1 }}天</span>
                  <span class="day-date">{{ day.date }}</span>
                </div>
              </template>

              <!-- 行程基本信息 -->
              <div class="day-info">
                <div class="info-row">
                  <span class="label">行程描述</span>
                  <span class="value">{{ day.description }}</span>
                </div>
                <div class="info-row">
                  <span class="label">交通方式</span>
                  <span class="value">{{ day.transportation }}</span>
                </div>
                <div class="info-row">
                  <span class="label">住宿</span>
                  <span class="value">{{ day.accommodation }}</span>
                </div>
              </div>

              <!-- 景点安排 -->
              <a-divider orientation="left">景点安排</a-divider>
              <a-list
                :data-source="day.attractions"
                :grid="{ gutter: 16, column: 2 }"
              >
                <template #renderItem="{ item, index }">
                  <a-list-item>
                    <a-card :title="item.name" size="small" class="attraction-card">
                      <!-- 编辑模式下的操作按钮 -->
                      <template #extra v-if="editMode">
                        <a-space>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'up')"
                            :disabled="index === 0"
                          >
                            ↑
                          </a-button>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'down')"
                            :disabled="index === day.attractions.length - 1"
                          >
                            ↓
                          </a-button>
                          <a-button
                            size="small"
                            danger
                            @click="deleteAttraction(day.day_index, index)"
                          >
                            🗑️
                          </a-button>
                        </a-space>
                      </template>

                      <!-- 景点图片 -->
                      <div class="attraction-image-wrapper">
                        <img
                          :src="getAttractionImage(item.name, index)"
                          :alt="item.name"
                          class="attraction-image"
                          @error="handleImageError"
                        />
                        <div class="attraction-badge">
                          <span class="badge-number">{{ index + 1 }}</span>
                        </div>
                        <div v-if="item.ticket_price" class="price-tag">
                          ¥{{ item.ticket_price }}
                        </div>
                      </div>

                      <!-- 编辑模式下可编辑的字段 -->
                      <div v-if="editMode">
                        <p><strong>地址:</strong></p>
                        <a-input v-model:value="item.address" size="small" style="margin-bottom: 8px" />

                        <p><strong>游览时长(分钟):</strong></p>
                        <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width: 100%; margin-bottom: 8px" />

                        <p><strong>描述:</strong></p>
                        <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom: 8px" />
                      </div>

                      <!-- 查看模式 -->
                      <div v-else>
                        <p><strong>地址:</strong> {{ item.address }}</p>
                        <p><strong>游览时长:</strong> {{ item.visit_duration }}分钟</p>
                        <p><strong>描述:</strong> {{ item.description }}</p>
                        <p v-if="item.rating"><strong>评分:</strong> {{ item.rating }}⭐</p>
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <!-- 酒店推荐 -->
              <a-divider v-if="day.hotel" orientation="left">住宿推荐</a-divider>
              <a-card v-if="day.hotel" size="small" class="hotel-card">
                <template #title>
                  <span class="hotel-title">{{ day.hotel.name }}</span>
                </template>
                <a-descriptions :column="2" size="small">
                  <a-descriptions-item label="地址">{{ day.hotel.address }}</a-descriptions-item>
                  <a-descriptions-item label="类型">{{ day.hotel.type }}</a-descriptions-item>
                  <a-descriptions-item label="价格范围">{{ day.hotel.price_range }}</a-descriptions-item>
                  <a-descriptions-item label="评分">{{ day.hotel.rating }}⭐</a-descriptions-item>
                  <a-descriptions-item label="距离" :span="2">{{ day.hotel.distance }}</a-descriptions-item>
                </a-descriptions>
              </a-card>

              <!-- 餐饮安排 -->
              <a-divider orientation="left">餐饮安排</a-divider>
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item
                  v-for="meal in day.meals"
                  :key="meal.type"
                  :label="getMealLabel(meal.type)"
                >
                  {{ meal.name }}
                  <span v-if="meal.description"> - {{ meal.description }}</span>
                </a-descriptions-item>
              </a-descriptions>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <a-card id="weather" v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0" title="天气信息" style="margin-top: 20px" :bordered="false">
        <a-list
          :data-source="tripPlan.weather_info"
          :grid="{ gutter: 16, column: 3 }"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-card size="small" class="weather-card" :class="getWeatherCardClass(item.day_weather, item.night_weather)">
                <div class="weather-date">{{ item.date }}</div>
                <div class="weather-info-row">
                  <span class="weather-icon">{{ getWeatherIcon(item.day_weather, 'day') }}</span>
                  <div>
                    <div class="weather-label">白天</div>
                    <div class="weather-value">{{ item.day_weather }} {{ item.day_temp }}°C</div>
                  </div>
                </div>
                <div class="weather-info-row">
                  <span class="weather-icon">{{ getWeatherIcon(item.night_weather, 'night') }}</span>
                  <div>
                    <div class="weather-label">夜间</div>
                    <div class="weather-value">{{ item.night_weather }} {{ item.night_temp }}°C</div>
                  </div>
                </div>
                <div class="weather-wind">
                  💨 {{ item.wind_direction }} {{ item.wind_power }}
                </div>
              </a-card>
            </a-list-item>
          </template>
        </a-list>
        </a-card>
      </div>
    </div>

    <a-empty v-else description="没有找到旅行计划数据">
      <template #image>
        <div style="font-size: 80px;">🗺️</div>
      </template>
      <template #description>
        <span style="color: #999;">暂无旅行计划数据,请先创建行程</span>
      </template>
      <a-button type="primary" @click="goBack">返回首页创建行程</a-button>
    </a-empty>

    <!-- 回到顶部按钮 -->
    <a-back-top :visibility-height="300">
      <div class="back-top-button">
        ↑
      </div>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  CloseOutlined,
  CloudOutlined,
  DownloadOutlined,
  DownOutlined,
  EditOutlined,
  EnvironmentOutlined,
  FilePdfOutlined,
  OrderedListOutlined,
  PictureOutlined,
  SaveOutlined,
  WalletOutlined
} from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import type { TripPlan } from '@/types'
import { API_BASE_URL } from '@/services/api'

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0]) // 默认展开第一天
let map: any = null
let AMapApi: any = null
const dailyMaps = new Map<number, any>()

type MapPointType = 'hotel' | 'attraction' | 'meal'

interface MapPoint {
  type: MapPointType
  name: string
  address?: string
  description?: string
  location: {
    longitude: number
    latitude: number
  }
  dayIndex: number
  markerText: string
  order: number
  routeOrder: number
  meta?: string
}

onMounted(async () => {
  const data = sessionStorage.getItem('tripPlan')
  if (data) {
    tripPlan.value = JSON.parse(data)
    // 加载景点图片
    await loadAttractionPhotos()
    // 回填缺失的餐饮坐标,旧session里的结果也尽量能显示餐厅点位
    await loadMissingMealLocations()
    // 等待DOM渲染完成后初始化地图
    await nextTick()
    initMaps()
  }
})

onUnmounted(() => {
  destroyMaps()
})

const goBack = () => {
  router.push('/')
}

// 滚动到指定区域
const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key

  if (key.startsWith('day-')) {
    const dayIndex = Number(key.replace('day-', ''))
    if (Number.isInteger(dayIndex)) {
      activeDays.value = [dayIndex]
    }
  }

  const element = document.getElementById(key)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 切换编辑模式
const toggleEditMode = () => {
  editMode.value = true
  // 保存原始数据用于取消编辑
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info('进入编辑模式')
}

// 保存修改
const saveChanges = () => {
  editMode.value = false
  // 更新sessionStorage
  if (tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  }
  message.success('修改已保存')

  // 重新初始化地图以反映更改
  destroyMaps()
  nextTick(() => {
    initMaps()
  })
}

// 取消编辑
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  }
  editMode.value = false
  message.info('已取消编辑')

  destroyMaps()
  nextTick(() => {
    initMaps()
  })
}

// 删除景点
const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning('每天至少需要保留一个景点')
    return
  }

  day.attractions.splice(attrIndex, 1)
  message.success('景点已删除')
}

// 移动景点顺序
const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  const attractions = day.attractions

  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

const normalizeWeatherText = (weather: unknown): string => String(weather || '').trim()

const getWeatherIcon = (weather: unknown, period: 'day' | 'night'): string => {
  const text = normalizeWeatherText(weather)
  if (!text || text.includes('未知') || text.includes('暂无')) return '—'
  if (text.includes('雷')) return '⛈️'
  if (text.includes('暴雨') || text.includes('大雨')) return '🌧️'
  if (text.includes('雨')) return '🌦️'
  if (text.includes('雪')) return '❄️'
  if (text.includes('冰雹')) return '🌨️'
  if (text.includes('雾') || text.includes('霾')) return '🌫️'
  if (text.includes('沙') || text.includes('尘')) return '🌪️'
  if (text.includes('阴')) return '☁️'
  if (text.includes('云')) return period === 'night' ? '☁️' : '⛅'
  if (text.includes('晴')) return period === 'night' ? '🌙' : '☀️'
  return period === 'night' ? '🌙' : '🌤️'
}

const getWeatherCardClass = (dayWeather: unknown, nightWeather: unknown): string => {
  const text = `${normalizeWeatherText(dayWeather)} ${normalizeWeatherText(nightWeather)}`
  if (!text.trim() || text.includes('未知') || text.includes('暂无')) return 'weather-card-unknown'
  if (text.includes('雨') || text.includes('雷')) return 'weather-card-rain'
  if (text.includes('雪')) return 'weather-card-snow'
  if (text.includes('雾') || text.includes('霾') || text.includes('沙') || text.includes('尘')) return 'weather-card-haze'
  if (text.includes('阴') || text.includes('云')) return 'weather-card-cloud'
  return 'weather-card-sun'
}

// 加载所有景点图片
const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return

  const promises: Promise<void>[] = []

  tripPlan.value.days.forEach(day => {
    day.attractions.forEach(attraction => {
      const promise = fetch(`${API_BASE_URL}/api/poi/photo?name=${encodeURIComponent(attraction.name)}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data.photo_url) {
            attractionPhotos.value[attraction.name] = data.data.photo_url
          }
        })
        .catch(err => {
          console.error(`获取${attraction.name}图片失败:`, err)
        })

      promises.push(promise)
    })
  })

  await Promise.all(promises)
}

const isLodgingBreakfastMeal = (type: string, name: string): boolean => {
  if (type !== 'breakfast') return false
  return ['酒店早餐', '民宿早餐', '客栈早餐', '住宿早餐'].some(keyword => name.includes(keyword))
}

const loadMissingMealLocations = async () => {
  if (!tripPlan.value) return

  let updatedCount = 0
  const promises: Promise<void>[] = []

  tripPlan.value.days.forEach(day => {
    day.meals.forEach(meal => {
      if (isValidLocation(meal.location) || isLodgingBreakfastMeal(meal.type, meal.name)) {
        return
      }

      const promise = fetch(
        `${API_BASE_URL}/api/poi/search?keywords=${encodeURIComponent(meal.name)}&city=${encodeURIComponent(tripPlan.value!.city)}&source_role=food`
      )
        .then(res => res.json())
        .then(data => {
          const poi = Array.isArray(data.data)
            ? data.data.find((item: any) => isValidLocation(item.location))
            : null

          if (!poi) return

          if (!meal.address && poi.address) {
            meal.address = poi.address
          }

          meal.location = normalizeLocation(poi.location)
          updatedCount += 1
        })
        .catch(err => {
          console.warn(`餐饮坐标回填失败: ${meal.name}`, err)
        })

      promises.push(promise)
    })
  })

  await Promise.all(promises)

  if (updatedCount > 0 && tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  }
}

// 获取景点图片
const getAttractionImage = (name: string, index: number): string => {
  // 如果已加载真实图片,返回真实图片
  if (attractionPhotos.value[name]) {
    return attractionPhotos.value[name]
  }

  // 返回一个纯色占位图(避免跨域问题)
  const colors = [
    { start: '#1677ff', end: '#69b1ff' },
    { start: '#0f766e', end: '#5eead4' },
    { start: '#475569', end: '#94a3b8' },
    { start: '#2563eb', end: '#93c5fd' },
    { start: '#334155', end: '#cbd5e1' }
  ]
  const colorIndex = index % colors.length
  const { start, end } = colors[colorIndex]

  // 使用base64编码避免中文问题
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
    <defs>
      <linearGradient id="grad${index}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${start};stop-opacity:1" />
        <stop offset="100%" style="stop-color:${end};stop-opacity:1" />
      </linearGradient>
    </defs>
    <rect width="400" height="300" fill="url(#grad${index})"/>
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="24" font-weight="bold" fill="white">${name}</text>
  </svg>`

  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

// 图片加载失败时的处理
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  // 使用灰色占位图
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18" fill="%23999"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}

const replaceMapSnapshots = (exportContainer: HTMLElement) => {
  const mapContainers = document.querySelectorAll<HTMLElement>('#amap-container, .daily-amap-container')

  mapContainers.forEach(container => {
    const mapCanvas = container.querySelector('canvas') as HTMLCanvasElement | null
    if (!mapCanvas || !container.id) return

    try {
      const mapSnapshot = mapCanvas.toDataURL('image/png')
      const exportMapContainer = exportContainer.querySelector<HTMLElement>(`#${container.id}`)
      if (exportMapContainer) {
        exportMapContainer.innerHTML = `<img src="${mapSnapshot}" style="width:100%;height:100%;object-fit:cover;" />`
      }
    } catch (err) {
      console.warn(`地图截图失败: ${container.id}`, err)
    }
  })
}

// 导出为图片
const exportAsImage = async () => {
  try {
    message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    // 创建一个独立的容器
    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f5f7fa'
    exportContainer.style.padding = '20px'

    // 复制所有内容
    exportContainer.innerHTML = element.innerHTML

    // 处理地图截图
    replaceMapSnapshots(exportContainer)

    // 移除所有ant-card类,替换为纯div
    const cards = exportContainer.querySelectorAll('.ant-card')
    cards.forEach((card) => {
      const cardEl = card as HTMLElement
      try {
        cardEl.className = '' // 移除所有类
        cardEl.style.setProperty('background-color', '#ffffff')
        cardEl.style.setProperty('border-radius', '8px')
        cardEl.style.setProperty('box-shadow', '0 10px 24px rgba(15, 23, 42, 0.08)')
        cardEl.style.setProperty('margin-bottom', '20px')
        cardEl.style.setProperty('overflow', 'hidden')
      } catch (err) {
        console.error('设置卡片样式失败:', err)
      }
    })

    // 处理卡片头部
    const cardHeads = exportContainer.querySelectorAll('.ant-card-head')
    cardHeads.forEach((head) => {
      const headEl = head as HTMLElement
      try {
        headEl.style.setProperty('background-color', '#ffffff')
        headEl.style.setProperty('color', '#0f172a')
        headEl.style.setProperty('padding', '16px 24px')
        headEl.style.setProperty('font-size', '18px')
        headEl.style.setProperty('font-weight', '600')
      } catch (err) {
        console.error('设置卡片头部样式失败:', err)
      }
    })

    // 处理卡片内容
    const cardBodies = exportContainer.querySelectorAll('.ant-card-body')
    cardBodies.forEach((body) => {
      const bodyEl = body as HTMLElement
      bodyEl.style.setProperty('background-color', '#ffffff')
      bodyEl.style.setProperty('padding', '24px')
    })

    // 处理酒店卡片头部
    const hotelCards = exportContainer.querySelectorAll('.hotel-card')
    hotelCards.forEach((card) => {
      const head = card.querySelector('.ant-card-head') as HTMLElement
      if (head) {
        head.style.setProperty('background-color', '#f8fafc')
      }
      (card as HTMLElement).style.setProperty('background-color', '#ffffff')
    })

    // 处理天气卡片
    const weatherCards = exportContainer.querySelectorAll('.weather-card')
    weatherCards.forEach((card) => {
      (card as HTMLElement).style.setProperty('background-color', '#f8fafc')
    })

    // 处理预算总计
    const budgetTotal = exportContainer.querySelector('.budget-total')
    if (budgetTotal) {
      const el = budgetTotal as HTMLElement
      el.style.setProperty('background-color', '#1677ff')
      el.style.setProperty('color', '#ffffff')
      el.style.setProperty('padding', '20px')
      el.style.setProperty('border-radius', '8px')
      el.style.setProperty('margin-bottom', '20px')
    }

    // 处理预算项
    const budgetItems = exportContainer.querySelectorAll('.budget-item')
    budgetItems.forEach((item) => {
      const el = item as HTMLElement
      el.style.setProperty('background-color', '#f5f7fa')
      el.style.setProperty('padding', '16px')
      el.style.setProperty('border-radius', '8px')
      el.style.setProperty('margin-bottom', '12px')
    })

    // 添加到body(隐藏)
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f5f7fa',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    // 移除容器
    document.body.removeChild(exportContainer)

    // 转换为图片并下载
    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.value?.city}_${new Date().getTime()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()

    message.success({ content: '图片导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出图片失败:', error)
    message.error({ content: `导出图片失败: ${error.message}`, key: 'export' })
  }
}

// 导出为PDF
const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    // 创建一个独立的容器
    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f5f7fa'
    exportContainer.style.padding = '20px'

    // 复制所有内容
    exportContainer.innerHTML = element.innerHTML

    // 处理地图截图
    replaceMapSnapshots(exportContainer)

    // 移除所有ant-card类,替换为纯div
    const cards = exportContainer.querySelectorAll('.ant-card')
    cards.forEach((card) => {
      const cardEl = card as HTMLElement
      try {
        cardEl.className = ''
        cardEl.style.setProperty('background-color', '#ffffff')
        cardEl.style.setProperty('border-radius', '12px')
        cardEl.style.setProperty('box-shadow', '0 4px 12px rgba(0, 0, 0, 0.1)')
        cardEl.style.setProperty('margin-bottom', '20px')
        cardEl.style.setProperty('overflow', 'hidden')
      } catch (err) {
        console.error('设置卡片样式失败:', err)
      }
    })

    // 处理卡片头部
    const cardHeads = exportContainer.querySelectorAll('.ant-card-head')
    cardHeads.forEach((head) => {
      const headEl = head as HTMLElement
      try {
        headEl.style.setProperty('background-color', '#ffffff')
        headEl.style.setProperty('color', '#0f172a')
        headEl.style.setProperty('padding', '16px 24px')
        headEl.style.setProperty('font-size', '18px')
        headEl.style.setProperty('font-weight', '600')
      } catch (err) {
        console.error('设置卡片头部样式失败:', err)
      }
    })

    // 处理卡片内容
    const cardBodies = exportContainer.querySelectorAll('.ant-card-body')
    cardBodies.forEach((body) => {
      const bodyEl = body as HTMLElement
      bodyEl.style.setProperty('background-color', '#ffffff')
      bodyEl.style.setProperty('padding', '24px')
    })

    // 处理酒店卡片头部
    const hotelCards = exportContainer.querySelectorAll('.hotel-card')
    hotelCards.forEach((card) => {
      const head = card.querySelector('.ant-card-head') as HTMLElement
      if (head) {
        head.style.setProperty('background-color', '#f8fafc')
      }
      (card as HTMLElement).style.setProperty('background-color', '#ffffff')
    })

    // 处理天气卡片
    const weatherCards = exportContainer.querySelectorAll('.weather-card')
    weatherCards.forEach((card) => {
      (card as HTMLElement).style.setProperty('background-color', '#f8fafc')
    })

    // 处理预算总计
    const budgetTotal = exportContainer.querySelector('.budget-total')
    if (budgetTotal) {
      const el = budgetTotal as HTMLElement
      el.style.setProperty('background-color', '#1677ff')
      el.style.setProperty('color', '#ffffff')
      el.style.setProperty('padding', '20px')
      el.style.setProperty('border-radius', '8px')
      el.style.setProperty('margin-bottom', '20px')
    }

    // 处理预算项
    const budgetItems = exportContainer.querySelectorAll('.budget-item')
    budgetItems.forEach((item) => {
      const el = item as HTMLElement
      el.style.setProperty('background-color', '#f5f7fa')
      el.style.setProperty('padding', '16px')
      el.style.setProperty('border-radius', '8px')
      el.style.setProperty('margin-bottom', '12px')
    })

    // 添加到body(隐藏)
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f5f7fa',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    // 移除容器
    document.body.removeChild(exportContainer)

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    const imgWidth = 210 // A4宽度(mm)
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    // 如果内容高度超过一页,分页处理
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297 // A4高度

    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }

    pdf.save(`旅行计划_${tripPlan.value?.city}_${new Date().getTime()}.pdf`)

    message.success({ content: 'PDF导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    message.error({ content: `导出PDF失败: ${error.message}`, key: 'export' })
  }
}

const DEFAULT_MAP_CENTER = [116.397128, 39.916527]
const pointColors: Record<MapPointType, string> = {
  hotel: '#ef4444',
  attraction: '#1677ff',
  meal: '#f59e0b'
}
const dayRouteColors = ['#1677ff', '#16a34a', '#f59e0b', '#8b5cf6', '#ef4444', '#0f766e']

const getDailyMapContainerId = (dayIndex: number): string => `daily-amap-container-${dayIndex}`

const escapeHtml = (value: unknown): string => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const isValidLocation = (location: any): boolean => {
  if (!location) return false
  const longitude = Number(location.longitude)
  const latitude = Number(location.latitude)
  return Number.isFinite(longitude) && Number.isFinite(latitude)
}

const normalizeLocation = (location: any) => ({
  longitude: Number(location.longitude),
  latitude: Number(location.latitude)
})

const getMealMarkerText = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早',
    lunch: '午',
    dinner: '晚',
    snack: '食'
  }
  return labels[type] || '餐'
}

const getMealRouteRank = (type: string): number => {
  const ranks: Record<string, number> = {
    breakfast: 10,
    lunch: 40,
    snack: 70,
    dinner: 90
  }
  return ranks[type] || 80
}

const getDisplayHotelForDay = (dayIndex: number) => {
  const days = tripPlan.value?.days || []
  const currentHotel = days[dayIndex]?.hotel
  if (currentHotel) {
    return {
      hotel: currentHotel,
      isCarriedOver: false
    }
  }

  for (let index = dayIndex - 1; index >= 0; index -= 1) {
    const previousHotel = days[index]?.hotel
    if (previousHotel) {
      return {
        hotel: previousHotel,
        isCarriedOver: true
      }
    }
  }

  const firstHotel = days.find(day => day.hotel)?.hotel
  return firstHotel
    ? {
        hotel: firstHotel,
        isCarriedOver: true
      }
    : null
}

const getDayMapPoints = (dayIndex: number): MapPoint[] => {
  const day = tripPlan.value?.days[dayIndex]
  if (!day) return []

  const points: MapPoint[] = []
  const displayHotel = getDisplayHotelForDay(dayIndex)

  if (displayHotel?.hotel && isValidLocation(displayHotel.hotel.location)) {
    const hotel = displayHotel.hotel
    points.push({
      type: 'hotel',
      name: hotel.name,
      address: hotel.address,
      description: displayHotel.isCarriedOver ? '沿用前一晚住处，方便当天出发或取行李' : hotel.distance,
      location: normalizeLocation(hotel.location),
      dayIndex,
      markerText: '住',
      order: 0,
      routeOrder: 0,
      meta: `${hotel.type || day.accommodation}${hotel.price_range ? ` | ${hotel.price_range}` : ''}`
    })
  }

  day.attractions.forEach((attraction, attrIndex) => {
    if (!isValidLocation(attraction.location)) return

    points.push({
      type: 'attraction',
      name: attraction.name,
      address: attraction.address,
      description: attraction.description,
      location: normalizeLocation(attraction.location),
      dayIndex,
      markerText: `景${attrIndex + 1}`,
      order: 100 + attrIndex,
      routeOrder: 20 + attrIndex * 20,
      meta: attraction.visit_duration ? `游览 ${attraction.visit_duration} 分钟` : undefined
    })
  })

  day.meals.forEach((meal, mealIndex) => {
    if (!isValidLocation(meal.location)) return

    points.push({
      type: 'meal',
      name: meal.name,
      address: meal.address,
      description: meal.description,
      location: normalizeLocation(meal.location),
      dayIndex,
      markerText: getMealMarkerText(meal.type),
      order: 200 + getMealRouteRank(meal.type) + mealIndex,
      routeOrder: getMealRouteRank(meal.type),
      meta: meal.estimated_cost ? `${getMealLabel(meal.type)} | 约 ¥${meal.estimated_cost}/人` : getMealLabel(meal.type)
    })
  })

  return points.sort((a, b) => a.order - b.order)
}

const hasDailyMapLocations = (dayIndex: number): boolean => getDayMapPoints(dayIndex).length > 0

const getDailyRoutePoints = (dayIndex: number): MapPoint[] => {
  const points = getDayMapPoints(dayIndex)
  const hotelPoint = points.find(point => point.type === 'hotel')
  const attractionPoints = points
    .filter(point => point.type === 'attraction')
    .sort((a, b) => a.routeOrder - b.routeOrder)
  const mealPoints = (type: string) => points
    .filter(point => point.type === 'meal' && point.markerText === getMealMarkerText(type))
    .sort((a, b) => a.routeOrder - b.routeOrder)

  const route: MapPoint[] = []
  if (hotelPoint) route.push(hotelPoint)
  route.push(...mealPoints('breakfast'))
  if (attractionPoints[0]) route.push(attractionPoints[0])
  route.push(...mealPoints('lunch'))
  route.push(...attractionPoints.slice(1))
  route.push(...mealPoints('snack'))
  route.push(...mealPoints('dinner'))
  if (hotelPoint && route.length > 1) route.push(hotelPoint)

  return route
}

const getPointTypeLabel = (type: MapPointType): string => {
  const labels: Record<MapPointType, string> = {
    hotel: '住宿',
    attraction: '景点',
    meal: '餐饮'
  }
  return labels[type]
}

const buildInfoWindowContent = (point: MapPoint): string => {
  const detailRows = [
    point.address ? `<p style="margin:4px 0;"><strong>地址:</strong> ${escapeHtml(point.address)}</p>` : '',
    point.meta ? `<p style="margin:4px 0;"><strong>信息:</strong> ${escapeHtml(point.meta)}</p>` : '',
    point.description ? `<p style="margin:4px 0;"><strong>说明:</strong> ${escapeHtml(point.description)}</p>` : ''
  ].join('')

  return `
    <div style="padding:10px;max-width:260px;">
      <div style="margin:0 0 8px;color:${pointColors[point.type]};font-weight:700;">第${point.dayIndex + 1}天 · ${getPointTypeLabel(point.type)}</div>
      <h4 style="margin:0 0 8px 0;color:#0f172a;">${escapeHtml(point.name)}</h4>
      ${detailRows}
    </div>
  `
}

const createMarkerLabelHtml = (point: MapPoint, prefix = ''): string => `
  <div style="background:${pointColors[point.type]};color:#fff;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(15,23,42,.18);white-space:nowrap;">
    ${escapeHtml(`${prefix}${point.markerText}`)}
  </div>
`

const createMarker = (AMap: any, targetMap: any, point: MapPoint, prefix = '') => {
  const marker = new AMap.Marker({
    position: [point.location.longitude, point.location.latitude],
    title: point.name,
    label: {
      content: createMarkerLabelHtml(point, prefix),
      offset: new AMap.Pixel(0, -30)
    }
  })

  const infoWindow = new AMap.InfoWindow({
    content: buildInfoWindowContent(point),
    offset: new AMap.Pixel(0, -30)
  })

  marker.on('click', () => {
    infoWindow.open(targetMap, marker.getPosition())
  })

  return marker
}

const drawRoute = (AMap: any, targetMap: any, routePoints: MapPoint[], color: string) => {
  if (routePoints.length < 2) return

  const path = routePoints.map(point => [
    point.location.longitude,
    point.location.latitude
  ])

  const polyline = new AMap.Polyline({
    path,
    strokeColor: color,
    strokeWeight: 4,
    strokeOpacity: 0.82,
    strokeStyle: 'solid',
    showDir: true
  })

  targetMap.add(polyline)
}

const fitMapToMarkers = (targetMap: any, markers: any[]) => {
  if (markers.length > 1) {
    targetMap.setFitView(markers)
  } else if (markers.length === 1) {
    const position = markers[0].getPosition()
    targetMap.setZoomAndCenter(13, position)
  }
}

const renderDayLayer = (AMap: any, targetMap: any, dayIndex: number, labelPrefix = '') => {
  const points = getDayMapPoints(dayIndex)
  const markers = points.map(point => createMarker(AMap, targetMap, point, labelPrefix))

  if (markers.length) {
    targetMap.add(markers)
  }

  drawRoute(
    AMap,
    targetMap,
    getDailyRoutePoints(dayIndex),
    dayRouteColors[dayIndex % dayRouteColors.length]
  )

  fitMapToMarkers(targetMap, markers)
  return markers
}

const initOverviewMap = (AMap: any) => {
  const container = document.getElementById('amap-container')
  if (!container || !tripPlan.value) return

  map = new AMap.Map('amap-container', {
    zoom: 12,
    center: DEFAULT_MAP_CENTER,
    viewMode: '3D'
  })

  const allMarkers: any[] = []

  tripPlan.value.days.forEach((_, dayIndex) => {
    const markers = getDayMapPoints(dayIndex).map(point =>
      createMarker(AMap, map, point, `D${dayIndex + 1}`)
    )

    if (markers.length) {
      map.add(markers)
      allMarkers.push(...markers)
    }

    drawRoute(
      AMap,
      map,
      getDailyRoutePoints(dayIndex),
      dayRouteColors[dayIndex % dayRouteColors.length]
    )
  })

  fitMapToMarkers(map, allMarkers)
}

const initDailyMap = (AMap: any, dayIndex: number) => {
  const containerId = getDailyMapContainerId(dayIndex)
  const container = document.getElementById(containerId)
  if (!container) return

  const existingMap = dailyMaps.get(dayIndex)
  if (existingMap) {
    existingMap.destroy()
  }

  const dailyMap = new AMap.Map(containerId, {
    zoom: 12,
    center: DEFAULT_MAP_CENTER,
    viewMode: '3D'
  })
  dailyMaps.set(dayIndex, dailyMap)
  renderDayLayer(AMap, dailyMap, dayIndex)
}

const initDailyMaps = (AMap: any) => {
  if (!tripPlan.value) return

  tripPlan.value.days.forEach((_, dayIndex) => {
    initDailyMap(AMap, dayIndex)
  })
}

const loadAMap = async () => {
  if (AMapApi) return AMapApi

  AMapApi = await AMapLoader.load({
    key: import.meta.env.VITE_AMAP_WEB_JS_KEY,
    version: '2.0',
    plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
  })

  return AMapApi
}

const initMaps = async () => {
  try {
    const AMap = await loadAMap()
    initOverviewMap(AMap)
    initDailyMaps(AMap)
    message.success('地图加载成功')
  } catch (error) {
    console.error('地图加载失败:', error)
    message.error('地图加载失败')
  }
}

const destroyMaps = () => {
  if (map) {
    map.destroy()
    map = null
  }

  dailyMaps.forEach(dailyMap => {
    dailyMap.destroy()
  })
  dailyMaps.clear()
}
</script>

<style scoped>
.result-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 28px 24px 48px;
}

.page-header {
  max-width: 1280px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.back-button {
  border-radius: 8px;
  font-weight: 600;
}

.page-header :deep(.ant-btn .anticon) {
  margin-right: 6px;
}

/* 内容布局 */
.content-wrapper {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  gap: 20px;
}

.side-nav {
  width: 240px;
  flex-shrink: 0;
}

.side-nav :deep(.ant-menu) {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.side-nav :deep(.ant-menu-item) {
  margin: 4px 8px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.side-nav :deep(.ant-menu-item-selected) {
  background: #eaf3ff;
  color: #0958d9;
}

.side-nav :deep(.ant-menu-item:hover) {
  background: #f0f6ff;
  color: #0958d9;
}

.main-content {
  flex: 1;
  min-width: 0;
}

/* 景点图片样式 */
.attraction-image-wrapper {
  position: relative;
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
}

.attraction-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.attraction-image-wrapper:hover .attraction-image {
  transform: scale(1.05);
}

.attraction-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  background: #1677ff;
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.badge-number {
  font-size: 18px;
}

.price-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(15, 23, 42, 0.82);
  color: white;
  padding: 4px 12px;
  border-radius: 999px;
  font-weight: bold;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* 天气卡片样式 */
.weather-card {
  background: #f8fafc;
  border: none !important;
  transition: all 0.3s ease;
}

.weather-card-sun {
  background: #fff7ed;
}

.weather-card-cloud {
  background: #f0f6ff;
}

.weather-card-rain {
  background: #e0f2fe;
}

.weather-card-snow {
  background: #f8fafc;
}

.weather-card-haze {
  background: #f5f5f4;
}

.weather-card-unknown {
  background: #f8fafc;
}

.weather-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.1);
}

.weather-date {
  font-size: 16px;
  font-weight: bold;
  color: #0f172a;
  margin-bottom: 12px;
  text-align: center;
}

.weather-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.weather-icon {
  font-size: 24px;
  width: 30px;
  text-align: center;
}

.weather-label {
  font-size: 12px;
  color: #666;
}

.weather-value {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.weather-wind {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(15, 23, 42, 0.12);
  text-align: center;
  color: #475569;
  font-size: 14px;
}

/* 回到顶部按钮 */
.back-top-button {
  width: 50px;
  height: 50px;
  background: #1677ff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-top-button:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

/* 酒店卡片样式 */
.hotel-card {
  border: 1px solid #e5e7eb !important;
  background: #ffffff;
}

.hotel-card :deep(.ant-card-head) {
  background: #f8fafc;
}

.hotel-title {
  color: #0f172a !important;
  font-weight: 700;
}

/* 顶部信息区布局 */
.top-info-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.left-info {
  flex: 0 0 400px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-map {
  flex: 1;
}

/* 行程概览卡片 */
.overview-card {
  height: fit-content;
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 14px;
  font-weight: 600;
  color: #666;
}

.info-value {
  font-size: 15px;
  color: #333;
  line-height: 1.6;
}

/* 预算卡片 */
.budget-card {
  height: fit-content;
}

.budget-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.budget-item {
  text-align: center;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.budget-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.budget-value {
  font-size: 20px;
  font-weight: 700;
  color: #1677ff;
}

.budget-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #1677ff;
  border-radius: 8px;
  color: white;
}

.total-label {
  font-size: 16px;
  font-weight: 600;
}

.total-value {
  font-size: 28px;
  font-weight: 700;
}

/* 地图卡片 */
.map-card {
  height: 100%;
  min-height: 500px;
}

.map-card :deep(.ant-card-body) {
  height: calc(100% - 57px);
  padding: 0;
}

.map-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 320px;
  overflow: hidden;
  border-radius: 0 0 8px 8px;
}

.amap-container {
  width: 100%;
  height: 100%;
  min-height: inherit;
}

.map-legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  z-index: 2;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 8px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
  color: #334155;
  font-size: 12px;
}

.map-legend.compact {
  gap: 8px;
  padding: 6px 8px;
}

.map-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.legend-hotel {
  background: #ef4444;
}

.legend-attraction {
  background: #1677ff;
}

.legend-meal {
  background: #f59e0b;
}

.map-empty-state {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.86);
  color: #64748b;
  font-size: 14px;
  font-weight: 600;
}

.daily-maps-card {
  margin-top: 20px;
}

.daily-map-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.daily-map-panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
}

.daily-map-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #edf0f5;
  background: #f8fafc;
}

.daily-map-title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.daily-map-date {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

.daily-map-count {
  flex-shrink: 0;
  padding: 4px 8px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #eff6ff;
  color: #0958d9;
  font-size: 12px;
  font-weight: 600;
}

.daily-map-shell {
  height: 320px;
  min-height: 320px;
  border-radius: 0;
}

/* 每日行程卡片 */
.days-card {
  margin-top: 20px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.day-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.day-date {
  font-size: 14px;
  color: #999;
}

.day-info {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.info-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  font-weight: 600;
  color: #475569;
  min-width: 100px;
}

.info-row .value {
  color: #0f172a;
  flex: 1;
}

/* 卡片样式优化 */
:deep(.ant-card) {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  margin-bottom: 20px;
  transition: box-shadow 0.2s ease;
}

:deep(.ant-card:hover) {
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}

:deep(.ant-card-head) {
  background: #ffffff;
  color: #0f172a !important;
  border-bottom: 1px solid #edf0f5;
  border-radius: 8px 8px 0 0;
  font-weight: 700;
}

:deep(.ant-card-head-title) {
  color: #0f172a !important;
  font-size: 17px;
}

:deep(.ant-card-head-title span) {
  color: #0f172a !important;
}

/* Collapse样式 */
:deep(.ant-collapse) {
  border: none;
  background: transparent;
}

:deep(.ant-collapse-item) {
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

:deep(.ant-collapse-header) {
  background: #f8fafc;
  padding: 16px 20px !important;
  font-weight: 600;
}

:deep(.ant-collapse-content) {
  border-top: 1px solid #e5e7eb;
}

:deep(.ant-collapse-content-box) {
  padding: 20px;
}

/* 统计卡片样式 */
:deep(.ant-statistic-title) {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

:deep(.ant-statistic-content) {
  font-size: 24px;
  font-weight: 600;
  color: #1677ff;
}

/* 景点卡片样式 */
:deep(.ant-list-item) {
  transition: all 0.3s ease;
}

:deep(.ant-list-item:hover) {
  transform: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .result-container {
    padding: 20px 10px;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .content-wrapper {
    display: block;
  }

  .side-nav {
    display: none;
  }

  .top-info-section {
    flex-direction: column;
  }

  .left-info {
    flex: 1;
  }

  .map-card {
    min-height: 360px;
  }

  .daily-map-grid {
    grid-template-columns: 1fr;
  }

  .map-legend {
    flex-wrap: wrap;
    right: 12px;
  }
}
</style>

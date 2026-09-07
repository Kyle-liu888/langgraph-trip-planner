<template>
  <div class="result-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <a-button class="back-button" size="large" @click="goBack">
        <ArrowLeftOutlined />
        返回首页
      </a-button>
      <a-space size="middle" wrap>
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
      <nav class="itinerary-nav" aria-label="行程章节">
        <button :aria-current="activeSection === 'overview' ? 'location' : undefined" @click="scrollToSection({ key: 'overview' })"><OrderedListOutlined />行程概览</button>
        <button v-if="tripPlan.budget" :aria-current="activeSection === 'budget' ? 'location' : undefined" @click="scrollToSection({ key: 'budget' })"><WalletOutlined />预算</button>
        <button :aria-current="activeSection === 'map' ? 'location' : undefined" @click="scrollToSection({ key: 'map' })"><EnvironmentOutlined />全程地图</button>
        <button :aria-current="activeSection === 'daily-maps' ? 'location' : undefined" @click="scrollToSection({ key: 'daily-maps' })">每日地图</button>
        <span class="nav-divider" aria-hidden="true"></span>
        <button v-for="(day, index) in tripPlan.days" :key="`day-${index}`" :aria-current="activeSection === `day-${index}` ? 'location' : undefined" @click="scrollToSection({ key: `day-${index}` })">第 {{ day.day_index + 1 }} 天</button>
        <button v-if="tripPlan.weather_info?.length" :aria-current="activeSection === 'weather' ? 'location' : undefined" @click="scrollToSection({ key: 'weather' })"><CloudOutlined />天气</button>
      </nav>

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
                  <div class="budget-label">景点门票（估算）</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_attractions }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-label">酒店住宿（估算）</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_hotels }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-label">餐饮费用（估算）</div>
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
                :grid="{ gutter: 16, xs: 1, sm: 1, md: 1, lg: 1, xl: 1, xxl: 2 }"
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
                            <span aria-hidden="true">↑</span><span class="sr-only">上移 {{ item.name }}</span>
                          </a-button>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'down')"
                            :disabled="index === day.attractions.length - 1"
                          >
                            <span aria-hidden="true">↓</span><span class="sr-only">下移 {{ item.name }}</span>
                          </a-button>
                          <a-button
                            size="small"
                            danger
                            @click="deleteAttraction(day.day_index, index)"
                          >
                            <span>移除</span><span class="sr-only"> {{ item.name }}</span>
                          </a-button>
                        </a-space>
                      </template>

                      <!-- 景点图片 -->
                      <div class="attraction-image-wrapper">
                        <img
                          v-if="getPhoto(item)?.status === 'available'"
                          :src="getPhoto(item)?.photo_url || undefined"
                          :alt="item.name"
                          class="attraction-image"
                          @error="handlePhotoError(item)"
                        />
                        <div v-else class="attraction-photo-placeholder" role="status">{{ editMode && !getPhoto(item) ? '保存后加载景点图片' : photoLabel(getPhoto(item)) }}</div>
                        <span v-if="getPhoto(item)?.status === 'available'" class="photo-source">图片来源：高德地图</span>
                        <div class="attraction-badge">
                          <span class="badge-number">{{ index + 1 }}</span>
                        </div>
                      </div>

                      <!-- 编辑模式下可编辑的字段 -->
                      <div v-if="editMode" class="attraction-details attraction-edit">
                        <p><strong>地址:</strong></p>
                        <a-input v-model:value="item.address" size="small" style="margin-bottom: 8px" />

                        <p><strong>游览时长(分钟):</strong></p>
                        <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width: 100%; margin-bottom: 8px" />

                        <p><strong>描述:</strong></p>
                        <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom: 8px" />
                      </div>

                      <!-- 查看模式 -->
                      <div v-else class="attraction-details">
                        <p><strong>地址:</strong> {{ item.address }}</p>
                        <p><strong>游览时长:</strong> {{ item.visit_duration }}分钟</p>
                        <p><strong>描述:</strong> {{ item.description }}</p>
                        <p v-if="item.rating"><strong>评分:</strong> {{ item.rating }}⭐</p>
                      </div>
                      <AttractionVisitInfo
                        :city="tripPlan.city" :name="item.name" :visit-date="day.date"
                        :ticket-price="item.ticket_price" :editing="editMode"
                        :info="visitInfos[visitKey(tripPlan.city, { place: item, visitDate: day.date })]"
                      />
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <!-- 酒店推荐 -->
              <a-divider v-if="day.hotel" orientation="left">住宿推荐</a-divider>
              <MerchantCard v-if="day.hotel" class="hotel-card"
                :city="tripPlan.city" kind="hotel" :merchant="day.hotel"
                :estimated-cost="day.hotel.estimated_cost" :price-range="day.hotel.price_range"
                :hotel-type="day.hotel.type" :distance="day.hotel.distance"
                :info="getMerchantInfo('hotel', day.hotel)" />

              <!-- 餐饮安排 -->
              <a-divider orientation="left">餐饮安排</a-divider>
              <div class="meal-cards">
                <MerchantCard v-for="(meal, mealIndex) in day.meals" :key="meal.type + '-' + mealIndex"
                  :city="tripPlan.city" kind="food" :merchant="meal" :meal-label="getMealLabel(meal.type)"
                  :estimated-cost="meal.estimated_cost" :description="meal.description"
                  :info="getMerchantInfo('food', meal)" />
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <a-card id="weather" v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0" title="天气信息" style="margin-top: 20px" :bordered="false">
        <a-list
          :data-source="tripPlan.weather_info"
          :grid="{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 2, xl: 3 }"
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
    <a-back-top :visibility-height="300" :duration="1" shape="square" type="primary" class="back-top-button" aria-label="回到页面顶部" title="回到页面顶部">
      <template #icon><span aria-hidden="true">↑</span></template>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import AttractionVisitInfo from '@/components/AttractionVisitInfo.vue'
import MerchantCard from '@/components/MerchantCard.vue'
import { loadMerchantInfos, merchantKey, isGenericMerchant,
  type MerchantInfo, type MerchantIdentity, type MerchantKind, type MerchantStop } from '@/services/merchantInfo'
import { loadVisitInfos, visitKey, type VisitInfo } from '@/services/visitInfo'
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
import type { Attraction, TripPlan } from '@/types'
import { loadPlacePhotos, photoKey, photoLabel, type PlacePhoto } from '@/services/photos'
import { saveTripPlan, type TripRecord } from '@/services/trips'
import { useTrips } from '@/stores/trips'

const props = defineProps<{ record: TripRecord }>()
const revision = ref(props.record.revision)
const trips = useTrips()

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, PlacePhoto>>({})
const getPhoto = (place: Attraction) => attractionPhotos.value[photoKey(tripPlan.value?.city || '', place)]
const handlePhotoError = (place: Attraction) => {
  attractionPhotos.value[photoKey(tripPlan.value?.city || '', place)] = { photo_url: null, source: null, status: 'unavailable' }
}
const activeSection = ref('overview')
const activeDays = ref<number[]>([0]) // 默认展开第一天
let map: any = null
let disposed = false
const visitInfos = ref<Record<string, VisitInfo>>({})
watch(() => JSON.stringify([
  editMode.value, tripPlan.value?.city,
  tripPlan.value?.days.flatMap(day => day.attractions.map(place => visitKey(tripPlan.value!.city, { place, visitDate: day.date }))),
]), (_signature, _previous, onCleanup) => {
  let stale = false
  onCleanup(() => { stale = true })
  if (!tripPlan.value || editMode.value) return
  const city = tripPlan.value.city
  const stops = tripPlan.value.days.flatMap(day => day.attractions.map(place => ({ place, visitDate: day.date })))
  visitInfos.value = {}
  void loadVisitInfos(city, stops, (key, info) => { visitInfos.value[key] = info }, () => stale || disposed)
}, { immediate: true })
let AMapApi: any = null
const dailyMaps = new Map<number, any>()
const merchantInfos = ref<Record<string, MerchantInfo>>({})
const getMerchantInfo = (kind: MerchantKind, merchant: MerchantIdentity) =>
  merchantInfos.value[merchantKey(tripPlan.value?.city || '', { kind, merchant })]
const expandedMerchants = computed<MerchantStop[]>(() => {
  const keys = Array.isArray(activeDays.value) ? activeDays.value : [activeDays.value]
  return keys.flatMap(key => {
    const day = tripPlan.value?.days[Number(key)]
    if (!day) return []
    return [...(day.hotel ? [{ kind: 'hotel' as const, merchant: day.hotel }] : []),
      ...day.meals.map(merchant => ({ kind: 'food' as const, merchant }))]
  })
})
watch(() => JSON.stringify([editMode.value, tripPlan.value?.city,
  expandedMerchants.value.map(stop => merchantKey(tripPlan.value?.city || '', stop))]), (_current, _previous, cleanup) => {
  let stale = false
  cleanup(() => { stale = true })
  if (!tripPlan.value || editMode.value) return
  void loadMerchantInfos(tripPlan.value.city, expandedMerchants.value,
    (key, info) => { merchantInfos.value[key] = info }, () => stale || disposed)
}, { immediate: true })
// Refresh map layers only when a newly verified location can supplement a missing one.
// Supplemental facts stay outside TripPlan and are never included in Save.
watch(() => JSON.stringify(tripPlan.value?.days.map((_day, index) => getDayMapPoints(index))), () => {
  if (!AMapApi || disposed || editMode.value) return
  destroyMaps()
  nextTick(() => { if (!disposed && AMapApi) { initOverviewMap(AMapApi); initDailyMaps(AMapApi) } })
})

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
  const data = props.record.plan
  if (data) {
    tripPlan.value = JSON.parse(JSON.stringify(data))
    // 加载景点图片
    void loadAttractionPhotos()
    // Merchant facts load independently for the expanded day; do not block maps.
    // 等待DOM渲染完成后初始化地图
    await nextTick()
    initMaps()
  }
})

onUnmounted(() => {
  disposed = true
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
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    element.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' })
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
const saveChanges = async () => {
  if (!tripPlan.value) return
  try {
    const saved = await saveTripPlan(props.record.id, tripPlan.value, revision.value)
    revision.value = saved.revision
    trips.upsert(saved)
  } catch (e) { message.error((e as Error).message); return }
  editMode.value = false
  message.success('修改已保存')
  void loadAttractionPhotos()

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
  await loadPlacePhotos(tripPlan.value.city, tripPlan.value.days.flatMap(day => day.attractions),
    (key, photo) => { attractionPhotos.value[key] = photo }, () => disposed)
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

  const hotelInfo = displayHotel?.hotel ? getMerchantInfo('hotel', displayHotel.hotel) : undefined
  const hotelLocation = isValidLocation(displayHotel?.hotel?.location) ? displayHotel?.hotel?.location
    : hotelInfo?.match_status === 'matched' ? hotelInfo.place?.location : undefined
  if (displayHotel?.hotel && isValidLocation(hotelLocation)) {
    const hotel = displayHotel.hotel
    points.push({
      type: 'hotel',
      name: hotel.name,
      address: hotelInfo?.place?.address || hotel.address,
      description: displayHotel.isCarriedOver ? '沿用前一晚住处，方便当天出发或取行李' : hotel.distance,
      location: normalizeLocation(hotelLocation),
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
    if (isGenericMerchant('food', tripPlan.value!.city, meal.name)) return
    const info = getMerchantInfo('food', meal)
    const location = isValidLocation(meal.location) ? meal.location : info?.match_status === 'matched' ? info.place?.location : undefined
    if (!isValidLocation(location)) return

    points.push({
      type: 'meal',
      name: meal.name,
      address: info?.place?.address || meal.address,
      description: meal.description,
      location: normalizeLocation(location),
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
  max-width: 1440px;
  margin: auto;
  padding: 0 36px 64px;
  color: var(--color-ink, #203c38);
}
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 0 0 22px; flex-wrap: wrap; }
.back-button { border-color: transparent; background: transparent; padding-left: 0; font-size: 14px; color: var(--color-muted, #657873); }
.content-wrapper { min-width: 0; }
.itinerary-nav { display: flex; align-items: center; gap: 4px; overflow-x: auto; max-width: 100%; padding: 8px 0 14px; margin-bottom: 22px; border-bottom: 1px solid var(--color-line, #dce5df); scrollbar-width: thin; }
.itinerary-nav button { display: inline-flex; align-items: center; gap: 7px; flex-shrink: 0; min-height: 40px; padding: 8px 13px; color: var(--color-muted, #657873); border: none; border-radius: 7px; background: transparent; cursor: pointer; white-space: nowrap; font: inherit; font-size: 13px; }
.itinerary-nav button:hover { background: #eaf0e9; color: var(--color-primary, #176b5b); }
.itinerary-nav button[aria-current] { color: #fff; background: var(--color-primary, #176b5b); }
.itinerary-nav button:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 2px; }
.nav-divider { flex: 0 0 1px; height: 20px; background: var(--color-line, #dce5df); margin: 0 9px; }
.main-content { min-width: 0; }
.main-content [id] { scroll-margin-top: 90px; }
.top-info-section { display: grid; grid-template-columns: minmax(280px, .95fr) minmax(300px, 1.1fr); align-items: stretch; gap: 22px; }
.left-info { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.right-map { min-width: 0; }
:deep(.ant-card) { background: var(--color-surface, #fff); border: 1px solid var(--color-line, #dce5df); border-radius: 12px; box-shadow: none; }
:deep(.ant-card-head) { min-height: 56px; padding: 0 22px; border-color: var(--color-line, #dce5df); background: transparent; }
:deep(.ant-card-head-title) { color: var(--color-ink, #203c38); font-size: 16px; white-space: normal; overflow-wrap: anywhere; }
:deep(.ant-card-body) { padding: 22px; }
.overview-card :deep(.ant-card-head-title) { font-family: STKaiti, KaiTi, 'Noto Serif CJK SC', serif; font-size: 26px; }
.overview-content { display: grid; gap: 16px; }
.info-item { display: grid; gap: 6px; }
.info-label, .budget-label { font-size: 12px; color: var(--color-muted, #657873); }
.info-value { line-height: 1.85; font-size: 14px; overflow-wrap: anywhere; }
.budget-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 18px; margin-bottom: 22px; }
.budget-value { margin-top: 5px; font-size: 21px; color: var(--color-ink, #203c38); font-weight: 600; font-variant-numeric: tabular-nums; }
.budget-total { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 16px 18px; background: #eaf2e5; border-radius: 8px; color: #254e3a; }
.total-label { font-size: 13px; }
.total-value { font-size: 28px; font-weight: 650; font-variant-numeric: tabular-nums; }
.map-card { height: 100%; display: flex; flex-direction: column; min-height: 480px; }
.map-card :deep(.ant-card-body) { flex: 1; padding: 0; display: flex; min-height: 360px; }
.map-shell { position: relative; width: 100%; height: 100%; min-height: 360px; overflow: hidden; border-radius: 0 0 12px 12px; background: #eaf0e9; }
.map-card .map-shell { flex: 1; height: auto; }
.amap-container { width: 100%; height: 100%; min-height: inherit; }
.map-card .amap-container { position: absolute; inset: 0; }
.map-legend { position: absolute; left: 12px; bottom: 16px; z-index: 2; display: flex; align-items: center; flex-wrap: wrap; gap: 10px; padding: 8px 10px; background: rgba(255,255,255,.95); border: 1px solid var(--color-line, #dce5df); border-radius: 6px; color: #334155; font-size: 12px; }
.map-legend.compact { gap: 8px; padding: 6px 8px; }
.map-legend span { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.legend-hotel { background: #ef4444; }
.legend-attraction { background: #1677ff; }
.legend-meal { background: #f59e0b; }
.map-empty-state { position: absolute; inset: 0; z-index: 3; display: grid; place-items: center; background: rgba(247,249,246,.92); color: var(--color-muted, #657873); font-size: 14px; }
.daily-maps-card, .days-card { margin-top: 28px; }
.daily-map-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.daily-map-panel { min-width: 0; overflow: hidden; border: 1px solid var(--color-line, #dce5df); border-radius: 9px; }
.daily-map-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px; background: var(--color-paper, #f7f9f6); }
.daily-map-title { font-size: 14px; font-weight: 650; }
.daily-map-date { margin-top: 3px; color: var(--color-muted, #657873); font-size: 12px; }
.daily-map-count { font-size: 12px; color: var(--color-primary, #176b5b); white-space: nowrap; }
.daily-map-shell { height: 280px; min-height: 280px; border-radius: 0; }
.day-header { display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap; width: 100%; }
.day-title { font-size: 18px; color: var(--color-ink, #203c38); }
.day-date { color: var(--color-muted, #657873); font-size: 13px; font-weight: 400; }
.day-info { padding: 18px 20px; margin-bottom: 20px; background: var(--color-paper, #f7f9f6); border-left: 2px solid #aac9aa; border-radius: 0 7px 7px 0; }
.info-row { display: flex; gap: 18px; margin-bottom: 10px; line-height: 1.85; }
.info-row:last-child { margin-bottom: 0; }
.info-row .label { min-width: 60px; color: var(--color-muted, #657873); font-size: 12px; }
.info-row .value { flex: 1; min-width: 0; font-size: 14px; overflow-wrap: anywhere; }
:deep(.ant-collapse) { border: none; background: transparent; }
:deep(.ant-collapse-item) { margin-bottom: 14px; border: 1px solid var(--color-line, #dce5df); border-radius: 9px; overflow: hidden; }
:deep(.ant-collapse-header) { background: #eef3eb; padding: 17px 20px !important; font-weight: 600; align-items: center !important; }
:deep(.ant-collapse-content) { border-top: 1px solid var(--color-line, #dce5df); }
:deep(.ant-collapse-content-box) { padding: 24px; }
:deep(.ant-divider-inner-text) { color: var(--color-ink, #203c38); font-size: 14px; }
.attraction-card :deep(.ant-card-head) { padding: 0 18px; min-height: 54px; }
.attraction-card :deep(.ant-card-head-title) { font-size: 19px; font-weight: 650; }
.attraction-card :deep(.ant-card-body) { padding: 18px; }
.attraction-image-wrapper { position: relative; margin-bottom: 20px; border-radius: 8px; overflow: hidden; }
.attraction-image { width: 100%; height: clamp(200px, 24vw, 340px); object-fit: cover; display: block; }
.attraction-photo-placeholder { min-height: 180px; display: grid; place-items: center; padding: 25px; color: var(--color-muted, #657873); background: #eef3eb; font-size: 13px; }
.photo-source { position: absolute; bottom: 8px; right: 8px; padding: 3px 7px; color: #fff; background: #203c38cf; border-radius: 4px; font-size: 11px; }
.attraction-badge { position: absolute; top: 12px; left: 12px; width: 34px; height: 40px; border-radius: 4px 4px 12px 4px; display: grid; place-items: center; font-size: 17px; font-weight: 650; color: #fff; background: var(--color-primary, #176b5b); }
.attraction-details { font-size: 14px; line-height: 1.85; overflow-wrap: anywhere; }
.attraction-details p { margin: 8px 0; }
.attraction-details strong { font-weight: 500; color: var(--color-muted, #657873); margin-right: 6px; }
.attraction-edit { padding: 4px 0; }
.hotel-card :deep(.ant-card-head) { background: var(--color-paper, #f7f9f6); }
.hotel-title { color: var(--color-ink, #203c38); }
.meal-cards { display: grid; gap: 14px; }
:deep(.ant-descriptions-item-content) { overflow-wrap: anywhere; }
.weather-card { background: var(--color-paper, #f7f9f6); }
.weather-card-sun { background: #fcf8e9; }
.weather-card-cloud, .weather-card-rain { background: #edf4f3; }
.weather-card-snow, .weather-card-haze, .weather-card-unknown { background: #f3f4f0; }
.weather-date { font-size: 15px; font-weight: 600; margin-bottom: 18px; }
.weather-info-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.weather-icon { width: 28px; font-size: 23px; text-align: center; }
.weather-label { color: var(--color-muted, #657873); font-size: 12px; }
.weather-value { font-size: 15px; font-weight: 500; }
.weather-wind { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--color-line, #dce5df); font-size: 12px; color: var(--color-muted, #657873); }
.back-top-button { width: 44px; height: 44px; border: none; border-radius: 10px; display: grid; place-items: center; background: var(--color-primary, #176b5b); color: #fff; font-size: 23px; cursor: pointer; }
.back-top-button :deep(.ant-float-btn-body) { background: var(--color-primary, #176b5b); border-radius: 10px; }
.back-top-button :deep(.ant-float-btn-icon) { color: #fff; font-size: 23px; }
.back-top-button:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 4px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 1180px) {
  .result-container { padding: 0 24px 48px; }
  .top-info-section { grid-template-columns: 1fr; }
  .map-card { min-height: 400px; }
  .left-info { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
}
@media (max-width: 760px) {
  .result-container { padding: 0 16px 40px; }
  .page-header { gap: 10px; padding-bottom: 12px; }
  .page-header :deep(.ant-space) { gap: 8px !important; }
  .back-button { height: 34px; }
  .itinerary-nav { margin-bottom: 18px; padding-bottom: 10px; }
  .left-info, .daily-map-grid { grid-template-columns: 1fr; }
  .top-info-section { gap: 18px; }
  :deep(.ant-card-head) { padding: 0 16px; }
  :deep(.ant-card-body) { padding: 16px; }
  :deep(.ant-collapse-header) { padding: 15px 14px !important; }
  :deep(.ant-collapse-content-box) { padding: 12px; }
  .attraction-card :deep(.ant-card-head) { padding: 0 12px; }
  .attraction-card :deep(.ant-card-body) { padding: 12px; }
  .day-info { padding: 14px; }
  .info-row { gap: 12px; }
  .map-card, .map-card :deep(.ant-card-body) { min-height: 320px; }
  .map-shell { min-height: 280px; }
  .map-legend { right: auto; max-width: calc(100% - 24px); }
  .daily-maps-card, .days-card { margin-top: 22px; }
  .attraction-card :deep(.ant-card-head-wrapper) { flex-wrap: wrap; padding: 10px 0; gap: 6px; }
  .attraction-card :deep(.ant-card-extra) { margin-inline-start: auto; }
}
@media (prefers-reduced-motion: reduce) { .result-container :deep(*) { scroll-behavior: auto !important; transition: none !important; animation: none !important; } }
</style>

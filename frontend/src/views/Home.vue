<template>
  <div class="home-container">
    <div class="planner-page">
      <div class="top-banner">
        <div class="top-banner-content">
          <div class="banner-kicker">AI Trip Planner</div>
          <h1>创建一份可执行的旅行计划</h1>
          <p>输入目的地、日期、同行人数和预算偏好，系统会结合工具快照生成每日行程。</p>
        </div>
        <div class="banner-summary">
          <div>
            <span class="summary-label">行程</span>
            <strong>{{ formData.travel_days }} 天</strong>
          </div>
          <div>
            <span class="summary-label">同行</span>
            <strong>{{ formData.party.total }} 人</strong>
          </div>
          <div>
            <span class="summary-label">协议</span>
            <strong>Planner</strong>
          </div>
        </div>
      </div>

      <a-card class="form-card" :bordered="false">
        <div class="form-card-header">
          <div>
            <div class="form-eyebrow">Plan Request</div>
            <h2>行程需求</h2>
          </div>
          <div class="header-status">
            <span>{{ formData.city || '未选择城市' }}</span>
            <span>{{ formData.travel_days }} 天</span>
            <span>{{ formData.party.total }} 人</span>
          </div>
        </div>

        <a-form
          :model="formData"
          layout="vertical"
          @finish="handleSubmit"
        >
          <div class="form-section">
            <div class="section-header">
              <EnvironmentOutlined />
              <span class="section-title">目的地与日期</span>
            </div>

            <a-row :gutter="[20, 16]">
              <a-col :xs="{ span: 24 }" :lg="{ span: 10 }">
                <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地城市' }]">
                  <template #label>
                    <span class="form-label">目的地城市</span>
                  </template>
                  <a-input
                    v-model:value="formData.city"
                    placeholder="例如: 北京"
                    size="large"
                    class="custom-input"
                  />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :sm="{ span: 12 }" :lg="{ span: 7 }">
                <a-form-item name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
                  <template #label>
                    <span class="form-label">开始日期</span>
                  </template>
                  <a-date-picker
                    v-model:value="formData.start_date"
                    style="width: 100%"
                    size="large"
                    class="custom-input"
                    placeholder="选择日期"
                  />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :sm="{ span: 12 }" :lg="{ span: 7 }">
                <a-form-item name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
                  <template #label>
                    <span class="form-label">结束日期</span>
                  </template>
                  <a-date-picker
                    v-model:value="formData.end_date"
                    style="width: 100%"
                    size="large"
                    class="custom-input"
                    placeholder="选择日期"
                  />
                </a-form-item>
              </a-col>
            </a-row>
          </div>

          <div class="form-section">
            <div class="section-header">
              <TeamOutlined />
              <span class="section-title">同行与预算</span>
            </div>

            <a-row :gutter="[20, 16]">
              <a-col :xs="{ span: 8 }" :md="{ span: 4 }">
                <a-form-item name="adults">
                  <template #label>
                    <span class="form-label">成人</span>
                  </template>
                  <a-input-number v-model:value="formData.party.adults" :min="0" :max="20" size="large" class="custom-input" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 8 }" :md="{ span: 4 }">
                <a-form-item name="children">
                  <template #label>
                    <span class="form-label">儿童</span>
                  </template>
                  <a-input-number v-model:value="formData.party.children" :min="0" :max="20" size="large" class="custom-input" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 8 }" :md="{ span: 4 }">
                <a-form-item name="elders">
                  <template #label>
                    <span class="form-label">老人</span>
                  </template>
                  <a-input-number v-model:value="formData.party.elders" :min="0" :max="20" size="large" class="custom-input" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :md="{ span: 4 }">
                <a-form-item name="companion_type">
                  <template #label>
                  <span class="form-label">同行类型</span>
                </template>
                <a-select v-model:value="formData.party.companion_type" size="large" class="custom-select">
                    <a-select-option
                      v-for="option in companionTypeOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :md="{ span: 4 }">
                <a-form-item name="budget_amount">
                  <template #label>
                    <span class="form-label">总预算</span>
                  </template>
                  <a-input-number
                    v-model:value="formData.budget_constraint.amount"
                    :min="0"
                    :step="100"
                    size="large"
                    class="custom-input"
                    style="width: 100%"
                    placeholder="可不填"
                  />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :md="{ span: 4 }">
                <a-form-item name="budget_level">
                  <template #label>
                  <span class="form-label">预算档位</span>
                </template>
                <a-select v-model:value="formData.budget_constraint.budget_level" size="large" class="custom-select">
                    <a-select-option
                      v-for="option in budgetLevelOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
            </a-row>
          </div>

          <div class="form-section">
            <div class="section-header">
              <CarOutlined />
              <span class="section-title">偏好设置</span>
            </div>

            <a-row :gutter="[20, 16]">
              <a-col :xs="{ span: 24 }" :lg="{ span: 8 }">
                <a-form-item name="transportation">
                  <template #label>
                  <span class="form-label">交通方式</span>
                </template>
                <a-select v-model:value="formData.transportation" size="large" class="custom-select">
                    <a-select-option
                      v-for="option in transportationOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :lg="{ span: 8 }">
                <a-form-item name="accommodation">
                  <template #label>
                  <span class="form-label">住宿偏好</span>
                </template>
                <a-select v-model:value="formData.accommodation" size="large" class="custom-select">
                    <a-select-option
                      v-for="option in accommodationOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :lg="{ span: 8 }">
                <a-form-item name="preferences">
                  <template #label>
                    <span class="form-label">旅行偏好</span>
                  </template>
                  <div class="preference-tags">
                    <a-checkbox-group v-model:value="formData.preferences" class="custom-checkbox-group">
                      <a-checkbox
                        v-for="option in preferenceOptions"
                        :key="option.value"
                        :value="option.value"
                        class="preference-tag"
                      >
                        <span class="preference-icon">{{ option.icon }}</span>
                        <span>{{ option.label }}</span>
                      </a-checkbox>
                    </a-checkbox-group>
                  </div>
                </a-form-item>
              </a-col>
            </a-row>
          </div>

          <div class="form-section">
            <div class="section-header">
              <EditOutlined />
              <span class="section-title">额外要求</span>
            </div>

            <a-form-item name="free_text_input">
              <a-textarea
                v-model:value="formData.free_text_input"
                placeholder="请输入您的额外要求，例如：想去看升旗、需要无障碍设施、对海鲜过敏等..."
                :rows="3"
                size="large"
                class="custom-textarea"
              />
            </a-form-item>
          </div>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              size="large"
              block
              class="submit-button"
            >
              <template v-if="!loading">
                <RocketOutlined />
                <span>开始规划行程</span>
              </template>
              <template v-else>
                <span>正在生成中...</span>
              </template>
            </a-button>
          </a-form-item>

          <a-form-item v-if="loading">
            <div class="loading-container">
              <a-progress
                :percent="loadingProgress"
                status="active"
                :stroke-color="{
                  '0%': '#0f766e',
                  '100%': '#2563eb',
                }"
                :stroke-width="8"
              />
              <p class="loading-status">
                {{ loadingStatus }}
              </p>
            </div>
          </a-form-item>
        </a-form>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  CarOutlined,
  EditOutlined,
  EnvironmentOutlined,
  RocketOutlined,
  TeamOutlined
} from '@ant-design/icons-vue'
import { generateTripPlan } from '@/services/api'
import type { TripFormData } from '@/types'
import type { Dayjs } from 'dayjs'

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const companionTypeOptions = [
  { label: '独行', value: 'solo' },
  { label: '情侣', value: 'couple' },
  { label: '朋友', value: 'friends' },
  { label: '亲子', value: 'family_with_children' },
  { label: '带长辈', value: 'family_with_elders' },
  { label: '商务', value: 'business' },
  { label: '其他', value: 'other' }
]

const budgetLevelOptions = [
  { label: '节省', value: 'limited' },
  { label: '标准', value: 'standard' },
  { label: '舒适', value: 'comfortable' },
  { label: '高端', value: 'premium' },
  { label: '奢华', value: 'luxury' }
]

const transportationOptions = [
  { label: '公共交通', value: '公共交通' },
  { label: '地铁公交', value: '地铁公交' },
  { label: '打车/网约车', value: '打车/网约车' },
  { label: '自驾', value: '自驾' },
  { label: '租车自驾', value: '租车自驾' },
  { label: '包车/私人司机', value: '包车/私人司机' },
  { label: '高铁+市内交通', value: '高铁+市内交通' },
  { label: '飞机+市内交通', value: '飞机+市内交通' },
  { label: '骑行/步行', value: '骑行/步行' },
  { label: '混合交通', value: '混合交通' },
  { label: '无障碍交通优先', value: '无障碍交通优先' }
]

const accommodationOptions = [
  { label: '经济型酒店', value: '经济型酒店' },
  { label: '舒适型酒店', value: '舒适型酒店' },
  { label: '高端酒店', value: '高端酒店' },
  { label: '豪华酒店', value: '豪华酒店' },
  { label: '亲子酒店', value: '亲子酒店' },
  { label: '民宿', value: '民宿' }
]

const preferenceOptions = [
  { label: '历史文化', value: '历史文化', icon: '🏛️' },
  { label: '自然风光', value: '自然风光', icon: '🏞️' },
  { label: '美食探店', value: '美食', icon: '🍜' },
  { label: '购物商圈', value: '购物', icon: '🛍️' },
  { label: '艺术展览', value: '艺术', icon: '🎨' },
  { label: '休闲放松', value: '休闲', icon: '☕' },
  { label: '亲子友好', value: '亲子友好', icon: '🧸' },
  { label: '老人友好', value: '老人友好', icon: '🧓' },
  { label: '小众路线', value: '小众路线', icon: '🧭' },
  { label: '夜游体验', value: '夜游', icon: '🌃' },
  { label: '摄影打卡', value: '摄影打卡', icon: '📷' },
  { label: '博物馆', value: '博物馆', icon: '🏺' },
  { label: '城市漫步', value: '城市漫步', icon: '🚶' },
  { label: '户外徒步', value: '户外徒步', icon: '🥾' },
  { label: '主题乐园', value: '主题乐园', icon: '🎢' },
  { label: '避开人群', value: '避开人群', icon: '🌿' }
]

type TripFormState = Omit<TripFormData, 'start_date' | 'end_date'> & {
  start_date: Dayjs | null
  end_date: Dayjs | null
}

const formData = reactive<TripFormState>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: '',
  party: {
    adults: 1,
    children: 0,
    elders: 0,
    total: 1,
    companion_type: 'solo'
  },
  budget_constraint: {
    amount: null,
    scope: 'total',
    currency: 'CNY',
    budget_level: 'standard',
    strictness: 'none'
  }
})

// 监听日期变化,自动计算旅行天数
watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days
    } else if (days > 30) {
      message.warning('旅行天数不能超过30天')
      formData.end_date = null
    } else {
      message.warning('结束日期不能早于开始日期')
      formData.end_date = null
    }
  }
})

// planner协议要求party.total显式等于成人、儿童、老人之和
watch([() => formData.party.adults, () => formData.party.children, () => formData.party.elders], ([adults, children, elders]) => {
  const adultCount = Number(adults || 0)
  const childCount = Number(children || 0)
  const elderCount = Number(elders || 0)
  formData.party.total = adultCount + childCount + elderCount
  if (childCount > 0) {
    formData.party.companion_type = 'family_with_children'
  } else if (elderCount > 0) {
    formData.party.companion_type = 'family_with_elders'
  } else if (adultCount === 1) {
    formData.party.companion_type = 'solo'
  } else if (adultCount === 2) {
    formData.party.companion_type = 'couple'
  } else if (adultCount > 2) {
    formData.party.companion_type = 'friends'
  }
})

const handleSubmit = async () => {
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择日期')
    return
  }

  if (formData.party.total <= 0) {
    message.error('同行人数至少为1人')
    return
  }

  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = '正在初始化...'

  // 模拟进度更新
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10

      // 更新状态文本
      if (loadingProgress.value <= 30) {
        loadingStatus.value = '🔍 正在搜索景点...'
      } else if (loadingProgress.value <= 50) {
        loadingStatus.value = '🌤️ 正在查询天气...'
      } else if (loadingProgress.value <= 70) {
        loadingStatus.value = '🏨 正在推荐酒店...'
      } else {
        loadingStatus.value = '📋 正在生成行程计划...'
      }
    }
  }, 500)

  try {
    const budgetAmount = formData.budget_constraint.amount
    const budgetStrictness = budgetAmount === null || budgetAmount === undefined ? 'none' : 'soft'
    const requestData: TripFormData = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input,
      party: {
        adults: formData.party.adults,
        children: formData.party.children,
        elders: formData.party.elders,
        total: formData.party.total,
        companion_type: formData.party.companion_type
      },
      budget_constraint: {
        amount: budgetAmount ?? null,
        scope: 'total',
        currency: 'CNY',
        budget_level: formData.budget_constraint.budget_level,
        strictness: budgetStrictness
      }
    }

    const response = await generateTripPlan(requestData)

    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '✅ 完成!'

    if (response.success && response.data) {
      // 保存到sessionStorage
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))

      message.success('旅行计划生成成功!')

      // 短暂延迟后跳转
      setTimeout(() => {
        router.push('/result')
      }, 500)
    } else {
      message.error(response.message || '生成失败')
    }
  } catch (error: any) {
    clearInterval(progressInterval)
    message.error(error.message || '生成旅行计划失败,请稍后重试')
  } finally {
    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: 28px 24px 48px;
  width: 100%;
  background: #f5f7fa;
}

.planner-page {
  max-width: 1280px;
  margin: 0 auto;
}

.top-banner {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  min-height: 220px;
  margin-bottom: -28px;
  padding: 34px 38px 58px;
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.62)),
    url('https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80') center/cover;
  color: #ffffff;
}

.top-banner-content {
  max-width: 620px;
}

.banner-kicker {
  margin-bottom: 12px;
  color: rgba(255, 255, 255, 0.76);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.top-banner h1 {
  margin: 0;
  font-size: 36px;
  font-weight: 760;
  line-height: 1.18;
}

.top-banner p {
  margin: 14px 0 0;
  color: rgba(255, 255, 255, 0.84);
  font-size: 16px;
  line-height: 1.7;
}

.banner-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  min-width: 340px;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(10px);
}

.banner-summary > div {
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.12);
}

.summary-label {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}

.banner-summary strong {
  color: #ffffff;
  font-size: 20px;
}

.form-card {
  position: relative;
  z-index: 1;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff !important;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
}

.form-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
  padding-bottom: 20px;
  border-bottom: 1px solid #edf0f5;
}

.form-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.form-card-header h2 {
  margin: 6px 0 0;
  color: #0f172a;
  font-size: 24px;
  font-weight: 700;
}

.header-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.header-status span {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f3f6fb;
  color: #475569;
  font-size: 13px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 22px;
  border-bottom: 1px solid #eef2f7;
}

.form-section:last-of-type {
  border-bottom: none;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #1677ff;
}

.section-header :deep(.anticon) {
  font-size: 17px;
}

.section-title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.form-label {
  color: #475569;
  font-size: 13px;
  font-weight: 650;
}

.custom-input :deep(.ant-input) {
  border-radius: 8px;
}

.custom-input :deep(.ant-input),
.custom-textarea :deep(.ant-input),
.custom-select :deep(.ant-select-selector),
.custom-input :deep(.ant-picker) {
  border-color: #d9dee8 !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.custom-input :deep(.ant-input:hover),
.custom-textarea :deep(.ant-input:hover),
.custom-select:hover :deep(.ant-select-selector),
.custom-input :deep(.ant-picker:hover) {
  border-color: #1677ff !important;
}

.custom-input :deep(.ant-input:focus),
.custom-textarea :deep(.ant-input:focus),
.custom-select :deep(.ant-select-focused .ant-select-selector),
.custom-input :deep(.ant-picker-focused) {
  border-color: #1677ff !important;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.12) !important;
}

.preference-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.custom-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  width: 100%;
}

.preference-tag :deep(.ant-checkbox-wrapper) {
  margin: 0 !important;
  padding: 7px 12px 7px 10px;
  border: 1px solid #d9dee8;
  border-radius: 999px;
  transition: all 0.3s ease;
  background: #ffffff;
  font-size: 14px;
}

.preference-tag :deep(.ant-checkbox-wrapper:hover) {
  border-color: #1677ff;
  background: #f0f6ff;
}

.preference-tag :deep(.ant-checkbox-wrapper-checked) {
  border-color: #1677ff;
  background: #eaf3ff;
  color: #0958d9;
}

.preference-tag :deep(.ant-checkbox + span) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.preference-icon {
  display: inline-flex;
  width: 18px;
  justify-content: center;
}

.submit-button {
  height: 52px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 700;
  background: #1677ff;
  border: none;
  box-shadow: 0 10px 22px rgba(22, 119, 255, 0.24);
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.submit-button :deep(.anticon) {
  margin-right: 8px;
}

.submit-button:hover {
  background: #0958d9 !important;
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(22, 119, 255, 0.3);
}

.submit-button:active {
  transform: translateY(0);
}

.loading-container {
  text-align: center;
  padding: 20px;
  border: 1px dashed #1677ff;
  border-radius: 8px;
  background: #f7fbff;
}

.loading-status {
  margin: 14px 0 0;
  color: #0958d9;
  font-size: 15px;
  font-weight: 650;
}

@media (max-width: 960px) {
  .top-banner {
    display: block;
    min-height: auto;
    padding: 28px 24px 52px;
  }

  .banner-summary {
    min-width: 0;
    margin-top: 22px;
  }
}

@media (max-width: 720px) {
  .home-container {
    padding: 16px 12px 32px;
  }

  .top-banner {
    margin-bottom: -18px;
    padding: 24px 18px 42px;
  }

  .top-banner h1 {
    font-size: 28px;
  }

  .form-card :deep(.ant-card-body) {
    padding: 20px;
  }

  .banner-summary {
    grid-template-columns: 1fr;
  }

  .form-card-header {
    flex-direction: column;
  }

  .header-status {
    justify-content: flex-start;
  }
}
</style>

<template>
  <div class="home-container">
    <div class="planner-page">
      <div class="top-banner">
        <div class="top-banner-content">
          <h1>下一站，想去哪里？</h1>
          <p>选一个城市，说说你的旅行偏好。一起把想去的地方，整理成每天都用得上的行程。</p>
        </div>
        <JourneySketch class="banner-illustration" />
      </div>

      <a-card class="form-card" :bordered="false">
        <div class="form-card-header">
          <div>
            <h2>写下你的旅行想法</h2>
            <p>日期、同伴和节奏，都由你决定。</p>
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
                <a-form-item name="city" :rules="[{ required: true, validator: validateCity }]" extra="当前支持单个城市，请勿只填写云南、四川等省份">
                  <template #label>
                    <span class="form-label">目的地城市</span>
                  </template>
                  <a-input
                    v-model:value="formData.city"
                    placeholder="例如：北京、昆明、丽江（选择一个）"
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
              <a-col :xs="{ span: 8 }">
                <a-form-item name="adults">
                  <template #label>
                    <span class="form-label">成人</span>
                  </template>
                  <a-input-number v-model:value="formData.party.adults" :min="0" :max="20" size="large" class="custom-input" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 8 }">
                <a-form-item name="children">
                  <template #label>
                    <span class="form-label">儿童</span>
                  </template>
                  <a-input-number v-model:value="formData.party.children" :min="0" :max="20" size="large" class="custom-input" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 8 }">
                <a-form-item name="elders">
                  <template #label>
                    <span class="form-label">老人</span>
                  </template>
                  <a-input-number v-model:value="formData.party.elders" :min="0" :max="20" size="large" class="custom-input" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="{ span: 24 }" :sm="{ span: 8 }">
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
              <a-col :xs="{ span: 24 }" :sm="{ span: 8 }">
                <a-form-item name="budget_amount">
                  <template #label>
                    <span class="form-label">总预算（元）</span>
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
              <a-col :xs="{ span: 24 }" :sm="{ span: 8 }">
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
              <a-col :xs="{ span: 24 }" :sm="{ span: 12 }">
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
              <a-col :xs="{ span: 24 }" :sm="{ span: 12 }">
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
              <a-col :span="24">
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
                        <span class="preference-icon" aria-hidden="true">{{ option.icon }}</span>
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
            <div class="submit-area">
            <p class="submit-note">提交后可实时查看进度，行程自动保存在历史记录。模型调用可能产生 API 费用。</p>
            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              size="large"
              class="submit-button"
            >
              <template v-if="!loading">
                <RocketOutlined />
                <span>开始规划行程</span>
              </template>
              <template v-else>
                <span>正在提交...</span>
              </template>
            </a-button>
            </div>
          </a-form-item>

          <a-form-item v-if="loading">
            <div class="loading-container">
              <a-spin />
              <p class="loading-status">
                {{ loadingStatus }}
              </p>
            </div>
          </a-form-item>
        </a-form>
        <a-alert v-if="quota" type="info" show-icon class="quota-note">
          <template #message>今日已创建 {{ quota.used }} / {{ quota.limit }} 次行程（北京时间每日重置）</template>
          <template #description><router-link v-if="quota.active_trip_id" :to="`/trips/${quota.active_trip_id}`">已有行程正在规划，点击查看进度</router-link><span v-else>模型调用可能产生供应商 API 费用；失败后可在历史行程中继续。</span></template>
        </a-alert>
        <a-alert v-if="quotaError" type="warning" show-icon :message="quotaError" class="quota-note" />
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  CarOutlined,
  EditOutlined,
  EnvironmentOutlined,
  RocketOutlined,
  TeamOutlined
} from '@ant-design/icons-vue'
import { createTrip } from '@/services/trips'
import { newIdempotencyKey } from '@/services/idempotency'
import { useTrips } from '@/stores/trips'
import api from '@/services/api'
import { validateCity } from '@/services/destination'
import JourneySketch from '@/components/JourneySketch.vue'
import type { TripFormData } from '@/types'
import type { Dayjs } from 'dayjs'

const router = useRouter()
const loading = ref(false)
const trips = useTrips()
let pendingBody = '', pendingKey = ''
const loadingStatus = ref('')
const quota = ref<{ used: number; limit: number; active_trip_id: string | null } | null>(null)
const quotaError = ref('')
onMounted(async () => {
  try { quota.value = (await api.get('/api/me/usage')).data }
  catch (e) { quotaError.value = (e as Error).message }
})

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
  loadingStatus.value = '正在提交，提交后可查看实时节点进度…'

  try {
    const budgetAmount = formData.budget_constraint.amount
    const budgetStrictness = budgetAmount === null || budgetAmount === undefined ? 'none' : 'soft'
    const requestData: TripFormData = {
      city: formData.city.trim(),
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

    const body = JSON.stringify(requestData)
    if (body !== pendingBody) { pendingBody = body; pendingKey = newIdempotencyKey() }
    const trip = await createTrip(requestData, pendingKey)
    trips.upsert(trip)
    await router.push(`/trips/${trip.id}`)
  } catch (error: any) {
    message.error(error.message || '生成旅行计划失败,请稍后重试')
  } finally {
    loading.value = false
    loadingStatus.value = ''
  }
}
</script>

<style scoped>
.home-container { padding: 0 36px 56px; width: 100%; }
.planner-page { max-width: 1120px; margin: 0 auto; }
.top-banner { display: flex; align-items: center; justify-content: space-between; gap: 32px; padding: 42px 0 32px; }
.top-banner-content { max-width: 580px; }
.top-banner h1 { margin: 0; font-family: var(--font-display); font-size: clamp(30px, 3.1vw, 44px); font-weight: 600; line-height: 1.45; letter-spacing: .015em; }
.top-banner p { margin: 14px 0 0; color: var(--color-muted); font-size: 15px; line-height: 1.9; max-width: 35em; }
.banner-illustration { width: 275px; flex: 0 0 29%; max-width: 320px; }
.form-card { border-radius: 18px; border: 1px solid var(--color-line); background: var(--color-surface); box-shadow: 0 4px 24px #203c3805; }
.form-card :deep(.ant-card-body) { padding: 32px 36px 20px; }
.form-card-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 28px; }
.form-card-header h2 { margin: 0; font-size: 21px; font-weight: 650; }
.form-card-header p { margin: 6px 0 0; font-size: 13px; color: var(--color-muted); }
.header-status { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
.header-status span { padding: 5px 10px; border-radius: 6px; background: var(--color-paper); color: var(--color-primary); font-size: 12px; }
.form-section { margin-bottom: 28px; padding-bottom: 8px; border-bottom: 1px solid var(--color-line); }
.form-section:last-of-type { border-bottom: none; margin-bottom: 8px; }
.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 22px; color: var(--color-primary); }
.section-header :deep(.anticon) { display: grid; place-items: center; width: 30px; height: 30px; background: #edf3ed; border-radius: 8px; font-size: 16px; }
.section-title { font-size: 15px; font-weight: 650; color: var(--color-ink); }
.form-label { color: var(--color-muted); font-size: 13px; }
.custom-checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; width: 100%; }
.preference-tag { margin: 0; padding: 9px 12px; border: 1px solid var(--color-line); border-radius: 8px; background: var(--color-surface); font-size: 13px; transition: background-color .15s, border-color .15s; }
.preference-tag:hover { border-color: var(--color-primary); }
.preference-tag.ant-checkbox-wrapper-checked { background: #edf5e9; border-color: #8eac91; color: var(--color-primary); }
.preference-tag :deep(.ant-checkbox + span) { display: inline-flex; align-items: center; gap: 5px; padding-right: 0; }
.preference-icon { display: inline-flex; width: 19px; justify-content: center; font-size: 15px; }
.submit-area { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding-top: 4px; }
.submit-note { max-width: 32em; color: var(--color-muted); font-size: 12px; line-height: 1.8; margin: 0; }
.submit-button { height: 48px; min-width: 200px; border-radius: 10px; font-size: 15px; }
.quota-note { margin-top: 22px; }
.loading-container { text-align: center; padding: 16px; border-radius: 10px; background: var(--color-paper); }
.loading-status { margin: 12px 0 0; color: var(--color-primary); font-size: 14px; }
@media (max-width: 1100px) {
  .home-container { padding: 0 24px 40px; }
  .top-banner { gap: 12px; padding-top: 28px; }
  .form-card :deep(.ant-card-body) { padding: 28px; }
}
@media (max-width: 600px) {
  .home-container { padding: 0 16px 32px; }
  .top-banner { padding: 28px 2px; }
  .top-banner h1 { font-size: 30px; }
  .top-banner p { font-size: 14px; }
  .banner-illustration { display: none; }
  .form-card { border-radius: 14px; }
  .form-card :deep(.ant-card-body) { padding: 22px 18px 12px; }
  .form-card-header { align-items: flex-start; gap: 12px; }
  .form-card-header h2 { font-size: 19px; }
  .header-status { max-width: 116px; gap: 5px; }
  .header-status span { padding: 4px 7px; }
  .form-section { margin-bottom: 22px; }
  .preference-tag { padding: 8px 10px; }
  .custom-checkbox-group { gap: 8px; }
  .submit-area { flex-direction: column; align-items: stretch; gap: 14px; }
  .submit-button { width: 100%; }
}
</style>

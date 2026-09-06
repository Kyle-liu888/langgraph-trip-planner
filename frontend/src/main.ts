import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './styles/theme.css'
import App from './App.vue'
import { createPinia } from 'pinia'
import { useAuth } from './stores/auth'

const pinia = createPinia()

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/trips/new'
    },
    {
      path: '/trips/new', component: () => import('./views/Home.vue')
    },
    { path: '/trips/:id', component: () => import('./views/TripDetail.vue') },
    { path: '/login', component: () => import('./views/Login.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/trips/new' }
  ]
})

const app = createApp(App)

app.use(pinia)
router.beforeEach(async (to) => {
  const auth = useAuth(pinia)
  await auth.init()
  if (to.path.startsWith('/trips/') && !auth.user)
    return { path: '/login', query: { redirect: to.fullPath } }
})
app.use(router)
app.use(Antd)

app.mount('#app')

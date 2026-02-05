import { createRouter, createWebHistory } from 'vue-router'
import IndexPage from 'pages/IndexPage.vue'
import ResumePage from 'pages/ResumePage.vue'

const routes = [
  {
    path: '/',
    component: IndexPage
  },
  {
    path: '/resume',
    component: ResumePage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

import axios from 'axios'
import { boot } from 'quasar/wrappers'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  timeout: 60000
})

export default boot(({ app }) => {
  app.config.globalProperties.$api = api
})

export { api }

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/AuthLayout.vue'),
      children: [
        { path: '', redirect: '/login' },
        {
          path: 'login',
          name: 'Login',
          component: () => import('@/views/LoginView.vue'),
          meta: { title: '登录', guest: true },
        },
        {
          path: 'register',
          name: 'Register',
          component: () => import('@/views/RegisterView.vue'),
          meta: { title: '注册', guest: true },
        },
      ],
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '仪表盘' },
        },
        {
          path: 'my-resumes',
          name: 'MyResumes',
          component: () => import('@/views/MyResumesView.vue'),
          meta: { title: '我的简历' },
        },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          name: 'AdminDashboard',
          component: () => import('@/views/AdminDashboardView.vue'),
          meta: { title: '管理面板' },
        },
        {
          path: 'resumes',
          name: 'AdminResumes',
          component: () => import('@/views/AdminResumesView.vue'),
          meta: { title: '简历管理' },
        },
        {
          path: 'jobs',
          name: 'AdminJobs',
          component: () => import('@/views/AdminJobsView.vue'),
          meta: { title: '岗位管理' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/login',
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  const userRaw = localStorage.getItem('user')
  let user: { role?: string } | null = null

  try {
    user = userRaw ? JSON.parse(userRaw) : null
  } catch {
    user = null
  }

  const isAuthenticated = !!token && !!user

  if (to.meta.guest && isAuthenticated) {
    if (user?.role === 'admin') return next('/admin')
    return next('/dashboard')
  }

  if (to.meta.requiresAuth && !isAuthenticated) return next('/login')

  if (to.meta.requiresAdmin && user?.role !== 'admin') return next('/dashboard')

  next()
})

export default router

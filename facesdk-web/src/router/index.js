import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import HomeView from '@/views/HomeView.vue'
import DetectView from '@/views/DetectView.vue'
import CompareView from '@/views/CompareView.vue'
import SearchView from '@/views/SearchView.vue'
import SubjectsView from '@/views/SubjectsView.vue'
import SettingsView from '@/views/SettingsView.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: HomeView
      },
      {
        path: 'detect',
        name: 'detect',
        component: DetectView
      },
      {
        path: 'compare',
        name: 'compare',
        component: CompareView
      },
      {
        path: 'search',
        name: 'search',
        component: SearchView
      },
      {
        path: 'subjects',
        name: 'subjects',
        component: SubjectsView
      },
      {
        path: 'settings',
        name: 'settings',
        component: SettingsView
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

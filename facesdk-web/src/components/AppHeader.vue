<template>
  <el-header class="app-header">
    <div class="logo">
      <el-icon size="28"><Monitor /></el-icon>
      <span class="title">FaceSDK</span>
    </div>
    <div class="nav-menu">
      <el-menu
        :default-active="$route.path"
        mode="horizontal"
        router
        background-color="#409EFF"
        text-color="#fff"
        active-text-color="#ffd04b"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>{{ $t('nav.home') }}</span>
        </el-menu-item>
        <el-menu-item index="/detect">
          <el-icon><Camera /></el-icon>
          <span>{{ $t('nav.detect') }}</span>
        </el-menu-item>
        <el-menu-item index="/compare">
          <el-icon><CopyDocument /></el-icon>
          <span>{{ $t('nav.compare') }}</span>
        </el-menu-item>
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <span>{{ $t('nav.search') }}</span>
        </el-menu-item>
        <el-menu-item index="/subjects">
          <el-icon><UserFilled /></el-icon>
          <span>{{ $t('nav.subjects') }}</span>
        </el-menu-item>
        <el-menu-item index="/api">
          <el-icon><Document /></el-icon>
          <span>{{ $t('nav.api') }}</span>
        </el-menu-item>
      </el-menu>
    </div>
    <div class="actions">
      <el-dropdown @command="handleLanguageChange">
        <el-button type="primary" plain>
          <el-icon><Switch /></el-icon>
          {{ $t(`language.${currentLocale}`) }}
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="zh">{{ $t('language.zh') }}</el-dropdown-item>
            <el-dropdown-item command="en">{{ $t('language.en') }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button type="primary" plain @click="$router.push('/settings')">
        <el-icon><Setting /></el-icon>
      </el-button>
    </div>
  </el-header>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import {
  Monitor,
  HomeFilled,
  Camera,
  CopyDocument,
  Search,
  UserFilled,
  Switch,
  Setting,
  ArrowDown,
  Document
} from '@element-plus/icons-vue'

const { locale } = useI18n()
const $route = useRoute()

const currentLocale = computed(() => locale.value)

const handleLanguageChange = (lang) => {
  locale.value = lang
  localStorage.setItem('locale', lang)
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #409EFF;
  padding: 0 20px;
  height: 60px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
}

.logo .title {
  font-size: 20px;
  font-weight: bold;
}

.nav-menu {
  flex: 1;
  margin: 0 20px;
}

.nav-menu .el-menu {
  border-bottom: none;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>

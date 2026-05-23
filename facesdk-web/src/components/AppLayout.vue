<template>
  <el-container class="app-layout">
    <AppHeader />
    <el-main class="main-content">
      <router-view />
    </el-main>
    <el-footer class="app-footer">
      <p>FaceSDK Web Management © 2026</p>
    </el-footer>
  </el-container>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
}

.app-footer {
  text-align: center;
  color: #909399;
  padding: 20px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}
</style>

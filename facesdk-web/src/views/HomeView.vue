<template>
  <div class="home-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <span class="title">FaceSDK {{ $t('nav.home') }}</span>
            </div>
          </template>
          <div class="welcome-content">
            <el-icon size="64" color="#409EFF"><Monitor /></el-icon>
            <h2>{{ $t('nav.home') }}</h2>
            <p>{{ $t('detect.description') }}</p>
            <el-row :gutter="20" class="feature-cards">
              <el-col :xs="24" :sm="12" :md="8" :lg="6">
                <el-card class="feature-card" @click="$router.push('/detect')">
                  <el-icon size="48" color="#67C23A"><Camera /></el-icon>
                  <h3>{{ $t('nav.detect') }}</h3>
                  <p>{{ $t('detect.description') }}</p>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="12" :md="8" :lg="6">
                <el-card class="feature-card" @click="$router.push('/compare')">
                  <el-icon size="48" color="#E6A23C"><CopyDocument /></el-icon>
                  <h3>{{ $t('nav.compare') }}</h3>
                  <p>{{ $t('compare.description') }}</p>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="12" :md="8" :lg="6">
                <el-card class="feature-card" @click="$router.push('/search')">
                  <el-icon size="48" color="#F56C6C"><Search /></el-icon>
                  <h3>{{ $t('nav.search') }}</h3>
                  <p>{{ $t('search.description') }}</p>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="12" :md="8" :lg="6">
                <el-card class="feature-card" @click="$router.push('/subjects')">
                  <el-icon size="48" color="#909399"><UserFilled /></el-icon>
                  <h3>{{ $t('nav.subjects') }}</h3>
                  <p>{{ $t('subjects.description') }}</p>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { Monitor, Camera, CopyDocument, Search, UserFilled } from '@element-plus/icons-vue'
</script>

<style scoped>
.home-view {
  max-width: 1200px;
  margin: 0 auto;
}

.welcome-card {
  text-align: center;
}

.welcome-content {
  padding: 40px 20px;
}

.welcome-content h2 {
  margin: 20px 0;
  color: #303133;
}

.feature-cards {
  margin-top: 40px;
}

.feature-card {
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.feature-card h3 {
  margin: 15px 0 10px;
  color: #303133;
}

.feature-card p {
  color: #606266;
  font-size: 14px;
}
</style>

<template>
  <div class="detect-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('detect.title') }}</span>
          <el-button type="primary" @click="handleDetect" :loading="loading" :disabled="!imageFile">
            {{ $t('common.submit') }}
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="24" :md="12">
          <div class="upload-section">
            <h3>{{ $t('detect.uploadImage') }}</h3>
            <el-upload
              class="image-uploader"
              action="#"
              :auto-upload="false"
              :on-change="handleImageChange"
              :show-file-list="false"
              accept="image/jpeg,image/png"
            >
              <img v-if="imageUrl" :src="imageUrl" class="preview-image" />
              <div v-else class="upload-placeholder">
                <el-icon size="48"><Plus /></el-icon>
                <div class="el-upload__text">
                  {{ $t('common.dragUpload') }}
                </div>
                <div class="el-upload__tip">
                  {{ $t('common.supportedFormats') }}
                </div>
              </div>
            </el-upload>
          </div>
        </el-col>
        
        <el-col :xs="24" :md="12">
          <div class="result-section" v-if="result">
            <h3>{{ $t('detect.detectResult') }}</h3>
            <el-alert
              :title="$t('detect.faceCount', { count: result.face_count })"
              :type="result.face_count > 0 ? 'success' : 'warning'"
              show-icon
            />
            
            <div v-if="result.faces && result.faces.length > 0" class="faces-list">
              <el-card v-for="(face, index) in result.faces" :key="index" class="face-card">
                <template #header>
                  <span>{{ $t('detect.faceInfo') }} #{{ index + 1 }}</span>
                </template>
                <el-descriptions :column="1" border>
                  <el-descriptions-item :label="$t('detect.confidence')">
                    {{ (face.confidence * 100).toFixed(2) }}%
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('detect.boundingBox')">
                    x: {{ face.box?.x_min }}, y: {{ face.box?.y_min }}, 
                    w: {{ face.box?.x_max - face.box?.x_min }}, 
                    h: {{ face.box?.y_max - face.box?.y_min }}
                  </el-descriptions-item>
                  <el-descriptions-item v-if="face.quality" :label="$t('detect.quality')">
                    <el-tag v-if="face.quality.score > 0.8" type="success">High</el-tag>
                    <el-tag v-else-if="face.quality.score > 0.5" type="warning">Medium</el-tag>
                    <el-tag v-else type="danger">Low</el-tag>
                    ({{ (face.quality.score * 100).toFixed(1) }}%)
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </div>
          </div>
          <el-empty v-else :description="$t('common.noData')" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { detectFace } from '@/api/face'

const imageFile = ref(null)
const imageUrl = ref('')
const loading = ref(false)
const result = ref(null)

const handleImageChange = (file) => {
  imageFile.value = file.raw
  imageUrl.value = URL.createObjectURL(file.raw)
}

const handleDetect = async () => {
  if (!imageFile.value) {
    ElMessage.warning('Please upload an image first')
    return
  }
  
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', imageFile.value)
    
    const res = await detectFace(formData)
    result.value = res
    ElMessage.success('Detection completed')
  } catch (error) {
    ElMessage.error(error.message || 'Detection failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.detect-view {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-section, .result-section {
  padding: 20px;
}

.image-uploader {
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color 0.3s;
}

.image-uploader:hover {
  border-color: #409EFF;
}

.upload-placeholder {
  height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #8c939d;
}

.preview-image {
  width: 100%;
  height: 300px;
  object-fit: contain;
}

.faces-list {
  margin-top: 20px;
}

.face-card {
  margin-bottom: 15px;
}
</style>

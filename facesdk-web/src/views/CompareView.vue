<template>
  <div class="compare-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('compare.title') }}</span>
          <el-button 
            type="primary" 
            @click="handleCompare" 
            :loading="loading"
            :disabled="!image1 || !image2"
          >
            {{ $t('compare.compareBtn') }}
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="24" :md="8">
          <div class="upload-section">
            <h3>{{ $t('compare.uploadFirst') }}</h3>
            <el-upload
              class="image-uploader"
              action="#"
              :auto-upload="false"
              :on-change="(file) => handleImageChange(file, 1)"
              :show-file-list="false"
              accept="image/jpeg,image/png"
            >
              <img v-if="imageUrl1" :src="imageUrl1" class="preview-image" />
              <div v-else class="upload-placeholder">
                <el-icon size="36"><Plus /></el-icon>
                <div class="el-upload__text">{{ $t('common.dragUpload') }}</div>
              </div>
            </el-upload>
          </div>
        </el-col>
        
        <el-col :xs="24" :md="8">
          <div class="upload-section">
            <h3>{{ $t('compare.uploadSecond') }}</h3>
            <el-upload
              class="image-uploader"
              action="#"
              :auto-upload="false"
              :on-change="(file) => handleImageChange(file, 2)"
              :show-file-list="false"
              accept="image/jpeg,image/png"
            >
              <img v-if="imageUrl2" :src="imageUrl2" class="preview-image" />
              <div v-else class="upload-placeholder">
                <el-icon size="36"><Plus /></el-icon>
                <div class="el-upload__text">{{ $t('common.dragUpload') }}</div>
              </div>
            </el-upload>
          </div>
        </el-col>
        
        <el-col :xs="24" :md="8">
          <div class="result-section" v-if="result">
            <h3>{{ $t('compare.result') }}</h3>
            <el-result
              :icon="isMatch ? 'success' : 'warning'"
              :title="isMatch ? $t('compare.yes') : $t('compare.no')"
            />
            <el-descriptions :column="1" border>
              <el-descriptions-item :label="$t('compare.similarity')">
                <el-progress 
                  :percentage="Number((similarity * 100).toFixed(2))" 
                  :color="isMatch ? '#67C23A' : '#E6A23C'"
                />
                <span style="margin-left: 10px">{{ (similarity * 100).toFixed(2) }}%</span>
              </el-descriptions-item>
            </el-descriptions>
          </div>
          <el-empty v-else :description="$t('common.noData')" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { compareFaces } from '@/api/face'

const image1 = ref(null)
const image2 = ref(null)
const imageUrl1 = ref('')
const imageUrl2 = ref('')
const loading = ref(false)
const result = ref(null)

// CompreFace Verification API 返回结果解析
const similarity = computed(() => {
  // API 返回 { result: [...] }，需要取 result.result
  const resultArray = result.value?.result || result.value
  console.log('Result array:', JSON.stringify(resultArray))
  if (!resultArray || !Array.isArray(resultArray) || resultArray.length === 0) {
    return 0
  }
  const firstResult = resultArray[0]
  if (firstResult.face_matches && firstResult.face_matches.length > 0) {
    return firstResult.face_matches[0].similarity || 0
  }
  return 0
})

const isMatch = computed(() => {
  // 相似度大于 0.5 认为是同一个人
  return similarity.value > 0.5
})

const handleImageChange = (file, index) => {
  if (index === 1) {
    image1.value = file.raw
    imageUrl1.value = URL.createObjectURL(file.raw)
  } else {
    image2.value = file.raw
    imageUrl2.value = URL.createObjectURL(file.raw)
  }
}

const handleCompare = async () => {
  if (!image1.value || !image2.value) {
    ElMessage.warning('Please upload both images')
    return
  }
  
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('source_image', image1.value)
    formData.append('target_image', image2.value)
    
    const res = await compareFaces(formData)
    result.value = res
    ElMessage.success('Comparison completed')
  } catch (error) {
    ElMessage.error(error.message || 'Comparison failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.compare-view {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-section, .result-section {
  padding: 15px;
}

.image-uploader {
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.3s;
}

.image-uploader:hover {
  border-color: #409EFF;
}

.upload-placeholder {
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #8c939d;
}

.preview-image {
  width: 100%;
  height: 200px;
  object-fit: contain;
}
</style>

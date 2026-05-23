<template>
  <div class="search-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('search.title') }}</span>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="24" :md="8">
          <div class="upload-section">
            <h3>{{ $t('search.uploadImage') }}</h3>
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
                <el-icon size="36"><Plus /></el-icon>
                <div class="el-upload__text">{{ $t('common.dragUpload') }}</div>
              </div>
            </el-upload>
            
            <el-form :model="form" label-position="top" class="search-form">
              <el-form-item :label="$t('search.limit')">
                <el-slider v-model="form.limit" :min="1" :max="10" show-stops />
              </el-form-item>
              <el-form-item :label="$t('search.threshold')">
                <el-slider v-model="form.threshold" :min="0" :max="1" :step="0.1" />
              </el-form-item>
              <el-form-item>
                <el-button 
                  type="primary" 
                  @click="handleSearch" 
                  :loading="loading"
                  :disabled="!imageFile"
                  style="width: 100%"
                >
                  {{ $t('search.searchBtn') }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-col>
        
        <el-col :xs="24" :md="16">
          <div class="result-section">
            <h3>{{ $t('search.results') }}</h3>
            <div v-if="results.length > 0">
              <el-table :data="results" style="width: 100%">
                <el-table-column type="index" width="50" />
                <el-table-column :label="$t('search.subjectId')" prop="subject" />
                <el-table-column :label="$t('search.similarity')">
                  <template #default="{ row }">
                    <el-progress 
                      :percentage="(row.similarity * 100).toFixed(2)"
                      :color="row.is_match ? '#67C23A' : '#E6A23C'"
                    />
                  </template>
                </el-table-column>
                <el-table-column :label="$t('compare.match')" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.is_match ? 'success' : 'info'">
                      {{ row.is_match ? $t('compare.yes') : $t('compare.no') }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else :description="$t('search.noMatch')" />
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { searchFace } from '@/api/face'

const imageFile = ref(null)
const imageUrl = ref('')
const loading = ref(false)
const results = ref([])

const form = reactive({
  limit: 5,
  threshold: 0.5
})

const handleImageChange = (file) => {
  imageFile.value = file.raw
  imageUrl.value = URL.createObjectURL(file.raw)
}

const handleSearch = async () => {
  if (!imageFile.value) {
    ElMessage.warning('Please upload an image first')
    return
  }
  
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', imageFile.value)
    formData.append('limit', form.limit)
    formData.append('threshold', form.threshold)
    
    const res = await searchFace(formData)
    results.value = res.results || []
    ElMessage.success(`Found ${results.value.length} matches`)
  } catch (error) {
    ElMessage.error(error.message || 'Search failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.search-view {
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
  margin-bottom: 20px;
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

.search-form {
  margin-top: 20px;
}
</style>

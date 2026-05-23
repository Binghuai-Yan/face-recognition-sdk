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
        <el-col :xs="24" :md="8">
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
        
        <el-col :xs="24" :md="8">
          <div class="config-section">
            <h3>{{ $t('detect.configTitle') }}</h3>
            <el-form :model="form" label-position="top">
              <el-form-item :label="$t('detect.detThreshold')">
                <el-slider v-model="form.detThreshold" :min="0" :max="1" :step="0.05" show-stops />
                <div class="threshold-hint">{{ form.detThreshold }}</div>
              </el-form-item>
              
              <el-divider>{{ $t('detect.extraFeatures') }}</el-divider>
              
              <el-form-item>
                <el-checkbox v-model="form.age">{{ $t('detect.age') }}</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="form.gender">{{ $t('detect.gender') }}</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="form.pose">{{ $t('detect.pose') }}</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="form.landmarks">{{ $t('detect.landmarks') }}</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="form.quality">{{ $t('detect.qualityCheck') }}</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="form.liveness">{{ $t('detect.liveness') }}</el-checkbox>
              </el-form-item>
            </el-form>
            
            <el-alert
              :title="$t('detect.thresholdHint')"
              type="info"
              :closable="false"
              show-icon
              style="margin-top: 15px"
            />
          </div>
        </el-col>
        
        <el-col :xs="24" :md="8">
          <div class="result-section" v-if="result">
            <h3>{{ $t('detect.detectResult') }}</h3>
            <el-alert
              :title="$t('detect.faceCount', { count: faceCount })"
              :type="faceCount > 0 ? 'success' : 'warning'"
              show-icon
            />
            
            <div v-if="faceCount > 0" class="faces-list">
              <el-card v-for="(face, index) in faces" :key="index" class="face-card">
                <template #header>
                  <span>{{ $t('detect.faceInfo') }} #{{ index + 1 }}</span>
                </template>
                <el-descriptions :column="1" border>
                  <el-descriptions-item :label="$t('detect.confidence')">
                    {{ ((face.box?.probability || face.probability || face.confidence || 0) * 100).toFixed(2) }}%
                  </el-descriptions-item>
                  <el-descriptions-item v-if="face.age" :label="$t('detect.age')">
                    {{ face.age.low }} - {{ face.age.high }} {{ $t('detect.years') }}
                  </el-descriptions-item>
                  <el-descriptions-item v-if="face.gender" :label="$t('detect.gender')">
                    {{ face.gender.value === 'male' ? $t('detect.male') : $t('detect.female') }}
                    ({{ (face.gender.probability * 100).toFixed(1) }}%)
                  </el-descriptions-item>
                  <el-descriptions-item v-if="face.pose" :label="$t('detect.pose')">
                    <div>Pitch: {{ face.pose.pitch?.toFixed(2) }}</div>
                    <div>Roll: {{ face.pose.roll?.toFixed(2) }}</div>
                    <div>Yaw: {{ face.pose.yaw?.toFixed(2) }}</div>
                  </el-descriptions-item>
                  <el-descriptions-item v-if="face.quality" :label="$t('detect.quality')">
                    <el-tag v-if="face.quality.score > 0.8" type="success">High</el-tag>
                    <el-tag v-else-if="face.quality.score > 0.5" type="warning">Medium</el-tag>
                    <el-tag v-else type="danger">Low</el-tag>
                    ({{ ((face.quality.score || 0) * 100).toFixed(1) }}%)
                  </el-descriptions-item>
                  <el-descriptions-item v-if="face.liveness" :label="$t('detect.liveness')">
                    <el-tag :type="face.liveness.value === 'live' ? 'success' : 'danger'">
                      {{ face.liveness.value === 'live' ? $t('detect.live') : $t('detect.spoof') }}
                    </el-tag>
                    ({{ (face.liveness.probability * 100).toFixed(1) }}%)
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('detect.boundingBox')">
                    x: {{ face.box?.x_min }}, y: {{ face.box?.y_min }}, 
                    w: {{ face.box?.x_max - face.box?.x_min }}, 
                    h: {{ face.box?.y_max - face.box?.y_min }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </div>

            <!-- 活体检测结果 -->
            <el-card v-if="livenessResult" class="liveness-card" style="margin-top: 20px">
              <template #header>
                <span>{{ $t('detect.liveness') }}</span>
              </template>
              <template v-if="livenessResult.error">
                <el-alert :title="livenessResult.message" type="error" show-icon />
              </template>
              <template v-else>
                <el-descriptions :column="1" border>
                  <el-descriptions-item :label="$t('detect.liveness')">
                    <el-tag 
                      :type="getLivenessTag(livenessResult)" 
                      size="large"
                    >
                      {{ getLivenessText(livenessResult) }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item v-if="livenessResult.result" label="Score">
                    {{ ((livenessResult.result || 0) * 100).toFixed(1) }}%
                  </el-descriptions-item>
                </el-descriptions>
                <el-alert
                  :title="$t('detect.livenessHint')"
                  type="info"
                  :closable="false"
                  show-icon
                  style="margin-top: 10px"
                />
              </template>
            </el-card>
          </div>
          <el-empty v-else :description="$t('common.noData')" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { detectFace, checkLiveness } from '@/api/face'

const { t: $t } = useI18n()

const imageFile = ref(null)
const imageUrl = ref('')
const loading = ref(false)
const result = ref(null)
const livenessResult = ref(null)

const form = reactive({
  detThreshold: 0.5,
  age: true,
  gender: true,
  pose: true,
  landmarks: false,
  quality: true,
  liveness: false
})

const faceCount = computed(() => {
  if (!result.value) return 0
  // CompreFace 返回 { result: [{ box, ... }] }
  const resultArray = result.value.result || result.value.faces || []
  return resultArray.length
})

const faces = computed(() => {
  if (!result.value) return []
  const resultArray = result.value.result || result.value.faces || []
  return resultArray
})

const handleImageChange = (file) => {
  imageFile.value = file.raw
  imageUrl.value = URL.createObjectURL(file.raw)
}

// 活体检测结果解析
const getLivenessTag = (res) => {
  // CompreFace Anti-spoofing: result > 0.5 为活体
  const score = res.result || 0
  return score > 0.5 ? 'success' : 'danger'
}

const getLivenessText = (res) => {
  const score = res.result || 0
  if (score > 0.5) {
    return `${$t('detect.live')} (${(score * 100).toFixed(1)}%)`
  }
  return `${$t('detect.spoof')} (${(score * 100).toFixed(1)}%)`
}

const handleDetect = async () => {
  if (!imageFile.value) {
    ElMessage.warning('Please upload an image first')
    return
  }

  loading.value = true
  livenessResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', imageFile.value)
    formData.append('det_prob_threshold', form.detThreshold)

    // 根据勾选的选项添加 face_plugins 参数
    const plugins = []
    if (form.age) plugins.push('age')
    if (form.gender) plugins.push('gender')
    if (form.pose) plugins.push('pose')
    if (form.landmarks) plugins.push('landmarks')
    if (form.quality) plugins.push('quality')

    const res = await detectFace(formData, plugins)
    result.value = res

    // 如果勾选了活体检测，调用 Anti-spoofing API
    if (form.liveness) {
      try {
        const livenessFormData = new FormData()
        livenessFormData.append('file', imageFile.value)
        const livenessRes = await checkLiveness(livenessFormData)
        livenessResult.value = livenessRes
      } catch (livenessError) {
        console.error('Liveness check error:', livenessError)
        livenessResult.value = { error: true, message: livenessError.response?.data?.message || 'Liveness check failed' }
      }
    }

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
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-section, .config-section, .result-section {
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

.threshold-hint {
  text-align: center;
  color: #409EFF;
  font-weight: bold;
}

.faces-list {
  margin-top: 20px;
  max-height: 500px;
  overflow-y: auto;
}

.face-card {
  margin-bottom: 15px;
}
</style>

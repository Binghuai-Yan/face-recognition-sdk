<template>
  <div class="api-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('api.title') }}</span>
        </div>
      </template>

      <el-alert
        :title="$t('api.intro')"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      />

      <!-- Detection API -->
      <el-collapse v-model="activeNames">
        <el-collapse-item name="detection">
          <template #title>
            <div class="api-title">
              <el-tag type="success">POST</el-tag>
              <span class="api-path">/api/v1/detection/detect</span>
              <span class="api-desc">{{ $t('api.detection.desc') }}</span>
            </div>
          </template>

          <div class="api-content">
            <h4>{{ $t('api.headers') }}</h4>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="x-api-key">{{ $t('api.detection.apiKey') }}</el-descriptions-item>
              <el-descriptions-item label="Content-Type">multipart/form-data</el-descriptions-item>
            </el-descriptions>

            <h4>{{ $t('api.params') }}</h4>
            <el-table :data="detectionParams" border>
              <el-table-column prop="name" :label="$t('api.paramName')" width="150" />
              <el-table-column prop="type" :label="$t('api.paramType')" width="100" />
              <el-table-column prop="required" :label="$t('api.required')" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.required ? 'danger' : 'info'">
                    {{ row.required ? $t('api.yes') : $t('api.no') }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="$t('api.description')" />
            </el-table>

            <h4>{{ $t('api.example') }}</h4>
            <pre class="code-block"><code>curl -X POST "{{ baseUrl }}/api/v1/detection/detect?det_prob_threshold=0.5" \
  -H "x-api-key: {{ $t('api.yourApiKey') }}" \
  -F "file=@image.jpg"</code></pre>

            <h4>{{ $t('api.response') }}</h4>
            <pre class="code-block"><code>{
  "result": [{
    "box": {
      "probability": 0.9999,
      "x_max": 1156,
      "y_max": 1332,
      "x_min": 87,
      "y_min": 93
    }
  }]
}</code></pre>
          </div>
        </el-collapse-item>

        <!-- Verification API -->
        <el-collapse-item name="verification">
          <template #title>
            <div class="api-title">
              <el-tag type="success">POST</el-tag>
              <span class="api-path">/api/v1/verification/verify</span>
              <span class="api-desc">{{ $t('api.verification.desc') }}</span>
            </div>
          </template>

          <div class="api-content">
            <h4>{{ $t('api.headers') }}</h4>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="x-api-key">{{ $t('api.verification.apiKey') }}</el-descriptions-item>
              <el-descriptions-item label="Content-Type">multipart/form-data</el-descriptions-item>
            </el-descriptions>

            <h4>{{ $t('api.params') }}</h4>
            <el-table :data="verificationParams" border>
              <el-table-column prop="name" :label="$t('api.paramName')" width="150" />
              <el-table-column prop="type" :label="$t('api.paramType')" width="100" />
              <el-table-column prop="required" :label="$t('api.required')" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.required ? 'danger' : 'info'">
                    {{ row.required ? $t('api.yes') : $t('api.no') }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="$t('api.description')" />
            </el-table>

            <h4>{{ $t('api.example') }}</h4>
            <pre class="code-block"><code>curl -X POST "{{ baseUrl }}/api/v1/verification/verify" \
  -H "x-api-key: {{ $t('api.yourApiKey') }}" \
  -F "source_image=@face1.jpg" \
  -F "target_image=@face2.jpg"</code></pre>

            <h4>{{ $t('api.response') }}</h4>
            <pre class="code-block"><code>{
  "result": [{
    "source_image_face": { "box": {...} },
    "face_matches": [{
      "box": {...},
      "similarity": 0.99938
    }]
  }]
}</code></pre>
          </div>
        </el-collapse-item>

        <!-- Recognition API -->
        <el-collapse-item name="recognition">
          <template #title>
            <div class="api-title">
              <el-tag type="success">POST</el-tag>
              <span class="api-path">/api/v1/recognition/recognize</span>
              <span class="api-desc">{{ $t('api.recognition.desc') }}</span>
            </div>
          </template>

          <div class="api-content">
            <h4>{{ $t('api.headers') }}</h4>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="x-api-key">{{ $t('api.recognition.apiKey') }}</el-descriptions-item>
              <el-descriptions-item label="Content-Type">multipart/form-data</el-descriptions-item>
            </el-descriptions>

            <h4>{{ $t('api.params') }}</h4>
            <el-table :data="recognitionParams" border>
              <el-table-column prop="name" :label="$t('api.paramName')" width="150" />
              <el-table-column prop="type" :label="$t('api.paramType')" width="100" />
              <el-table-column prop="required" :label="$t('api.required')" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.required ? 'danger' : 'info'">
                    {{ row.required ? $t('api.yes') : $t('api.no') }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="$t('api.description')" />
            </el-table>

            <h4>{{ $t('api.example') }}</h4>
            <pre class="code-block"><code>curl -X POST "{{ baseUrl }}/api/v1/recognition/recognize?prediction_count=5" \
  -H "x-api-key: {{ $t('api.yourApiKey') }}" \
  -F "file=@image.jpg"</code></pre>
          </div>
        </el-collapse-item>

      </el-collapse>

      <!-- Threshold Reference -->
      <el-card style="margin-top: 20px">
        <template #header>
          <span>{{ $t('api.thresholdTitle') }}</span>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item :label="$t('api.detectionThreshold')">0.5</el-descriptions-item>
          <el-descriptions-item :label="$t('api.compareThreshold1')">0.80 ({{ $t('api.compareHint1') }})</el-descriptions-item>
          <el-descriptions-item :label="$t('api.compareThreshold2')">0.82 ({{ $t('api.compareHint2') }})</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const activeNames = ref(['detection'])

const baseUrl = computed(() => {
  return window.location.origin
})

const detectionParams = computed(() => [
  { name: 'file', type: 'File', required: true, desc: t('api.detection.paramFile') },
  { name: 'det_prob_threshold', type: 'Float', required: false, desc: t('api.detection.paramThreshold') },
  { name: 'face_plugins', type: 'String', required: false, desc: t('api.detection.paramPlugins') }
])

const verificationParams = computed(() => [
  { name: 'source_image', type: 'File', required: true, desc: t('api.verification.paramSource') },
  { name: 'target_image', type: 'File', required: true, desc: t('api.verification.paramTarget') }
])

const recognitionParams = computed(() => [
  { name: 'file', type: 'File', required: true, desc: t('api.recognition.paramFile') },
  { name: 'prediction_count', type: 'Integer', required: false, desc: t('api.recognition.paramLimit') }
])

</script>

<style scoped>
.api-view {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  font-weight: bold;
}

.api-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.api-path {
  font-family: monospace;
  font-weight: bold;
  color: #409EFF;
}

.api-desc {
  color: #606266;
  margin-left: 10px;
}

.api-content {
  padding: 10px 0;
}

.api-content h4 {
  margin: 20px 0 10px 0;
  color: #303133;
}

.code-block {
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 15px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.code-block code {
  color: #303133;
}
</style>

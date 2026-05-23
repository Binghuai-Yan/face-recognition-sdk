<template>
  <div class="settings-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('settings.title') }}</span>
        </div>
      </template>
      
      <el-form :model="form" label-position="top" style="max-width: 600px">
        <el-divider>{{ $t('settings.language') }}</el-divider>
        
        <el-form-item :label="$t('settings.language')">
          <el-radio-group v-model="form.language" @change="handleLanguageChange">
            <el-radio-button label="zh">{{ $t('language.zh') }}</el-radio-button>
            <el-radio-button label="en">{{ $t('language.en') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <el-divider>{{ $t('settings.apiConfig') }}</el-divider>
        
        <el-alert
          :title="$t('settings.apiKeyHint')"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        />
        
        <el-form-item label="Detection API Key">
          <el-input 
            v-model="form.detectionApiKey" 
            type="password" 
            show-password
            placeholder="Detection 服务 API Key"
          />
        </el-form-item>
        
        <el-form-item label="Recognition API Key">
          <el-input 
            v-model="form.recognitionApiKey" 
            type="password" 
            show-password
            placeholder="Recognition 服务 API Key"
          />
        </el-form-item>
        
        <el-form-item label="Verification API Key">
          <el-input 
            v-model="form.verificationApiKey" 
            type="password" 
            show-password
            placeholder="Verification 服务 API Key"
          />
        </el-form-item>
        
        <el-form-item label="Anti-spoofing API Key">
          <el-input 
            v-model="form.antispoofingApiKey" 
            type="password" 
            show-password
            placeholder="Anti-spoofing（RGB 活体检测）服务 API Key"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSave" style="width: 100%">
            {{ $t('settings.save') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const { locale } = useI18n()

const form = reactive({
  language: localStorage.getItem('locale') || 'zh',
  detectionApiKey: localStorage.getItem('apiKey_detection') || '',
  recognitionApiKey: localStorage.getItem('apiKey_recognition') || '',
  verificationApiKey: localStorage.getItem('apiKey_verification') || '',
  antispoofingApiKey: localStorage.getItem('apiKey_antispoofing') || ''
})

const handleLanguageChange = (lang) => {
  locale.value = lang
  localStorage.setItem('locale', lang)
  ElMessage.success('Language changed')
}

const handleSave = () => {
  localStorage.setItem('locale', form.language)
  localStorage.setItem('apiKey_detection', form.detectionApiKey)
  localStorage.setItem('apiKey_recognition', form.recognitionApiKey)
  localStorage.setItem('apiKey_verification', form.verificationApiKey)
  localStorage.setItem('apiKey_antispoofing', form.antispoofingApiKey)
  ElMessage.success('Settings saved')
}
</script>

<style scoped>
.settings-view {
  max-width: 700px;
  margin: 0 auto;
}

.card-header {
  font-weight: bold;
}
</style>

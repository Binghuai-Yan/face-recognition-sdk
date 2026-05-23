<template>
  <div class="settings-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('settings.title') }}</span>
        </div>
      </template>
      
      <el-form :model="form" label-position="top" style="max-width: 500px">
        <el-divider>{{ $t('settings.language') }}</el-divider>
        
        <el-form-item :label="$t('settings.language')">
          <el-radio-group v-model="form.language" @change="handleLanguageChange">
            <el-radio-button label="zh">{{ $t('language.zh') }}</el-radio-button>
            <el-radio-button label="en">{{ $t('language.en') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <el-divider>{{ $t('settings.apiConfig') }}</el-divider>
        
        <el-form-item :label="$t('settings.apiUrl')">
          <el-input v-model="form.apiUrl" placeholder="http://localhost:8000" />
        </el-form-item>
        
        <el-form-item :label="$t('settings.apiKey')">
          <el-input 
            v-model="form.apiKey" 
            type="password" 
            show-password
            placeholder="Enter your API key"
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
  apiUrl: localStorage.getItem('apiUrl') || 'http://localhost:8000',
  apiKey: localStorage.getItem('apiKey') || ''
})

const handleLanguageChange = (lang) => {
  locale.value = lang
  localStorage.setItem('locale', lang)
  ElMessage.success('Language changed')
}

const handleSave = () => {
  localStorage.setItem('locale', form.language)
  localStorage.setItem('apiUrl', form.apiUrl)
  localStorage.setItem('apiKey', form.apiKey)
  ElMessage.success('Settings saved')
}
</script>

<style scoped>
.settings-view {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  font-weight: bold;
}
</style>

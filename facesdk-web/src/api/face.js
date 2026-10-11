import axios from 'axios'

const API_BASE = '/api/v1'
const segment = value => {
  if (typeof value !== 'string' || !value || value === '.' || value === '..') {
    throw new Error('Identifier must not be empty or a dot segment')
  }
  return encodeURIComponent(value)
}

// CompreFace 不同服务使用不同的 API Key
const getApiKey = (service) => {
  return localStorage.getItem(`apiKey_${service}`) || localStorage.getItem('apiKey') || ''
}

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use((config) => {
  // 根据请求路径自动选择对应服务的 API Key
  const url = config.url || ''
  let service = 'recognition' // 默认
  if (url.includes('/detection/')) {
    service = 'detection'
  } else if (url.includes('/verification/')) {
    service = 'verification'
  } else if (url.includes('/recognition/')) {
    service = 'recognition'

  }

  const apiKey = getApiKey(service)
  if (apiKey) {
    config.headers['x-api-key'] = apiKey
  }
  return config
})

// 人脸检测 - Detection 服务
export const detectFace = (formData, plugins = [], threshold = 0.5) => {
  const params = { det_prob_threshold: threshold }
  if (plugins.length > 0) {
    params.face_plugins = plugins.join(',')
  }
  return apiClient.post('/detection/detect', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 人脸比对 - Verification 服务（不是 recognition/compare）
export const compareFaces = (formData) => {
  return apiClient.post('/verification/verify', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 人脸搜索 - Recognition 服务
export const searchFace = (formData, predictionCount = 1) => {
  return apiClient.post('/recognition/recognize', formData, {
    params: { prediction_count: predictionCount },
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 获取所有人脸库 - Recognition 服务
export const getSubjects = () => {
  return apiClient.get('/recognition/subjects').then(res => res.data.subjects || [])
}

// 创建人脸库 - Recognition 服务
export const createSubject = (subjectId) => {
  return apiClient.post('/recognition/subjects', { subject: subjectId })
    .then(res => res.data)
}

// 删除人脸库 - Recognition 服务
export const deleteSubject = (subjectId) => {
  return apiClient.delete(`/recognition/subjects/${segment(subjectId)}`)
}

// 添加人脸 - Recognition 服务
export const addFace = (subjectId, formData) => {
  return apiClient.post('/recognition/faces', formData, {
    params: { subject: subjectId },
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 删除人脸 - Recognition 服务
export const deleteFace = (faceId) => {
  return apiClient.delete(`/recognition/faces/${segment(faceId)}`)
}

// 获取指定人脸库的人脸列表 - Recognition 服务
export const getFaces = (subjectId, page = 0, size = 20) => {
  return apiClient.get('/recognition/faces', {
    params: { subject: subjectId, page, size }
  }).then(res => res.data)
}

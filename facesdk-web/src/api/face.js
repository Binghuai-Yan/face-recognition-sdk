import axios from 'axios'

const API_BASE = '/api/v1'

const getApiKey = () => localStorage.getItem('apiKey') || ''

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use((config) => {
  const apiKey = getApiKey()
  if (apiKey) {
    config.headers['x-api-key'] = apiKey
  }
  return config
})

// 人脸检测
export const detectFace = (formData) => {
  return apiClient.post('/detection/detect', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 人脸比对
export const compareFaces = (formData) => {
  return apiClient.post('/recognition/compare', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 人脸搜索
export const searchFace = (formData) => {
  return apiClient.post('/recognition/recognize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 获取所有人脸库
export const getSubjects = () => {
  return apiClient.get('/recognition/subjects').then(res => res.data.subjects || [])
}

// 创建人脸库
export const createSubject = (subjectId, name = '') => {
  return apiClient.post('/recognition/subjects', { subject: subjectId, name })
    .then(res => res.data)
}

// 删除人脸库
export const deleteSubject = (subjectId) => {
  return apiClient.delete(`/recognition/subjects/${subjectId}`)
}

// 添加人脸
export const addFace = (subjectId, formData) => {
  return apiClient.post('/recognition/faces', formData, {
    params: { subject: subjectId },
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

// 删除人脸
export const deleteFace = (faceId) => {
  return apiClient.delete(`/recognition/faces/${faceId}`)
}

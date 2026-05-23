<template>
  <div class="subjects-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('subjects.title') }}</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            {{ $t('subjects.createSubject') }}
          </el-button>
        </div>
      </template>
      
      <el-table :data="subjects" v-loading="loading" style="width: 100%">
        <el-table-column type="index" width="50" />
        <el-table-column :label="$t('subjects.subjectId')" prop="subject" />
        <el-table-column :label="$t('subjects.subjectName')" prop="name" />
        <el-table-column :label="$t('subjects.faceCount')">
          <template #default="{ row }">
            {{ row.faces?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="handleAddFace(row.subject)">
              {{ $t('subjects.addFace') }}
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.subject)">
              {{ $t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- Create Subject Dialog -->
    <el-dialog v-model="showCreateDialog" :title="$t('subjects.createSubject')" width="400px">
      <el-form :model="createForm" label-position="top">
        <el-form-item :label="$t('subjects.subjectId')" required>
          <el-input v-model="createForm.subjectId" :placeholder="$t('subjects.subjectId')" />
        </el-form-item>
        <el-form-item :label="$t('subjects.subjectName')">
          <el-input v-model="createForm.name" :placeholder="$t('subjects.subjectName')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">
          {{ $t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- Add Face Dialog -->
    <el-dialog v-model="showAddFaceDialog" :title="$t('subjects.addFace')" width="500px">
      <el-upload
        class="image-uploader"
        action="#"
        :auto-upload="false"
        :on-change="handleFaceImageChange"
        :show-file-list="false"
        accept="image/jpeg,image/png"
      >
        <img v-if="faceImageUrl" :src="faceImageUrl" class="preview-image" />
        <div v-else class="upload-placeholder">
          <el-icon size="36"><Plus /></el-icon>
          <div class="el-upload__text">{{ $t('common.dragUpload') }}</div>
        </div>
      </el-upload>
      <template #footer>
        <el-button @click="showAddFaceDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitAddFace" :loading="addingFace" :disabled="!faceImage">
          {{ $t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getSubjects, createSubject, deleteSubject, addFace, getFaces } from '@/api/face'

const subjects = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showAddFaceDialog = ref(false)
const creating = ref(false)
const addingFace = ref(false)
const currentSubjectId = ref('')

const createForm = ref({
  subjectId: '',
  name: ''
})

const faceImage = ref(null)
const faceImageUrl = ref('')

const fetchSubjects = async () => {
  loading.value = true
  try {
    const res = await getSubjects()
    // 获取每个人脸库的人脸数量
    const subjectsWithFaces = await Promise.all(
      res.map(async (subjectId) => {
        try {
          const faces = await getFaces(subjectId)
          return { subject: subjectId, name: '', faces: faces || [] }
        } catch (e) {
          return { subject: subjectId, name: '', faces: [] }
        }
      })
    )
    subjects.value = subjectsWithFaces
  } catch (error) {
    ElMessage.error(error.message || 'Failed to load subjects')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  if (!createForm.value.subjectId) {
    ElMessage.warning('Please enter subject ID')
    return
  }
  
  creating.value = true
  try {
    await createSubject(createForm.value.subjectId, createForm.value.name)
    ElMessage.success('Subject created successfully')
    showCreateDialog.value = false
    createForm.value = { subjectId: '', name: '' }
    fetchSubjects()
  } catch (error) {
    ElMessage.error(error.message || 'Failed to create subject')
  } finally {
    creating.value = false
  }
}

const handleDelete = async (subjectId) => {
  try {
    await ElMessageBox.confirm(
      // eslint-disable-next-line no-undef
      $t('subjects.deleteConfirm'),
      // eslint-disable-next-line no-undef
      $t('common.confirm'),
      { type: 'warning' }
    )
    await deleteSubject(subjectId)
    ElMessage.success('Subject deleted successfully')
    fetchSubjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || 'Failed to delete subject')
    }
  }
}

const handleAddFace = (subjectId) => {
  currentSubjectId.value = subjectId
  faceImage.value = null
  faceImageUrl.value = ''
  showAddFaceDialog.value = true
}

const handleFaceImageChange = (file) => {
  faceImage.value = file.raw
  faceImageUrl.value = URL.createObjectURL(file.raw)
}

const submitAddFace = async () => {
  if (!faceImage.value) return
  
  addingFace.value = true
  try {
    const formData = new FormData()
    formData.append('file', faceImage.value)
    await addFace(currentSubjectId.value, formData)
    ElMessage.success('Face added successfully')
    showAddFaceDialog.value = false
    fetchSubjects()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.message || 'Failed to add face')
  } finally {
    addingFace.value = false
  }
}

onMounted(fetchSubjects)
</script>

<style scoped>
.subjects-view {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { beforeEach, expect, test, vi } from 'vitest'
import ElementPlus, { ElMessageBox } from 'element-plus'
import SubjectsView from '../src/views/SubjectsView.vue'
import SearchView from '../src/views/SearchView.vue'
import DetectView from '../src/views/DetectView.vue'
import CompareView from '../src/views/CompareView.vue'
import * as api from '../src/api/face'
import en from '../src/locales/en.json'
vi.mock('../src/api/face', () => ({ getSubjects: vi.fn(), getFaces: vi.fn(), deleteSubject: vi.fn(), createSubject: vi.fn(), addFace: vi.fn(), searchFace: vi.fn(), detectFace: vi.fn(), compareFaces: vi.fn() }))
const render = component => mount(component, {global:{plugins:[ElementPlus,createI18n({legacy:false,locale:'en',messages:{en}})]}})
beforeEach(() => { vi.clearAllMocks(); URL.createObjectURL = vi.fn(()=>'blob:test'); api.getSubjects.mockResolvedValue(['alice']); api.getFaces.mockResolvedValue({faces:[],total_elements:42}); api.deleteSubject.mockResolvedValue({}) })
test('subject deletion reaches translated confirmation and deletes the intended subject', async () => {
  const confirm = vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm')
  const wrapper=render(SubjectsView)
  await flushPromises()
  expect(wrapper.text()).toContain('42')
  await wrapper.findAll('button').find(b=>b.text()==='Delete').trigger('click')
  await flushPromises()
  expect(confirm).toHaveBeenCalledWith(en.subjects.deleteConfirm,en.common.confirm,{type:'warning'})
  expect(api.deleteSubject).toHaveBeenCalledWith('alice')
  wrapper.unmount(); confirm.mockRestore()
})
test('search sends candidate count and filters below threshold including the boundary', async () => {
  api.searchFace.mockResolvedValue({result:[{subjects:[{subject:'below',similarity:.49},{subject:'boundary',similarity:.5},{subject:'best',similarity:.9}]}]})
  const wrapper=render(SearchView)
  wrapper.vm.$.setupState.handleImageChange({raw:new File(['image'],'image.jpg')})
  await flushPromises()
  await wrapper.findAll('button').find(b=>b.text()==='Search').trigger('click')
  await flushPromises()
  expect(api.searchFace).toHaveBeenCalledWith(expect.any(FormData),5)
  const form=api.searchFace.mock.calls[0][0]
  expect([...form.keys()]).toEqual(['file'])
  expect(wrapper.text()).toContain('boundary'); expect(wrapper.text()).toContain('best'); expect(wrapper.text()).not.toContain('below')
  wrapper.unmount()
})
test('detection offers supported plugins and sends the threshold as an API option', async () => {
  api.detectFace.mockResolvedValue({result:[]})
  const wrapper=render(DetectView)
  expect(wrapper.text()).not.toContain('Liveness'); expect(wrapper.text()).not.toContain('Quality')
  wrapper.vm.$.setupState.handleImageChange({raw:new File(['image'],'image.jpg')})
  await flushPromises()
  await wrapper.findAll('button').find(b=>b.text()==='Submit').trigger('click')
  await flushPromises()
  expect(api.detectFace).toHaveBeenCalledWith(expect.any(FormData),['age','gender','pose'],.5)
  wrapper.unmount()
})
test('comparison accepts threshold boundary and rejects multiple faces', async () => {
  const wrapper=render(CompareView)
  wrapper.vm.$.setupState.handleImageChange({raw:new File(['image'],'image.jpg')},1)
  wrapper.vm.$.setupState.handleImageChange({raw:new File(['image'],'image.jpg')},2)
  api.compareFaces.mockResolvedValue({result:[{face_matches:[{similarity:.8}]}]})
  await wrapper.vm.$.setupState.handleCompare(); await flushPromises()
  expect(wrapper.vm.$.setupState.isMatch).toBe(true)
  api.compareFaces.mockResolvedValue({result:[{face_matches:[{similarity:.9},{similarity:.95}]}]})
  await wrapper.vm.$.setupState.handleCompare(); await flushPromises()
  expect(wrapper.vm.$.setupState.result).toBe(null)
  wrapper.unmount()
})

import { beforeEach, expect, test, vi } from 'vitest'
const { transport, interceptors } = vi.hoisted(() => ({
  transport: { post: vi.fn(), get: vi.fn(), delete: vi.fn() },
  interceptors: { request: { use: vi.fn() } }
}))
vi.mock('axios', () => ({ default: { create: () => ({ ...transport, interceptors }) } }))
import { detectFace, compareFaces, searchFace, getFaces, createSubject, deleteSubject, deleteFace } from '../src/api/face'
beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); transport.post.mockResolvedValue({data:{}}); transport.delete.mockResolvedValue({data:{}}) })
test('query parameters and fields use the official protocol', async () => {
  const form = new FormData()
  await detectFace(form, ['age'], 0.7)
  expect(transport.post).toHaveBeenLastCalledWith('/detection/detect', form, expect.objectContaining({params:{face_plugins:'age',det_prob_threshold:0.7}}))
  await compareFaces(form)
  expect(transport.post.mock.calls.at(-1)[0]).toBe('/verification/verify')
  await searchFace(form, 5)
  expect(transport.post.mock.calls.at(-1)[2].params).toEqual({prediction_count:5})
  await createSubject('张三')
  expect(transport.post).toHaveBeenLastCalledWith('/recognition/subjects',{subject:'张三'})
})
test('face pagination preserves total count and identifiers are encoded', async () => {
  transport.get.mockResolvedValue({data:{faces:[{image_id:'face'}],total_elements:42,total_pages:3}})
  expect((await getFaces('alice',0,1)).total_elements).toBe(42)
  expect(transport.get).toHaveBeenLastCalledWith('/recognition/faces',{params:{subject:'alice',page:0,size:1}})
  await deleteSubject('张三 /?&')
  expect(transport.delete.mock.calls.at(-1)[0]).toBe('/recognition/subjects/'+encodeURIComponent('张三 /?&'))
  await deleteFace('id/?')
  expect(transport.delete.mock.calls.at(-1)[0]).toBe('/recognition/faces/'+encodeURIComponent('id/?'))
  const calls=transport.delete.mock.calls.length
  expect(()=>deleteSubject('')).toThrow('Identifier')
  expect(()=>deleteSubject('..')).toThrow('Identifier')
  expect(()=>deleteFace('')).toThrow('Identifier')
  expect(transport.delete).toHaveBeenCalledTimes(calls)
})

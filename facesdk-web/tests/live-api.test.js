import { readFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import { test, expect, beforeEach, afterEach } from 'vitest'
import { detectFace, compareFaces, searchFace, createSubject, deleteSubject, getSubjects, addFace, getFaces, deleteFace } from '../src/api/face'

const live = process.env.FACESDK_LIVE === '1' ? test : test.skip
beforeEach(() => {
  if (process.env.FACESDK_LIVE !== '1') return
  for (const service of ['detection', 'recognition', 'verification']) {
    localStorage.setItem(`apiKey_${service}`, process.env[`FACESDK_${service.toUpperCase()}_API_KEY`])
  }
})
afterEach(() => localStorage.clear())
const image = () => new File([readFileSync(process.env.FACESDK_TEST_IMAGE)], 'face.jpg', { type: 'image/jpeg' })
const upload = fields => {
  const form = new FormData()
  for (const field of fields) form.append(field, image())
  return form
}

live('frontend actual XHR detects and verifies a real face through the same-origin proxy', async () => {
  const detected = await detectFace(upload(['file']), ['calculator'], 0.7)
  expect(detected.result).toHaveLength(1)
  expect(detected.result[0].embedding.length).toBeGreaterThan(0)
  const compared = await compareFaces(upload(['source_image', 'target_image']))
  expect(compared.result[0].face_matches).toHaveLength(1)
  expect(compared.result[0].face_matches[0].similarity).toBeGreaterThanOrEqual(0.8)
}, 120000)

live('frontend actual XHR creates, lists, searches, paginates and deletes face records', async () => {
  const subject = `facesdk-web-${randomUUID()}`
  let cleanup = false
  try {
    expect((await createSubject(subject)).subject).toBe(subject)
    cleanup = true
    expect(await getSubjects()).toContain(subject)
    const record = await addFace(subject, upload(['file']))
    expect(record.subject).toBe(subject)
    const faces = await getFaces(subject, 0, 1)
    expect(faces.total_elements).toBe(1)
    expect(faces.faces[0].image_id).toBe(record.image_id)
    const results = await searchFace(upload(['file']), 100)
    expect(results.result[0].subjects.some(r => r.subject === subject && r.similarity >= 0.8)).toBe(true)
    await deleteFace(record.image_id)
    expect((await getFaces(subject)).total_elements).toBe(0)
    if (!(await getSubjects()).includes(subject)) await createSubject(subject)
    await deleteSubject(subject)
    cleanup = false
    expect(await getSubjects()).not.toContain(subject)
  } finally {
    if (cleanup) await deleteSubject(subject)
  }
}, 120000)

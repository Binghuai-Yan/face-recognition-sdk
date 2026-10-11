const assert = require('node:assert/strict');
const fs = require('node:fs');
const {randomUUID, createHash} = require('node:crypto');
const {FaceSDKClient} = require('../../../sdk/nodejs');

async function main() {
  const image = fs.readFileSync(process.env.FACESDK_TEST_IMAGE);
  const client = new FaceSDKClient({apiUrl:process.env.FACESDK_API_URL,
    apiKeys:Object.fromEntries(['detection','recognition','verification'].map(s => [s,process.env[`FACESDK_${s.toUpperCase()}_API_KEY`]])),
    timeout:120000, maxRetries:0});
  const subject = `facesdk-node-${randomUUID()}`;
  let cleanup = false;
  try {
    assert.equal((await client.detect(image)).face_count, 1);
    assert.equal((await client.createSubject(subject)).subject, subject);
    cleanup = true;
    assert.ok((await client.listSubjects()).some(s => s.subject === subject));
    const record = await client.addFace(subject, image);
    assert.equal(record.subject, subject);
    assert.ok(record.image_id);
    const results = await client.search(image, 100, 0.8);
    assert.equal(results.face_count, 1);
    assert.ok(results.results.some(r => r.subject === subject && r.is_match));
    const comparison = await client.compare(image, image);
    assert.ok(comparison.is_match && comparison.similarity >= 0.8);
    const feature = Buffer.from(await client.extractFeature(image), 'base64');
    assert.ok(feature.length > 0 && feature.length % 4 === 0);
    if (process.env.FACESDK_FEATURE_SHA256) assert.equal(createHash('sha256').update(feature).digest('hex'), process.env.FACESDK_FEATURE_SHA256);
    await client.deleteFace(record.image_id);
    if (!(await client.listSubjects()).some(s => s.subject === subject)) await client.createSubject(subject);
    await client.deleteSubject(subject);
    cleanup = false;
    assert.ok(!(await client.listSubjects()).some(s => s.subject === subject));
    console.log('Node real-model lifecycle passed');
  } finally {
    if (cleanup) await client.deleteSubject(subject);
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });

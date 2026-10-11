const http = require('http');
const { Readable } = require('stream');
const fixtures = require('../../tests/fixtures/compreface-1.2.json');
const { FaceSDKClient, FaceSDKError } = require('./index');
const bytes = Buffer.from('image\x00\xff');
let server, client, queue, requests;
beforeEach(async () => {
  queue = []; requests = [];
  server = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    requests.push({ url: new URL(req.url, 'http://localhost'), method: req.method, headers: req.headers, body: Buffer.concat(chunks) });
    const [status, payload] = queue.shift() || [500, fixtures.error];
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(typeof payload === 'string' ? payload : JSON.stringify(payload));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  client = new FaceSDKClient({ apiUrl: `http://127.0.0.1:${server.address().port}/`, apiKeys: { detection: 'D', verification: 'V', recognition: 'R' }, maxRetries: 1, retryDelay: 0 });
});
afterEach(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); });
test('all public operations use official routes, keys and models', async () => {
  queue.push([200, fixtures.detection]);
  const detection = await client.detect(bytes, { det_prob_threshold: 0.7, status: true });
  expect(detection.face_count).toBe(1); expect(detection.faces[0].confidence).toBe(0.99);
  expect(requests.at(-1).headers['x-api-key']).toBe('D');
  expect(requests.at(-1).url.searchParams.get('status')).toBe('true');
  queue.push([200, fixtures.verification]);
  const comparison = await client.compare(bytes, bytes);
  expect(comparison.is_match).toBe(true); expect(comparison.similarity).toBe(0.8);
  expect(requests.at(-1).url.pathname).toBe('/api/v1/verification/verify');
  expect(requests.at(-1).headers['x-api-key']).toBe('V');
  expect(requests.at(-1).body.toString()).toContain('name="source_image"');
  expect(requests.at(-1).body.toString()).toContain('name="target_image"');
  queue.push([200, fixtures.recognition]);
  const search = await client.search(bytes, 3, 0.8);
  expect(search.results.map(s => s.subject)).toEqual(['best', 'boundary']);
  expect(search.face_count).toBe(1); expect(requests.at(-1).url.search).toBe('?prediction_count=3');
  expect(requests.at(-1).headers['x-api-key']).toBe('R');
  queue.push([200, fixtures.detection]); expect(await client.extractFeature(bytes)).toBe(fixtures.embedding_base64);
  expect(requests.at(-1).url.searchParams.get('face_plugins')).toBe('calculator');
  queue.push([200, fixtures.subjects]); expect(await client.listSubjects()).toEqual(fixtures.subjects.subjects.map(subject => ({subject})));
  const subject = fixtures.created.subject;
  queue.push([201, fixtures.created]); await client.createSubject(subject, 'ignored');
  expect(JSON.parse(requests.at(-1).body.toString())).toEqual({subject});
  queue.push([201, fixtures.added]); const record = await client.addFace(subject, bytes);
  expect(record.image_id).toBe(fixtures.added.image_id); expect(requests.at(-1).url.searchParams.get('subject')).toBe(subject);
  queue.push([204, '']); await client.deleteFace(record.image_id);
  queue.push([204, '']); await client.deleteSubject(subject);
  expect(decodeURIComponent(requests.at(-1).url.pathname.split('/subjects/')[1])).toBe(subject);
  expect(requests.at(-1).url.search).toBe('');
});
test('retries replay complete stream and multipart bytes', async () => {
  queue.push([503, fixtures.error], [200, fixtures.detection]);
  await client.detect(Readable.from([bytes]));
  expect(requests).toHaveLength(2);
  for (const req of requests) { expect(req.body.includes(bytes)).toBe(true); expect(req.body.toString()).toContain('name="file"'); }
});
test.each([400, 401])('HTTP %i is not retried', async status => {
  queue.push([status, fixtures.error]); await expect(client.detect(bytes)).rejects.toBeInstanceOf(FaceSDKError);
  expect(requests).toHaveLength(1);
});
test.each(['createSubject', 'addFace'])('%s writes are not retried', async method => {
  queue.push([503, fixtures.error]); await expect(client[method]('new', bytes)).rejects.toBeInstanceOf(FaceSDKError);
  expect(requests).toHaveLength(1);
});
test.each(['<html>bad</html>', '[]', '{}'])('invalid success payload %s fails without retry', async payload => {
  queue.push([200, payload]); await expect(client.detect(bytes)).rejects.toBeInstanceOf(FaceSDKError);
  expect(requests).toHaveLength(1);
});
test('validation and ambiguous images fail', async () => {
  await expect(client.search(bytes, 0)).rejects.toBeInstanceOf(FaceSDKError);
  await expect(client.search(bytes, 1, NaN)).rejects.toBeInstanceOf(FaceSDKError);
  await expect(client.addFace('new', bytes, {source:'camera'})).rejects.toBeInstanceOf(FaceSDKError);
  await expect(client.deleteSubject('..')).rejects.toBeInstanceOf(FaceSDKError);
  expect(requests).toHaveLength(0);
  queue.push([200, {result: fixtures.detection.result.concat(fixtures.detection.result)}]);
  await expect(client.extractFeature(bytes)).rejects.toBeInstanceOf(FaceSDKError);
  queue.push([200, fixtures.empty]); await expect(client.compare(bytes, bytes)).rejects.toBeInstanceOf(FaceSDKError);
});
test('zero retries and missing keys', async () => {
  client.maxRetries = 0;
  queue.push([503, fixtures.error]); await expect(client.detect(bytes)).rejects.toBeInstanceOf(FaceSDKError);
  expect(requests).toHaveLength(1);
  client.apiKeys = {}; await expect(client.detect(bytes)).rejects.toBeInstanceOf(FaceSDKError);
  expect(requests).toHaveLength(1);
});

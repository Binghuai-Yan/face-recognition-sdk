/** CompreFace 1.2 client. Copyright FaceSDK Contributors, MIT License. */
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');

class FaceSDKError extends Error {
  constructor(message, errorCode, httpStatusCode) {
    super(message);
    this.name = 'FaceSDKError';
    this.errorCode = errorCode;
    this.httpStatusCode = httpStatusCode;
  }
}
class APIError extends FaceSDKError {
  constructor(message, errorCode = 'API_ERROR', httpStatusCode) {
    super(message, errorCode, httpStatusCode);
    this.name = 'APIError';
  }
}
class NoFaceError extends FaceSDKError {
  constructor(message = 'No face detected in the image') {
    super(message, 'NO_FACE_DETECTED', 400);
    this.name = 'NoFaceError';
  }
}

const validateThreshold = (value) => {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new FaceSDKError('threshold must be between 0 and 1', 'VALIDATION_ERROR');
  }
};
const segment = (value) => {
  if (!value || value === '.' || value === '..') {
    throw new FaceSDKError('Identifier must not be empty or a dot segment', 'VALIDATION_ERROR');
  }
  return encodeURIComponent(value);
};
const face = (value) => ({ ...value, confidence: value.confidence ?? value.box?.probability ?? 0 });
const resultArray = (data, key = 'result', legacy) => {
  const values = data[key] ?? data[legacy];
  if (!Array.isArray(values)) throw new APIError(`Missing ${key} array`, 'INVALID_RESPONSE');
  return values;
};

class FaceSDKClient {
  constructor(config) {
    this.apiUrl = config.apiUrl.replace(/\/+$/, '');
    this.apiKey = config.apiKey || '';
    this.apiKeys = { ...config.apiKeys };
    this.timeout = config.timeout ?? 30000;
    this.maxRetries = config.maxRetries ?? 3;
    this.retryDelay = config.retryDelay ?? 500;
    this.comparisonThreshold = config.comparisonThreshold ?? 0.8;
    validateThreshold(this.comparisonThreshold);
    if (!Number.isInteger(this.maxRetries) || this.maxRetries < 0 || this.retryDelay < 0) {
      throw new FaceSDKError('Invalid retry configuration', 'VALIDATION_ERROR');
    }
    this.httpClient = axios.create({ timeout: this.timeout, validateStatus: () => true });
  }

  async _readImage(image) {
    if (Buffer.isBuffer(image)) return { content: image, filename: 'image.jpg' };
    if (typeof image === 'string') {
      return { content: await fs.promises.readFile(image), filename: path.basename(image) };
    }
    if (image && typeof image[Symbol.asyncIterator] === 'function') {
      const chunks = [];
      for await (const chunk of image) chunks.push(Buffer.from(chunk));
      return { content: Buffer.concat(chunks), filename: 'image.jpg' };
    }
    throw new FaceSDKError('Unsupported image type', 'VALIDATION_ERROR');
  }

  async _request(method, endpoint, { parts, params, json } = {}) {
    const service = endpoint.split('/')[3];
    const apiKey = this.apiKeys[service] ?? this.apiKey;
    if (!apiKey) throw new APIError(`Missing API key for ${service}`, 'AUTHENTICATION_ERROR', 401);
    const safe = method === 'GET' || method === 'DELETE' ||
      ['/api/v1/detection/detect', '/api/v1/verification/verify', '/api/v1/recognition/recognize'].includes(endpoint);
    const retries = safe ? this.maxRetries : 0;
    for (let attempt = 0; attempt <= retries; attempt++) {
      let data = json;
      let headers = { 'x-api-key': apiKey };
      if (parts) {
        data = new FormData();
        for (const [field, image] of parts) {
          data.append(field, image.content, { filename: image.filename });
        }
        headers = { ...headers, ...data.getHeaders() };
      }
      try {
        const response = await this.httpClient.request({ method, url: this.apiUrl + endpoint, data, params, headers });
        if ([429, 500, 502, 503, 504].includes(response.status) && attempt < retries) {
          await this._delay(attempt);
          continue;
        }
        if (response.status < 200 || response.status >= 300) this._responseError(response);
        if (response.status === 204) return {};
        if (!response.data || typeof response.data !== 'object' || Array.isArray(response.data)) {
          throw new APIError('API returned invalid JSON', 'INVALID_RESPONSE', response.status);
        }
        return response.data;
      } catch (error) {
        if (error instanceof FaceSDKError) throw error;
        if (attempt === retries) throw new FaceSDKError(error.message, 'NETWORK_ERROR');
        await this._delay(attempt);
      }
    }
  }

  _delay(attempt) {
    return new Promise(resolve => setTimeout(resolve, this.retryDelay * 2 ** attempt));
  }

  _responseError(response) {
    const message = response.data?.message || response.data?.error || `HTTP ${response.status}`;
    if (response.status === 400 && /no face/i.test(message)) throw new NoFaceError(message);
    throw new APIError(message, `HTTP_${response.status}`, response.status);
  }

  async detect(image, options = {}) {
    const data = await this._request('POST', '/api/v1/detection/detect', {
      parts: [['file', await this._readImage(image)]], params: options,
    });
    const faces = resultArray(data, 'result', 'faces').map(face);
    return { ...data, faces, face_count: faces.length };
  }

  async compare(image1, image2) {
    const data = await this._request('POST', '/api/v1/verification/verify', {
      parts: [['source_image', await this._readImage(image1)], ['target_image', await this._readImage(image2)]],
    });
    const results = resultArray(data);
    if (!results.length || !results[0].face_matches?.length) throw new NoFaceError();
    if (results.length !== 1 || results[0].face_matches.length !== 1) {
      throw new FaceSDKError('Comparison requires exactly one face in each image', 'VALIDATION_ERROR');
    }
    const target = results[0].face_matches[0];
    return { ...data, similarity: target.similarity, threshold: this.comparisonThreshold,
      is_match: target.similarity >= this.comparisonThreshold,
      face1: face(results[0].source_image_face), face2: face(target) };
  }

  async search(image, limit = 1, threshold = 0) {
    validateThreshold(threshold);
    if (!Number.isInteger(limit) || limit < 1) {
      throw new FaceSDKError('limit must be a positive integer', 'VALIDATION_ERROR');
    }
    const data = await this._request('POST', '/api/v1/recognition/recognize', {
      parts: [['file', await this._readImage(image)]], params: { prediction_count: limit },
    });
    const results = resultArray(data).flatMap(f => (f.subjects || [])
      .filter(s => s.similarity >= threshold).map(s => ({ ...s, is_match: true, face: face(f) })));
    results.sort((a, b) => b.similarity - a.similarity);
    return { ...data, results, face_count: (data.result || []).length };
  }

  async extractFeature(image) {
    const data = await this.detect(image, { face_plugins: 'calculator' });
    if (!data.faces.length) throw new NoFaceError();
    if (data.faces.length !== 1) throw new FaceSDKError('Feature extraction requires exactly one face', 'VALIDATION_ERROR');
    const embedding = data.faces[0].embedding;
    if (!embedding?.length) throw new APIError('The calculator plugin did not return an embedding', 'NO_EMBEDDING');
    const buffer = Buffer.alloc(embedding.length * 4);
    embedding.forEach((value, index) => buffer.writeFloatLE(value, index * 4));
    return buffer.toString('base64');
  }

  async createSubject(subjectId, _name = '') {
    // name is retained for source compatibility; CompreFace persists only subject.
    return this._request('POST', '/api/v1/recognition/subjects', { json: { subject: subjectId } });
  }
  async deleteSubject(subjectId) {
    await this._request('DELETE', `/api/v1/recognition/subjects/${segment(subjectId)}`);
  }
  async listSubjects() {
    const data = await this._request('GET', '/api/v1/recognition/subjects');
    return resultArray(data, 'subjects').map(s => typeof s === 'string' ? { subject: s } : s);
  }
  async addFace(subjectId, image, metadata = null) {
    if (metadata && Object.keys(metadata).length) {
      throw new FaceSDKError('CompreFace 1.2 does not persist metadata; store it in your application', 'VALIDATION_ERROR');
    }
    return this._request('POST', '/api/v1/recognition/faces', {
      parts: [['file', await this._readImage(image)]], params: { subject: subjectId },
    });
  }
  async deleteFace(faceId) {
    await this._request('DELETE', `/api/v1/recognition/faces/${segment(faceId)}`);
  }
}

module.exports = { FaceSDKClient, FaceSDKError, APIError, NoFaceError };

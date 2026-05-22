/**
 * File: facesdk/sdk/nodejs/index.js
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * FaceSDK Node.js SDK
 */

const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');

/**
 * FaceSDK 错误类
 */
class FaceSDKError extends Error {
  constructor(message, errorCode, httpStatusCode) {
    super(message);
    this.name = 'FaceSDKError';
    this.errorCode = errorCode;
    this.httpStatusCode = httpStatusCode;
  }
}

/**
 * API 错误类
 */
class APIError extends FaceSDKError {
  constructor(message, errorCode, httpStatusCode) {
    super(message, errorCode || 'API_ERROR', httpStatusCode);
    this.name = 'APIError';
  }
}

/**
 * 未检测到人脸错误
 */
class NoFaceError extends FaceSDKError {
  constructor(message = 'No face detected in the image') {
    super(message, 'NO_FACE_DETECTED', 400);
    this.name = 'NoFaceError';
  }
}

/**
 * FaceSDK 客户端
 */
class FaceSDKClient {
  /**
   * 创建 FaceSDK 客户端
   * @param {Object} config - 配置对象
   * @param {string} config.apiUrl - API 基础 URL
   * @param {string} config.apiKey - API 密钥
   * @param {number} [config.timeout=30000] - 请求超时时间（毫秒）
   * @param {number} [config.maxRetries=3] - 最大重试次数
   * @param {number} [config.retryDelay=500] - 重试延迟（毫秒）
   */
  constructor(config) {
    this.apiUrl = config.apiUrl.replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
    this.connectTimeout = config.connectTimeout || 5000;
    this.maxRetries = config.maxRetries || 3;
    this.retryDelay = config.retryDelay || 500;

    this.httpClient = axios.create({
      timeout: this.timeout,
      // Note: axios uses `timeout` as overall timeout.
      // For separate connect timeout, use http.Agent:
      httpAgent: new (require('http').Agent)({ timeout: this.connectTimeout }),
      httpsAgent: new (require('https').Agent)({ timeout: this.connectTimeout }),
      headers: {
        'x-api-key': this.apiKey,
      },
    });

    // 请求拦截器
    this.httpClient.interceptors.request.use(
      (config) => {
        console.log(`[FaceSDK] ${config.method.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 响应拦截器
    this.httpClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const config = error.config;
        
        if (!config || !config.retry) {
          config.retry = 0;
        }

        if (config.retry < this.maxRetries) {
          config.retry += 1;
          const delay = this.retryDelay * Math.pow(2, config.retry - 1);
          console.log(`[FaceSDK] Retrying request (${config.retry}/${this.maxRetries}) after ${delay}ms`);
          await new Promise(resolve => setTimeout(resolve, delay));
          return this.httpClient(config);
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * 处理错误响应
   * @private
   */
  _handleError(error) {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data || {};
      const message = data.message || data.error || 'Unknown error';

      if (status === 400 && message.toLowerCase().includes('no face')) {
        throw new NoFaceError(message);
      }

      throw new APIError(message, `HTTP_${status}`, status);
    }

    throw new FaceSDKError(error.message, 'NETWORK_ERROR');
  }

  /**
   * 准备文件数据
   * @private
   */
  _prepareFile(file, fieldName = 'file') {
    const form = new FormData();
    
    if (Buffer.isBuffer(file)) {
      form.append(fieldName, file, { filename: 'image.jpg', contentType: 'image/jpeg' });
    } else if (typeof file === 'string') {
      const fileStream = fs.createReadStream(file);
      const filename = path.basename(file);
      form.append(fieldName, fileStream, filename);
    } else if (file && typeof file.pipe === 'function') {
      form.append(fieldName, file);
    } else {
      throw new Error('Unsupported file type');
    }

    return form;
  }

  /**
   * 人脸检测
   * @param {string|Buffer|Stream} image - 图片路径、Buffer 或 Stream
   * @param {Object} [options] - 可选参数
   * @returns {Promise<DetectionResult>}
   */
  async detect(image, options = {}) {
    try {
      const form = this._prepareFile(image);
      
      // 添加可选参数
      Object.entries(options).forEach(([key, value]) => {
        form.append(key, String(value));
      });

      const response = await this.httpClient.post(
        `${this.apiUrl}/api/v1/detection/detect`,
        form,
        { headers: form.getHeaders() }
      );

      return response.data;
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 人脸比对
   * @param {string|Buffer|Stream} image1 - 第一张图片
   * @param {string|Buffer|Stream} image2 - 第二张图片
   * @returns {Promise<CompareResult>}
   */
  async compare(image1, image2) {
    try {
      const form = new FormData();

      if (Buffer.isBuffer(image1)) {
        form.append('file1', image1, { filename: 'image1.jpg', contentType: 'image/jpeg' });
      } else if (typeof image1 === 'string') {
        form.append('file1', fs.createReadStream(image1), path.basename(image1));
      } else {
        form.append('file1', image1);
      }

      if (Buffer.isBuffer(image2)) {
        form.append('file2', image2, { filename: 'image2.jpg', contentType: 'image/jpeg' });
      } else if (typeof image2 === 'string') {
        form.append('file2', fs.createReadStream(image2), path.basename(image2));
      } else {
        form.append('file2', image2);
      }

      const response = await this.httpClient.post(
        `${this.apiUrl}/api/v1/recognition/compare`,
        form,
        { headers: form.getHeaders() }
      );

      return response.data;
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 人脸识别（1:N）
   * @param {string|Buffer|Stream} image - 待搜索图片
   * @param {number} [limit=1] - 返回结果数量
   * @param {number} [threshold=0] - 相似度阈值
   * @returns {Promise<SearchResult>}
   */
  async search(image, limit = 1, threshold = 0) {
    try {
      const form = this._prepareFile(image);
      form.append('limit', String(limit));
      if (threshold > 0) {
        form.append('threshold', String(threshold));
      }

      const response = await this.httpClient.post(
        `${this.apiUrl}/api/v1/recognition/recognize`,
        form,
        { headers: form.getHeaders() }
      );

      return response.data;
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 提取人脸特征向量
   * @param {string|Buffer|Stream} image - 图片路径、Buffer 或 Stream
   * @returns {Promise<string>} Base64 编码的特征向量
   */
  async extractFeature(image) {
    try {
      const form = this._prepareFile(image);

      const response = await this.httpClient.post(
        `${this.apiUrl}/api/v1/recognition/face`,
        form,
        { headers: form.getHeaders() }
      );

      return response.data.embedding || '';
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 创建人脸库
   * @param {string} subjectId - 人脸库 ID
   * @param {string} [name=''] - 人脸库名称
   * @returns {Promise<Subject>}
   */
  async createSubject(subjectId, name = '') {
    try {
      const response = await this.httpClient.post(
        `${this.apiUrl}/api/v1/recognition/subjects`,
        { subject: subjectId, name }
      );
      return response.data;
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 删除人脸库
   * @param {string} subjectId - 人脸库 ID
   * @returns {Promise<void>}
   */
  async deleteSubject(subjectId) {
    try {
      await this.httpClient.delete(`${this.apiUrl}/api/v1/recognition/subjects/${subjectId}`);
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 列出所有人脸库
   * @returns {Promise<Subject[]>}
   */
  async listSubjects() {
    try {
      const response = await this.httpClient.get(`${this.apiUrl}/api/v1/recognition/subjects`);
      return response.data.subjects || [];
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 添加人脸到人脸库
   * @param {string} subjectId - 人脸库 ID
   * @param {string|Buffer|Stream} image - 人脸图片
   * @param {Object} [metadata] - 元数据
   * @returns {Promise<FaceRecord>}
   */
  async addFace(subjectId, image, metadata = null) {
    try {
      const form = this._prepareFile(image);
      
      if (metadata) {
        form.append('metadata', JSON.stringify(metadata));
      }

      const response = await this.httpClient.post(
        `${this.apiUrl}/api/v1/recognition/faces`,
        form,
        {
          headers: form.getHeaders(),
          params: { subject: subjectId }
        }
      );

      return response.data;
    } catch (error) {
      this._handleError(error);
    }
  }

  /**
   * 删除人脸
   * @param {string} faceId - 人脸 ID
   * @returns {Promise<void>}
   */
  async deleteFace(faceId) {
    try {
      await this.httpClient.delete(`${this.apiUrl}/api/v1/recognition/faces/${faceId}`);
    } catch (error) {
      this._handleError(error);
    }
  }
}

module.exports = {
  FaceSDKClient,
  FaceSDKError,
  APIError,
  NoFaceError,
};

/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/client/FaceSDKClient.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * FaceSDK HTTP Client
 */

package com.facesdk.client;

import com.facesdk.config.FaceSDKConfig;
import com.facesdk.exception.ApiException;
import com.facesdk.exception.FaceSDKException;
import com.facesdk.exception.NoFaceException;
import com.facesdk.model.*;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

/**
 * FaceSDK HTTP 客户端
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
public class FaceSDKClient {

    private static final Logger logger = LoggerFactory.getLogger(FaceSDKClient.class);
    private static final MediaType MEDIA_TYPE_JPEG = MediaType.parse("image/jpeg");
    private static final MediaType MEDIA_TYPE_PNG = MediaType.parse("image/png");

    private final FaceSDKConfig config;
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;

    public FaceSDKClient(FaceSDKConfig config) {
        this.config = Objects.requireNonNull(config, "Config must not be null");
        this.httpClient = createHttpClient(config);
        this.objectMapper = createObjectMapper();
        logger.info("FaceSDKClient initialized with config: {}", config);
    }

    private OkHttpClient createHttpClient(FaceSDKConfig config) {
        OkHttpClient.Builder builder = new OkHttpClient.Builder()
                .connectTimeout(config.getConnectTimeout())
                .readTimeout(config.getReadTimeout())
                .writeTimeout(config.getWriteTimeout())
                .connectionPool(new ConnectionPool(10, 5, TimeUnit.MINUTES));

        if (!config.isVerifySsl()) {
            try {
                // 信任所有证书（仅用于开发/测试）
                javax.net.ssl.SSLContext sslContext = javax.net.ssl.SSLContext.getInstance("TLS");
                sslContext.init(null, new javax.net.ssl.TrustManager[]{
                        new javax.net.ssl.X509TrustManager() {
                            public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                                return new java.security.cert.X509Certificate[]{};
                            }
                            public void checkClientTrusted(java.security.cert.X509Certificate[] certs, String authType) {}
                            public void checkServerTrusted(java.security.cert.X509Certificate[] certs, String authType) {}
                        }
                }, new java.security.SecureRandom());
                builder.sslSocketFactory(sslContext.getSocketFactory(), (javax.net.ssl.X509TrustManager) sslContext.getTrustManagers()[0]);
                builder.hostnameVerifier((hostname, session) -> true);
            } catch (Exception e) {
                logger.warn("Failed to disable SSL verification", e);
            }
        }

        return builder.build();
    }

    private ObjectMapper createObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        return mapper;
    }

    // ==================== 人脸检测 ====================

    /**
     * 检测图片中的人脸
     *
     * @param imageData 图片数据
     * @return 检测结果
     * @throws FaceSDKException 检测失败
     */
    public DetectionResult detect(byte[] imageData) throws FaceSDKException {
        return detect(imageData, null);
    }

    /**
     * 检测图片中的人脸
     *
     * @param imageData 图片数据
     * @param options   可选参数
     * @return 检测结果
     * @throws FaceSDKException 检测失败
     */
    public DetectionResult detect(byte[] imageData, Map<String, Object> options) throws FaceSDKException {
        logger.debug("Detecting faces in image ({} bytes)", imageData.length);

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", "image.jpg",
                        RequestBody.create(imageData, MEDIA_TYPE_JPEG));

        if (options != null) {
            options.forEach((key, value) -> builder.addFormDataPart(key, String.valueOf(value)));
        }

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/detection/detect")
                .header("x-api-key", config.getApiKey())
                .post(builder.build())
                .build();

        return executeWithRetry(request, DetectionResult.class);
    }

    /**
     * 检测文件中的人脸
     *
     * @param file 图片文件
     * @return 检测结果
     * @throws FaceSDKException 检测失败
     */
    public DetectionResult detect(File file) throws FaceSDKException {
        logger.debug("Detecting faces in file: {}", file.getAbsolutePath());

        MediaType mediaType = file.getName().toLowerCase().endsWith(".png") ? MEDIA_TYPE_PNG : MEDIA_TYPE_JPEG;

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", file.getName(),
                        RequestBody.create(file, mediaType))
                .build();

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/detection/detect")
                .header("x-api-key", config.getApiKey())
                .post(requestBody)
                .build();

        return executeWithRetry(request, DetectionResult.class);
    }

    // ==================== 人脸比对 ====================

    /**
     * 比对两张人脸图片
     *
     * @param imageData1 第一张图片
     * @param imageData2 第二张图片
     * @return 比对结果
     * @throws FaceSDKException 比对失败
     */
    public CompareResult compare(byte[] imageData1, byte[] imageData2) throws FaceSDKException {
        logger.debug("Comparing two images");

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file1", "image1.jpg",
                        RequestBody.create(imageData1, MEDIA_TYPE_JPEG))
                .addFormDataPart("file2", "image2.jpg",
                        RequestBody.create(imageData2, MEDIA_TYPE_JPEG))
                .build();

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/compare")
                .header("x-api-key", config.getApiKey())
                .post(requestBody)
                .build();

        return executeWithRetry(request, CompareResult.class);
    }

    // ==================== 人脸识别（1:N） ====================

    /**
     * 在人脸库中搜索相似人脸
     *
     * @param imageData 待搜索图片
     * @param limit     返回结果数量
     * @return 搜索结果
     * @throws FaceSDKException 搜索失败
     */
    public SearchResult search(byte[] imageData, int limit) throws FaceSDKException {
        return search(imageData, limit, 0.0);
    }

    /**
     * 在人脸库中搜索相似人脸
     *
     * @param imageData 待搜索图片
     * @param limit     返回结果数量
     * @param threshold 相似度阈值
     * @return 搜索结果
     * @throws FaceSDKException 搜索失败
     */
    public SearchResult search(byte[] imageData, int limit, double threshold) throws FaceSDKException {
        logger.debug("Searching faces with limit={}", limit);

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", "image.jpg",
                        RequestBody.create(imageData, MEDIA_TYPE_JPEG))
                .addFormDataPart("limit", String.valueOf(limit));

        if (threshold > 0) {
            builder.addFormDataPart("threshold", String.valueOf(threshold));
        }

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/recognize")
                .header("x-api-key", config.getApiKey())
                .post(builder.build())
                .build();

        return executeWithRetry(request, SearchResult.class);
    }

    // ==================== 特征提取 ====================

    /**
     * 提取人脸特征向量
     *
     * @param imageData 图片数据
     * @return 特征向量（Base64 编码的 embedding）
     * @throws FaceSDKException 提取失败
     */
    public String extractFeature(byte[] imageData) throws FaceSDKException {
        logger.debug("Extracting face feature from image ({} bytes)", imageData.length);

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", "image.jpg",
                        RequestBody.create(imageData, MEDIA_TYPE_JPEG));

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/face")
                .header("x-api-key", config.getApiKey())
                .post(builder.build())
                .build();

        try {
            return executeWithRetry(request, String.class);
        } catch (FaceSDKException e) {
            // extractFeature returns a JSON with embedding, parse it
            throw e;
        }
    }

    /**
     * 从文件提取人脸特征向量
     *
     * @param file 图片文件
     * @return 特征向量（Base64 编码的 embedding）
     * @throws FaceSDKException 提取失败
     */
    public String extractFeature(File file) throws FaceSDKException {
        logger.debug("Extracting face feature from file: {}", file.getAbsolutePath());

        MediaType mediaType = file.getName().toLowerCase().endsWith(".png") ? MEDIA_TYPE_PNG : MEDIA_TYPE_JPEG;

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", file.getName(),
                        RequestBody.create(file, mediaType))
                .build();

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/face")
                .header("x-api-key", config.getApiKey())
                .post(requestBody)
                .build();

        return executeWithRetry(request, String.class);
    }

    // ==================== 人脸库管理 ====================

    /**
     * 创建人脸库
     *
     * @param subjectId   人脸库ID
     * @param subjectName 人脸库名称
     * @return 创建的人脸库
     * @throws FaceSDKException 创建失败
     */
    public Subject createSubject(String subjectId, String subjectName) throws FaceSDKException {
        logger.debug("Creating subject: {} - {}", subjectId, subjectName);

        String json = String.format("{\"subject\":\"%s\",\"name\":\"%s\"}", subjectId, subjectName);

        RequestBody requestBody = RequestBody.create(json, MediaType.parse("application/json"));

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/subjects")
                .header("x-api-key", config.getApiKey())
                .post(requestBody)
                .build();

        return executeWithRetry(request, Subject.class);
    }

    /**
     * 删除人脸库
     *
     * @param subjectId 人脸库ID
     * @throws FaceSDKException 删除失败
     */
    public void deleteSubject(String subjectId) throws FaceSDKException {
        logger.debug("Deleting subject: {}", subjectId);

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/subjects/" + subjectId)
                .header("x-api-key", config.getApiKey())
                .delete()
                .build();

        executeWithRetry(request, Void.class);
    }

    /**
     * 列出所有人脸库
     *
     * @return 人脸库列表
     * @throws FaceSDKException 查询失败
     */
    public List<Subject> listSubjects() throws FaceSDKException {
        logger.debug("Listing all subjects");

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/subjects")
                .header("x-api-key", config.getApiKey())
                .get()
                .build();

        return executeWithRetry(request, List.class);
    }

    // ==================== 人脸管理 ====================

    /**
     * 添加人脸到人脸库
     *
     * @param subjectId 人脸库ID
     * @param imageData 人脸图片
     * @param metadata  元数据
     * @return 人脸记录
     * @throws FaceSDKException 添加失败
     */
    public FaceRecord addFace(String subjectId, byte[] imageData, Map<String, Object> metadata) throws FaceSDKException {
        logger.debug("Adding face to subject: {}", subjectId);

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", "image.jpg",
                        RequestBody.create(imageData, MEDIA_TYPE_JPEG));

        if (metadata != null) {
            try {
                builder.addFormDataPart("metadata", objectMapper.writeValueAsString(metadata));
            } catch (Exception e) {
                logger.warn("Failed to serialize metadata", e);
            }
        }

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/faces?subject=" + subjectId)
                .header("x-api-key", config.getApiKey())
                .post(builder.build())
                .build();

        return executeWithRetry(request, FaceRecord.class);
    }

    /**
     * 删除人脸
     *
     * @param faceId 人脸ID
     * @throws FaceSDKException 删除失败
     */
    public void deleteFace(String faceId) throws FaceSDKException {
        logger.debug("Deleting face: {}", faceId);

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/faces/" + faceId)
                .header("x-api-key", config.getApiKey())
                .delete()
                .build();

        executeWithRetry(request, Void.class);
    }

    // ==================== 内部方法 ====================

    private <T> T executeWithRetry(Request request, Class<T> responseType) throws FaceSDKException {
        int attempts = 0;
        Exception lastException = null;

        while (attempts <= config.getMaxRetries()) {
            try {
                return execute(request, responseType);
            } catch (IOException e) {
                lastException = e;
                attempts++;
                if (attempts <= config.getMaxRetries()) {
                    logger.warn("Request failed (attempt {}/{}), retrying...", attempts, config.getMaxRetries() + 1);
                    try {
                        Thread.sleep(config.getRetryDelay().toMillis());
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new FaceSDKException("Retry interrupted", ie);
                    }
                }
            }
        }

        throw new ApiException("Request failed after " + (config.getMaxRetries() + 1) + " attempts", lastException);
    }

    private <T> T execute(Request request, Class<T> responseType) throws IOException, FaceSDKException {
        try (Response response = httpClient.newCall(request).execute()) {
            String responseBody = response.body() != null ? response.body().string() : "";

            if (!response.isSuccessful()) {
                handleErrorResponse(response.code(), responseBody);
            }

            if (responseType == Void.class) {
                return null;
            }

            return objectMapper.readValue(responseBody, responseType);
        }
    }

    private void handleErrorResponse(int statusCode, String responseBody) throws FaceSDKException {
        logger.error("API error: status={}, body={}", statusCode, responseBody);

        String errorMessage = "Unknown error";
        try {
            Map<String, Object> errorMap = objectMapper.readValue(responseBody, Map.class);
            if (errorMap.containsKey("message")) {
                errorMessage = (String) errorMap.get("message");
            } else if (errorMap.containsKey("error")) {
                errorMessage = (String) errorMap.get("error");
            }
        } catch (Exception e) {
            errorMessage = responseBody;
        }

        if (statusCode == 400 && errorMessage.toLowerCase().contains("no face")) {
            throw new NoFaceException(errorMessage);
        }

        throw new ApiException(errorMessage, "API_ERROR", statusCode);
    }

    /**
     * 关闭客户端
     */
    public void close() {
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
    }
}

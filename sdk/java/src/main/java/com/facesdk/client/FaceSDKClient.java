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
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Base64;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.stream.Collectors;
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
                .retryOnConnectionFailure(false)
                .connectTimeout(config.getConnectTimeout())
                .readTimeout(config.getReadTimeout())
                .writeTimeout(config.getWriteTimeout())
                .connectionPool(new ConnectionPool(10, 5, TimeUnit.MINUTES));

        if (!config.isVerifySsl()) {
            try {
                // 信任所有证书（仅用于开发/测试）
                javax.net.ssl.SSLContext sslContext = javax.net.ssl.SSLContext.getInstance("TLS");
                javax.net.ssl.X509TrustManager trustManager = new javax.net.ssl.X509TrustManager() {
                            public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                                return new java.security.cert.X509Certificate[]{};
                            }
                            public void checkClientTrusted(java.security.cert.X509Certificate[] certs, String authType) {}
                            public void checkServerTrusted(java.security.cert.X509Certificate[] certs, String authType) {}
                        };
                sslContext.init(null, new javax.net.ssl.TrustManager[]{trustManager}, new java.security.SecureRandom());
                builder.sslSocketFactory(sslContext.getSocketFactory(), trustManager);
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

        HttpUrl.Builder url = Objects.requireNonNull(HttpUrl.parse(config.getApiUrl() + "/api/v1/detection/detect")).newBuilder();
        if (options != null) {
            options.forEach((key, value) -> url.addQueryParameter(key, String.valueOf(value)));
        }

        Request request = new Request.Builder()
                .url(url.build())
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
                .addFormDataPart("source_image", "image1.jpg",
                        RequestBody.create(imageData1, MEDIA_TYPE_JPEG))
                .addFormDataPart("target_image", "image2.jpg",
                        RequestBody.create(imageData2, MEDIA_TYPE_JPEG))
                .build();

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/verification/verify")
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
        if (limit < 1 || !Double.isFinite(threshold) || threshold < 0 || threshold > 1) {
            throw new FaceSDKException("Invalid search limit or threshold");
        }

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", "image.jpg",
                        RequestBody.create(imageData, MEDIA_TYPE_JPEG));

        Request request = new Request.Builder()
                .url(config.getApiUrl() + "/api/v1/recognition/recognize?prediction_count=" + limit)
                .header("x-api-key", config.getApiKey())
                .post(builder.build())
                .build();

        SearchResult result = executeWithRetry(request, SearchResult.class);
        result.setResults(result.getResults().stream().filter(m -> m.getSimilarity() >= threshold)
                .sorted(Comparator.comparingDouble(SearchResult.MatchResult::getSimilarity).reversed())
                .collect(Collectors.toList()));
        return result;
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
                .url(config.getApiUrl() + "/api/v1/detection/detect?face_plugins=calculator")
                .header("x-api-key", config.getApiKey())
                .post(builder.build())
                .build();

        return encodeEmbedding(executeWithRetry(request, JsonNode.class));
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
                .url(config.getApiUrl() + "/api/v1/detection/detect?face_plugins=calculator")
                .header("x-api-key", config.getApiKey())
                .post(requestBody)
                .build();

        return encodeEmbedding(executeWithRetry(request, JsonNode.class));
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

        String json;
        try { json = objectMapper.writeValueAsString(Map.of("subject", subjectId)); }
        catch (IOException e) { throw new FaceSDKException("Failed to encode subject", e); }

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
                .url(HttpUrl.get(config.getApiUrl() + "/api/v1/recognition/subjects").newBuilder().addPathSegment(validIdentifier(subjectId)).build())
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

        JsonNode data = executeWithRetry(request, JsonNode.class);
        if (!data.path("subjects").isArray()) throw new ApiException("Missing subjects array", "INVALID_RESPONSE", 200);
        List<Subject> subjects = new ArrayList<>();
        for (JsonNode name : data.path("subjects")) {
            Subject subject = new Subject();
            subject.setSubjectId(name.isTextual() ? name.asText() : name.path("subject").asText());
            subjects.add(subject);
        }
        return subjects;
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
        if (metadata != null && !metadata.isEmpty()) {
            throw new FaceSDKException("CompreFace 1.2 does not persist metadata; store it in your application");
        }

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", "image.jpg",
                        RequestBody.create(imageData, MEDIA_TYPE_JPEG));

        Request request = new Request.Builder()
                .url(HttpUrl.get(config.getApiUrl() + "/api/v1/recognition/faces").newBuilder().addQueryParameter("subject", subjectId).build())
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
                .url(HttpUrl.get(config.getApiUrl() + "/api/v1/recognition/faces").newBuilder().addPathSegment(validIdentifier(faceId)).build())
                .header("x-api-key", config.getApiKey())
                .delete()
                .build();

        executeWithRetry(request, Void.class);
    }

    // ==================== 内部方法 ====================

    private <T> T executeWithRetry(Request request, Class<T> responseType) throws FaceSDKException {
        int attempts = 0;
        Exception lastException = null;
        String path = request.url().encodedPath();
        boolean safe = request.method().equals("GET") || request.method().equals("DELETE") ||
                path.equals("/api/v1/detection/detect") || path.equals("/api/v1/verification/verify") ||
                path.equals("/api/v1/recognition/recognize");
        int retries = safe ? config.getMaxRetries() : 0;

        while (attempts <= retries) {
            try {
                return execute(request, responseType, attempts < retries);
            } catch (IOException e) {
                lastException = e;
                attempts++;
                if (attempts <= retries) {
                    logger.warn("Request failed (attempt {}/{}), retrying...", attempts, config.getMaxRetries() + 1);
                    try {
                        Thread.sleep(config.getRetryDelay().toMillis() * (1L << (attempts - 1)));
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new FaceSDKException("Retry interrupted", ie);
                    }
                }
            }
        }

        throw new ApiException("Request failed after " + (retries + 1) + " attempts", lastException);
    }

    private <T> T execute(Request request, Class<T> responseType, boolean canRetry) throws IOException, FaceSDKException {
        String service = request.url().pathSegments().get(2);
        String key = config.getApiKey(service);
        if (key == null || key.isBlank()) throw new ApiException("Missing API key for " + service, "AUTHENTICATION_ERROR", 401);
        request = request.newBuilder().header("x-api-key", key).build();
        try (Response response = httpClient.newCall(request).execute()) {
            String responseBody = response.body() != null ? response.body().string() : "";

            if (!response.isSuccessful()) {
                if (canRetry && (response.code() == 429 || response.code() == 500 || response.code() == 502 || response.code() == 503 || response.code() == 504)) {
                    throw new IOException("Transient HTTP " + response.code());
                }
                handleErrorResponse(response.code(), responseBody);
            }

            if (responseType == Void.class) {
                return null;
            }

            try {
                JsonNode data = objectMapper.readTree(responseBody);
                if (data == null || !data.isObject()) throw new ApiException("API returned invalid JSON", "INVALID_RESPONSE", response.code());
                if (responseType == DetectionResult.class) return responseType.cast(parseDetection(data));
                if (responseType == SearchResult.class) return responseType.cast(parseSearch(data));
                if (responseType == CompareResult.class) return responseType.cast(parseComparison(data));
                return objectMapper.treeToValue(data, responseType);
            } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
                throw new ApiException("API returned invalid JSON", e);
            }
        }
    }

    private static String validIdentifier(String value) {
        if (value == null || value.isEmpty() || value.equals(".") || value.equals("..")) {
            throw new FaceSDKException("Identifier must not be empty or a dot segment");
        }
        return value;
    }

    private Face parseFace(JsonNode data) throws IOException {
        Face face = objectMapper.treeToValue(data, Face.class);
        face.setConfidence(data.path("confidence").asDouble(data.path("box").path("probability").asDouble()));
        return face;
    }

    private DetectionResult parseDetection(JsonNode data) throws IOException {
        JsonNode values = data.has("result") ? data.get("result") : data.path("faces");
        if (!values.isArray()) throw new ApiException("Missing detection result array", "INVALID_RESPONSE", 200);
        List<Face> faces = new ArrayList<>();
        for (JsonNode value : values) faces.add(parseFace(value));
        DetectionResult result = new DetectionResult();
        result.setFaces(faces);
        result.setFaceCount(faces.size());
        return result;
    }

    private SearchResult parseSearch(JsonNode data) throws IOException {
        JsonNode faces = data.path("result");
        if (!faces.isArray()) throw new ApiException("Missing recognition result array", "INVALID_RESPONSE", 200);
        List<SearchResult.MatchResult> matches = new ArrayList<>();
        for (JsonNode face : faces) {
            for (JsonNode subject : face.path("subjects")) {
                SearchResult.MatchResult match = new SearchResult.MatchResult();
                match.setSubjectId(subject.path("subject").asText());
                match.setSimilarity(subject.path("similarity").asDouble());
                match.setMatch(true);
                match.setFace(parseFace(face));
                matches.add(match);
            }
        }
        SearchResult result = new SearchResult();
        result.setFaceCount(faces.size());
        result.setResults(matches);
        return result;
    }

    private CompareResult parseComparison(JsonNode data) throws IOException {
        JsonNode sources = data.path("result");
        if (!sources.isArray()) throw new ApiException("Missing verification result array", "INVALID_RESPONSE", 200);
        if (sources.isEmpty() || sources.get(0).path("face_matches").isEmpty()) throw new NoFaceException("No face detected in the image");
        JsonNode matches = sources.get(0).path("face_matches");
        if (sources.size() != 1 || matches.size() != 1) {
            throw new ApiException("Comparison requires exactly one face in each image", "VALIDATION_ERROR", 400);
        }
        CompareResult result = new CompareResult();
        result.setSimilarity(matches.get(0).path("similarity").asDouble());
        result.setThreshold(config.getComparisonThreshold());
        result.setMatch(result.getSimilarity() >= result.getThreshold());
        result.setFace1(parseFace(sources.get(0).path("source_image_face")));
        result.setFace2(parseFace(matches.get(0)));
        return result;
    }

    private String encodeEmbedding(JsonNode data) {
        JsonNode faces = data.path("result");
        if (!faces.isArray()) throw new ApiException("Missing detection result array", "INVALID_RESPONSE", 200);
        if (faces.isEmpty()) throw new NoFaceException("No face detected in the image");
        if (faces.size() != 1) throw new FaceSDKException("Feature extraction requires exactly one face");
        JsonNode values = faces.get(0).path("embedding");
        if (!values.isArray() || values.isEmpty()) throw new ApiException("Calculator plugin did not return an embedding", "NO_EMBEDDING", 200);
        ByteBuffer buffer = ByteBuffer.allocate(values.size() * Float.BYTES).order(ByteOrder.LITTLE_ENDIAN);
        for (JsonNode value : values) buffer.putFloat((float) value.asDouble());
        return Base64.getEncoder().encodeToString(buffer.array());
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

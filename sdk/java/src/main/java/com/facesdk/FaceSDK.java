/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/FaceSDK.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * FaceSDK Java Client - Main Entry Point
 */

package com.facesdk;

import com.facesdk.client.FaceSDKClient;
import com.facesdk.config.FaceSDKConfig;
import com.facesdk.exception.FaceSDKException;

import java.time.Duration;

/**
 * FaceSDK Java 客户端主类
 * 
 * 提供人脸检测、人脸比对、人脸识别、人脸库管理等功能的统一接口。
 * 
 * <p>使用示例：</p>
 * <pre>
 * FaceSDK client = FaceSDK.builder()
 *     .apiUrl("http://localhost:8000")
 *     .apiKey("your-api-key")
 *     .connectTimeout(Duration.ofSeconds(5))
 *     .readTimeout(Duration.ofSeconds(30))
 *     .build();
 * </pre>
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
public class FaceSDK {

    private final FaceSDKClient client;

    private FaceSDK(FaceSDKConfig config) {
        this.client = new FaceSDKClient(config);
    }

    /**
     * 获取 FaceSDK 客户端实例
     *
     * @return FaceSDKClient 实例
     */
    public FaceSDKClient getClient() {
        return client;
    }

    /**
     * 创建 FaceSDK 构建器
     *
     * @return FaceSDKBuilder 实例
     */
    public static FaceSDKBuilder builder() {
        return new FaceSDKBuilder();
    }

    /**
     * FaceSDK 构建器
     */
    public static class FaceSDKBuilder {
        private String apiUrl;
        private String apiKey;
        private Duration connectTimeout = Duration.ofSeconds(5);
        private Duration readTimeout = Duration.ofSeconds(30);
        private Duration writeTimeout = Duration.ofSeconds(30);
        private int maxRetries = 3;
        private Duration retryDelay = Duration.ofMillis(500);
        private boolean verifySsl = true;

        private FaceSDKBuilder() {}

        /**
         * 设置 API 基础 URL
         *
         * @param apiUrl API 基础 URL，如 http://localhost:8000
         * @return 当前构建器
         */
        public FaceSDKBuilder apiUrl(String apiUrl) {
            this.apiUrl = apiUrl;
            return this;
        }

        /**
         * 设置 API 密钥
         *
         * @param apiKey API 密钥
         * @return 当前构建器
         */
        public FaceSDKBuilder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }

        /**
         * 设置连接超时时间
         *
         * @param connectTimeout 连接超时时间
         * @return 当前构建器
         */
        public FaceSDKBuilder connectTimeout(Duration connectTimeout) {
            this.connectTimeout = connectTimeout;
            return this;
        }

        /**
         * 设置读取超时时间
         *
         * @param readTimeout 读取超时时间
         * @return 当前构建器
         */
        public FaceSDKBuilder readTimeout(Duration readTimeout) {
            this.readTimeout = readTimeout;
            return this;
        }

        /**
         * 设置写入超时时间
         *
         * @param writeTimeout 写入超时时间
         * @return 当前构建器
         */
        public FaceSDKBuilder writeTimeout(Duration writeTimeout) {
            this.writeTimeout = writeTimeout;
            return this;
        }

        /**
         * 设置最大重试次数
         *
         * @param maxRetries 最大重试次数
         * @return 当前构建器
         */
        public FaceSDKBuilder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        /**
         * 设置重试延迟
         *
         * @param retryDelay 重试延迟
         * @return 当前构建器
         */
        public FaceSDKBuilder retryDelay(Duration retryDelay) {
            this.retryDelay = retryDelay;
            return this;
        }

        /**
         * 设置是否验证 SSL 证书
         *
         * @param verifySsl 是否验证 SSL
         * @return 当前构建器
         */
        public FaceSDKBuilder verifySsl(boolean verifySsl) {
            this.verifySsl = verifySsl;
            return this;
        }

        /**
         * 构建 FaceSDK 实例
         *
         * @return FaceSDK 实例
         * @throws FaceSDKException 如果配置无效
         */
        public FaceSDK build() {
            validate();
            FaceSDKConfig config = new FaceSDKConfig(
                apiUrl,
                apiKey,
                connectTimeout,
                readTimeout,
                writeTimeout,
                maxRetries,
                retryDelay,
                verifySsl
            );
            return new FaceSDK(config);
        }

        private void validate() {
            if (apiUrl == null || apiUrl.trim().isEmpty()) {
                throw new FaceSDKException("API URL must not be null or empty");
            }
            if (apiKey == null || apiKey.trim().isEmpty()) {
                throw new FaceSDKException("API Key must not be null or empty");
            }
            if (maxRetries < 0) {
                throw new FaceSDKException("Max retries must be non-negative");
            }
        }
    }
}

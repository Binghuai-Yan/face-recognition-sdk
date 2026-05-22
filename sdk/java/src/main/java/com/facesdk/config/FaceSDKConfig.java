/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/config/FaceSDKConfig.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * FaceSDK Configuration
 */

package com.facesdk.config;

import java.time.Duration;
import java.util.Objects;

/**
 * FaceSDK 配置类
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
public class FaceSDKConfig {

    private final String apiUrl;
    private final String apiKey;
    private final Duration connectTimeout;
    private final Duration readTimeout;
    private final Duration writeTimeout;
    private final int maxRetries;
    private final Duration retryDelay;
    private final boolean verifySsl;

    public FaceSDKConfig(
            String apiUrl,
            String apiKey,
            Duration connectTimeout,
            Duration readTimeout,
            Duration writeTimeout,
            int maxRetries,
            Duration retryDelay,
            boolean verifySsl) {
        this.apiUrl = Objects.requireNonNull(apiUrl, "API URL must not be null");
        this.apiKey = Objects.requireNonNull(apiKey, "API Key must not be null");
        this.connectTimeout = Objects.requireNonNull(connectTimeout, "Connect timeout must not be null");
        this.readTimeout = Objects.requireNonNull(readTimeout, "Read timeout must not be null");
        this.writeTimeout = Objects.requireNonNull(writeTimeout, "Write timeout must not be null");
        this.maxRetries = maxRetries;
        this.retryDelay = Objects.requireNonNull(retryDelay, "Retry delay must not be null");
        this.verifySsl = verifySsl;
    }

    public String getApiUrl() {
        return apiUrl;
    }

    public String getApiKey() {
        return apiKey;
    }

    public Duration getConnectTimeout() {
        return connectTimeout;
    }

    public Duration getReadTimeout() {
        return readTimeout;
    }

    public Duration getWriteTimeout() {
        return writeTimeout;
    }

    public int getMaxRetries() {
        return maxRetries;
    }

    public Duration getRetryDelay() {
        return retryDelay;
    }

    public boolean isVerifySsl() {
        return verifySsl;
    }

    @Override
    public String toString() {
        return "FaceSDKConfig{" +
                "apiUrl='" + apiUrl + '\'' +
                ", apiKey='***'" +
                ", connectTimeout=" + connectTimeout +
                ", readTimeout=" + readTimeout +
                ", writeTimeout=" + writeTimeout +
                ", maxRetries=" + maxRetries +
                ", retryDelay=" + retryDelay +
                ", verifySsl=" + verifySsl +
                '}';
    }
}

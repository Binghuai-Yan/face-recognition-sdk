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
import java.util.Map;
import java.util.HashMap;
import java.util.Collections;

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
    private final Map<String, String> apiKeys;
    private final double comparisonThreshold;

    public FaceSDKConfig(
            String apiUrl,
            String apiKey,
            Duration connectTimeout,
            Duration readTimeout,
            Duration writeTimeout,
            int maxRetries,
            Duration retryDelay,
            boolean verifySsl) {
        this(apiUrl, apiKey, connectTimeout, readTimeout, writeTimeout, maxRetries, retryDelay,
             verifySsl, Collections.emptyMap(), 0.8);
    }

    public FaceSDKConfig(String apiUrl, String apiKey, Duration connectTimeout, Duration readTimeout,
                         Duration writeTimeout, int maxRetries, Duration retryDelay, boolean verifySsl,
                         Map<String, String> apiKeys, double comparisonThreshold) {
        this.apiUrl = Objects.requireNonNull(apiUrl, "API URL must not be null").replaceAll("/+$", "");
        this.apiKey = Objects.requireNonNull(apiKey, "API Key must not be null");
        this.connectTimeout = Objects.requireNonNull(connectTimeout, "Connect timeout must not be null");
        this.readTimeout = Objects.requireNonNull(readTimeout, "Read timeout must not be null");
        this.writeTimeout = Objects.requireNonNull(writeTimeout, "Write timeout must not be null");
        this.maxRetries = maxRetries;
        this.retryDelay = Objects.requireNonNull(retryDelay, "Retry delay must not be null");
        this.verifySsl = verifySsl;
        this.apiKeys = Collections.unmodifiableMap(new HashMap<>(apiKeys));
        this.comparisonThreshold = comparisonThreshold;
        if (maxRetries < 0 || retryDelay.isNegative() || !Double.isFinite(comparisonThreshold)
                || comparisonThreshold < 0 || comparisonThreshold > 1) {
            throw new IllegalArgumentException("Invalid retry configuration or comparison threshold");
        }
    }

    public String getApiUrl() {
        return apiUrl;
    }

    public String getApiKey() {
        return apiKey;
    }

    public String getApiKey(String service) { return apiKeys.getOrDefault(service, apiKey); }
    public double getComparisonThreshold() { return comparisonThreshold; }

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

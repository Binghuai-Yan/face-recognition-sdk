/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/exception/FaceSDKException.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * FaceSDK Exception
 */

package com.facesdk.exception;

/**
 * FaceSDK 通用异常类
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
public class FaceSDKException extends RuntimeException {

    private final Integer httpStatusCode;
    private final String errorCode;

    public FaceSDKException(String message) {
        super(message);
        this.httpStatusCode = null;
        this.errorCode = null;
    }

    public FaceSDKException(String message, Throwable cause) {
        super(message, cause);
        this.httpStatusCode = null;
        this.errorCode = null;
    }

    public FaceSDKException(String message, String errorCode, Integer httpStatusCode) {
        super(message);
        this.errorCode = errorCode;
        this.httpStatusCode = httpStatusCode;
    }

    public FaceSDKException(String message, Throwable cause, String errorCode, Integer httpStatusCode) {
        super(message, cause);
        this.errorCode = errorCode;
        this.httpStatusCode = httpStatusCode;
    }

    /**
     * 获取 HTTP 状态码
     *
     * @return HTTP 状态码，如果未知则返回 null
     */
    public Integer getHttpStatusCode() {
        return httpStatusCode;
    }

    /**
     * 获取错误代码
     *
     * @return 错误代码，如果未知则返回 null
     */
    public String getErrorCode() {
        return errorCode;
    }
}

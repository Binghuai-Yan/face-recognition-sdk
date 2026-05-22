/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/exception/ApiException.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * API Exception
 */

package com.facesdk.exception;

/**
 * API 调用异常
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
public class ApiException extends FaceSDKException {

    public ApiException(String message) {
        super(message);
    }

    public ApiException(String message, Throwable cause) {
        super(message, cause);
    }

    public ApiException(String message, String errorCode, Integer httpStatusCode) {
        super(message, errorCode, httpStatusCode);
    }

    public ApiException(String message, Throwable cause, String errorCode, Integer httpStatusCode) {
        super(message, cause, errorCode, httpStatusCode);
    }
}

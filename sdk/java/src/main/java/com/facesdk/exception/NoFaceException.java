/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/exception/NoFaceException.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * No Face Detected Exception
 */

package com.facesdk.exception;

/**
 * 未检测到人脸异常
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
public class NoFaceException extends FaceSDKException {

    public NoFaceException(String message) {
        super(message, "NO_FACE_DETECTED", 400);
    }

    public NoFaceException(String message, Throwable cause) {
        super(message, cause, "NO_FACE_DETECTED", 400);
    }
}

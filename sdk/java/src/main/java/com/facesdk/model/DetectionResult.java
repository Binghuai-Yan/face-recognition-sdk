/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/model/DetectionResult.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Detection Result Model
 */

package com.facesdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * 人脸检测结果
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DetectionResult {

    @JsonProperty("faces")
    private List<Face> faces;

    @JsonProperty("image_id")
    private String imageId;

    @JsonProperty("face_count")
    private int faceCount;

    public List<Face> getFaces() {
        return faces;
    }

    public void setFaces(List<Face> faces) {
        this.faces = faces;
    }

    public String getImageId() {
        return imageId;
    }

    public void setImageId(String imageId) {
        this.imageId = imageId;
    }

    public int getFaceCount() {
        return faceCount;
    }

    public void setFaceCount(int faceCount) {
        this.faceCount = faceCount;
    }

    @Override
    public String toString() {
        return "DetectionResult{" +
                "faces=" + faces +
                ", imageId='" + imageId + '\'' +
                ", faceCount=" + faceCount +
                '}';
    }
}

/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/model/FaceRecord.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Face Record Model
 */

package com.facesdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;
import java.util.Map;

/**
 * 人脸记录模型
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FaceRecord {

    @JsonProperty("image_id")
    private String imageId;

    @JsonProperty("subject")
    private String subjectId;

    @JsonProperty("created_at")
    private Instant createdAt;

    @JsonProperty("updated_at")
    private Instant updatedAt;

    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    public String getImageId() {
        return imageId;
    }

    public void setImageId(String imageId) {
        this.imageId = imageId;
    }

    public String getSubjectId() {
        return subjectId;
    }

    public void setSubjectId(String subjectId) {
        this.subjectId = subjectId;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    @Override
    public String toString() {
        return "FaceRecord{" +
                "imageId='" + imageId + '\'' +
                ", subjectId='" + subjectId + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                ", metadata=" + metadata +
                '}';
    }
}

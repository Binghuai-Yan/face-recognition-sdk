/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/model/Subject.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Subject Model
 */

package com.facesdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;
import java.util.List;

/**
 * 人脸库（Subject）模型
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Subject {

    @JsonProperty("subject")
    private String subjectId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("created_at")
    private Instant createdAt;

    @JsonProperty("updated_at")
    private Instant updatedAt;

    @JsonProperty("faces")
    private List<FaceRecord> faces;

    public String getSubjectId() {
        return subjectId;
    }

    public void setSubjectId(String subjectId) {
        this.subjectId = subjectId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
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

    public List<FaceRecord> getFaces() {
        return faces;
    }

    public void setFaces(List<FaceRecord> faces) {
        this.faces = faces;
    }

    @Override
    public String toString() {
        return "Subject{" +
                "subjectId='" + subjectId + '\'' +
                ", name='" + name + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                ", faces=" + faces +
                '}';
    }
}

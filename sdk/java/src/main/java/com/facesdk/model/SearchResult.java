/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/model/SearchResult.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Search Result Model
 */

package com.facesdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * 人脸识别（1:N 搜索）结果
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class SearchResult {

    @JsonProperty("results")
    private List<MatchResult> results;

    @JsonProperty("face_count")
    private int faceCount;

    @JsonProperty("image_id")
    private String imageId;

    public List<MatchResult> getResults() {
        return results;
    }

    public void setResults(List<MatchResult> results) {
        this.results = results;
    }

    public int getFaceCount() {
        return faceCount;
    }

    public void setFaceCount(int faceCount) {
        this.faceCount = faceCount;
    }

    public String getImageId() {
        return imageId;
    }

    public void setImageId(String imageId) {
        this.imageId = imageId;
    }

    @Override
    public String toString() {
        return "SearchResult{" +
                "results=" + results +
                ", faceCount=" + faceCount +
                ", imageId='" + imageId + '\'' +
                '}';
    }

    /**
     * 匹配结果
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class MatchResult {
        @JsonProperty("subject")
        private String subjectId;

        @JsonProperty("similarity")
        private double similarity;

        @JsonProperty("distance")
        private double distance;

        @JsonProperty("is_match")
        private boolean match;

        @JsonProperty("face")
        private Face face;

        public String getSubjectId() {
            return subjectId;
        }

        public void setSubjectId(String subjectId) {
            this.subjectId = subjectId;
        }

        public double getSimilarity() {
            return similarity;
        }

        public void setSimilarity(double similarity) {
            this.similarity = similarity;
        }

        public double getDistance() {
            return distance;
        }

        public void setDistance(double distance) {
            this.distance = distance;
        }

        public boolean isMatch() {
            return match;
        }

        public void setMatch(boolean match) {
            this.match = match;
        }

        public Face getFace() {
            return face;
        }

        public void setFace(Face face) {
            this.face = face;
        }

        @Override
        public String toString() {
            return "MatchResult{" +
                    "subjectId='" + subjectId + '\'' +
                    ", similarity=" + similarity +
                    ", distance=" + distance +
                    ", match=" + match +
                    ", face=" + face +
                    '}';
        }
    }
}
